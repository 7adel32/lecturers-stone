"""
The Lecturer's Stone - Unified Multi-Service AI Content Detection Framework.
Queries several online and local detection engines concurrently:
1. Local Desklib DeBERTa (#1 ranked on the RAID benchmark)
2. TrustSafeAI RADAR (Adversarial Robust AI Text Detector)
3. Fakespot AI (Commercial-grade AI Text Classifier)
4. SzegedAI (DeBERTa Transformer Classifier)
5. PirateXX (Multi-class RoBERTa AI Detector)
6. YugamJ LLM Detector
7. Heuristic & Burstiness Engine (Offline statistical NLP baseline)
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import requests

try:
    from gradio_client import Client
except ImportError:
    Client = None

from heuristic_engine import analyze_heuristic
from document_parser import extract_text_from_file
from metadata_forensics import inspect_metadata


class AICheckerHub:
    def __init__(self, timeout: int = 15, enable_local: bool = True):
        self.timeout = timeout
        self.enable_local = enable_local
        self.clients = {}

    def check_local_deberta(self, text: str) -> Dict[str, Any]:
        """Local DeBERTa-v3-large detector running via CUDA (GPU) or CPU fallback."""
        if not self.enable_local:
            return {
                "service_name": "Local Desklib DeBERTa",
                "ai_probability": None,
                "label": "Disabled",
                "status": "disabled by configuration",
                "latency_sec": 0.0
            }

        try:
            from local_detector import get_local_detector, is_local_available
            if not is_local_available():
                return {
                    "service_name": "Local Desklib DeBERTa",
                    "ai_probability": None,
                    "label": "Not Available",
                    "status": "local model dependencies or cached weights not found",
                    "latency_sec": 0.0
                }
            detector = get_local_detector()
            return detector.analyze_text(text)
        except Exception as e:
            return {
                "service_name": "Local Desklib DeBERTa",
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": 0.0
            }

    def _get_client(self, space_name: str):
        if Client is None:
            raise RuntimeError("gradio_client is not installed")
        if space_name not in self.clients:
            self.clients[space_name] = Client(space_name)
        return self.clients[space_name]

    def check_szegedai(self, text: str) -> Dict[str, Any]:
        service_name = "SzegedAI (DeBERTa AI Detector)"
        start_time = time.time()
        try:
            clean_text = text[:3500] if len(text) > 3500 else text
            client = self._get_client("SzegedAI/AI_Detector")
            res = client.predict(clean_text, api_name="/classify_text")
            output_str = res[0] if isinstance(res, (tuple, list)) else str(res)

            match = re.search(r"(\d+(\.\d+)?)%\s*likely\s*<b>\s*(Human written|AI written|AI generated)", output_str, re.IGNORECASE)
            if match:
                percentage = float(match.group(1)) / 100.0
                detected_type = match.group(3).lower()
                ai_prob = (1.0 - percentage) if "human" in detected_type else percentage
            else:
                pct_match = re.search(r"(\d+(\.\d+)?)%", output_str)
                pct = float(pct_match.group(1)) / 100.0 if pct_match else 0.5
                ai_prob = (1.0 - pct) if "human" in output_str.lower() else pct

            return {
                "service_name": service_name,
                "ai_probability": round(ai_prob, 4),
                "label": "AI-Generated" if ai_prob >= 0.5 else "Human-Written",
                "status": "success",
                "latency_sec": round(time.time() - start_time, 2),
                "raw_response": output_str[:150]
            }
        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

    def check_radar(self, text: str) -> Dict[str, Any]:
        service_name = "TrustSafeAI RADAR (Adversarial Detector)"
        start_time = time.time()
        try:
            clean_text = text[:3500] if len(text) > 3500 else text
            client = self._get_client("TrustSafeAI/RADAR-AI-Text-Detector")
            res = client.predict(clean_text, api_name="/predict")
            ai_prob = 0.5
            if isinstance(res, dict) and "confidences" in res:
                for conf in res["confidences"]:
                    if "ai" in conf.get("label", "").lower():
                        ai_prob = float(conf.get("confidence", 0.5))
                        break
            return {
                "service_name": service_name,
                "ai_probability": round(ai_prob, 4),
                "label": "AI-Generated" if ai_prob >= 0.5 else "Human-Written",
                "status": "success",
                "latency_sec": round(time.time() - start_time, 2),
                "raw_response": res
            }
        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

    def check_fakespot(self, text: str) -> Dict[str, Any]:
        service_name = "Fakespot AI Text Classifier"
        start_time = time.time()
        try:
            clean_text = text[:2000] if len(text) > 2000 else text
            client = self._get_client("fakespot-ai/ai-text-detector")
            res = client.predict(clean_text, api_name="/predict")
            ai_prob = 0.5
            if isinstance(res, dict) and "confidences" in res:
                for conf in res["confidences"]:
                    if conf.get("label", "").lower() == "ai":
                        ai_prob = float(conf.get("confidence", 0.5))
                        break
            return {
                "service_name": service_name,
                "ai_probability": round(ai_prob, 4),
                "label": "AI-Generated" if ai_prob >= 0.5 else "Human-Written",
                "status": "success",
                "latency_sec": round(time.time() - start_time, 2),
                "raw_response": res
            }
        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

    def check_piratexx(self, text: str) -> Dict[str, Any]:
        service_name = "PirateXX RoBERTa Detector"
        start_time = time.time()
        try:
            clean_text = text[:3500] if len(text) > 3500 else text
            client = self._get_client("PirateXX/AI-Content-Detector")
            res = client.predict(clean_text, api_name="/predict")
            ai_prob = 0.5
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                ai_prob = float(res[0].get("Fake", 0.5))
            elif isinstance(res, dict):
                ai_prob = float(res.get("Fake", 0.5))

            return {
                "service_name": service_name,
                "ai_probability": round(ai_prob, 4),
                "label": "AI-Generated" if ai_prob >= 0.5 else "Human-Written",
                "status": "success",
                "latency_sec": round(time.time() - start_time, 2),
                "raw_response": res
            }
        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

    def check_yugamj(self, text: str) -> Dict[str, Any]:
        service_name = "YugamJ LLM Text Detector"
        start_time = time.time()
        try:
            clean_text = text[:3500] if len(text) > 3500 else text
            client = self._get_client("yugamj/ai-text-detector-01")
            res = client.predict(clean_text, api_name="/predict")
            ai_prob = 0.5
            if isinstance(res, dict) and "confidences" in res:
                for conf in res["confidences"]:
                    if conf.get("label", "").lower() in ["ai", "chatgpt"]:
                        ai_prob = float(conf.get("confidence", 0.5))
                        break
            return {
                "service_name": service_name,
                "ai_probability": round(ai_prob, 4),
                "label": "AI-Generated" if ai_prob >= 0.5 else "Human-Written",
                "status": "success",
                "latency_sec": round(time.time() - start_time, 2),
                "raw_response": res
            }
        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

    def check_heuristic(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        res = analyze_heuristic(text)
        res["latency_sec"] = round(time.time() - start_time, 4)
        return res

    def analyze_text(self, text: str, services: List[str] = None) -> Dict[str, Any]:
        word_count = len(text.split())
        char_count = len(text)

        if word_count == 0:
            return {
                "verdict": "No Extractable Text",
                "consensus_ai_probability": None,
                "consensus_percentage": 0.0,
                "votes": {
                    "ai": 0,
                    "human": 0,
                    "total_valid_services": 0
                },
                "score_spread": {
                    "min": 0.0,
                    "max": 0.0,
                    "range": 0.0
                },
                "document_stats": {
                    "words": 0,
                    "characters": 0,
                },
                "services": []
            }

        all_runners = {
            "local_deberta": self.check_local_deberta,
            "radar": self.check_radar,
            "fakespot": self.check_fakespot,
            "szegedai": self.check_szegedai,
            "piratexx": self.check_piratexx,
            "yugamj": self.check_yugamj,
            "heuristic": self.check_heuristic,
        }

        if services:
            runners_to_use = {k: v for k, v in all_runners.items() if k in services}
        else:
            # Local model is optional: only include it in default set if enable_local and available
            from local_detector import is_local_available
            has_local = self.enable_local and is_local_available()
            runners_to_use = {
                k: v for k, v in all_runners.items()
                if k != "local_deberta" or has_local
            }

        results = []
        with ThreadPoolExecutor(max_workers=len(runners_to_use)) as executor:
            future_to_name = {executor.submit(fn, text): name for name, fn in runners_to_use.items()}
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:
                    results.append({
                        "service_name": name,
                        "ai_probability": None,
                        "label": "Execution Error",
                        "status": f"error: {exc}",
                        "latency_sec": 0.0
                    })

        # Exclude empty, none, or non-successful evaluations from consensus
        valid_results = [
            r for r in results
            if r.get("ai_probability") is not None
            and r.get("status") == "success"
            and r.get("label") not in ["Empty Input", "Empty / None", "Empty", "None", "No Extractable Text", "Insufficient Text", "Insufficient Text (< 10 words)"]
        ]
        valid_scores = [r["ai_probability"] for r in valid_results]

        if valid_scores:
            avg_prob = sum(valid_scores) / len(valid_scores)
            min_prob = min(valid_scores)
            max_prob = max(valid_scores)
            ai_votes = sum(1 for s in valid_scores if s >= 0.5)
            human_votes = len(valid_scores) - ai_votes

            if avg_prob >= 0.70:
                verdict = "Highly Likely AI-Generated"
            elif avg_prob >= 0.50:
                verdict = "Likely AI-Generated"
            elif avg_prob >= 0.35:
                verdict = "Mixed / Hybrid Content"
            else:
                verdict = "Likely Human-Written"
        else:
            avg_prob = None
            min_prob = 0.0
            max_prob = 0.0
            ai_votes = 0
            human_votes = 0
            verdict = "No active service succeeded"

        return {
            "verdict": verdict,
            "consensus_ai_probability": round(avg_prob, 4) if avg_prob is not None else None,
            "consensus_percentage": round(avg_prob * 100.0, 2) if avg_prob is not None else 0.0,
            "votes": {
                "ai": ai_votes,
                "human": human_votes,
                "total_valid_services": len(valid_scores)
            },
            "score_spread": {
                "min": round(min_prob, 4),
                "max": round(max_prob, 4),
                "range": round(max_prob - min_prob, 4)
            },
            "document_stats": {
                "words": word_count,
                "characters": char_count
            },
            "services": sorted(results, key=lambda x: (x.get("status") != "success", x.get("service_name", "")))
        }

    def analyze_file(self, file_path: Union[str, Path], services: List[str] = None, check_metadata: bool = True) -> Dict[str, Any]:
        path = Path(file_path)
        text = extract_text_from_file(path)
        report = self.analyze_text(text, services=services)
        report["source"] = path.name
        report["file_path"] = str(path.resolve())

        if check_metadata:
            report["metadata_forensics"] = inspect_metadata(path)

        return report
