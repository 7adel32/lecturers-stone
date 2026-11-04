"""
Local AI Detection Engine using desklib/ai-text-detector-v1.01.
Architecture: Fine-tuned microsoft/deberta-v3-large with mean pooling head.
Ranked #1 on the RAID AI Detection Benchmark.
Runs directly on local GPU via CUDA or CPU fallback (optional).
"""

import time
import math
import os
from typing import Dict, Any, List, Optional
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoConfig, AutoModel, PreTrainedModel

try:
    import spaces
except ImportError:
    class _MockSpaces:
        def GPU(self, fn=None, **kwargs):
            if fn is not None:
                return fn
            def wrapper(f):
                return f
            return wrapper
    spaces = _MockSpaces()

class DesklibAIDetectionModel(PreTrainedModel):
    config_class = AutoConfig
    _tied_weights_keys = []

    def __init__(self, config):
        super().__init__(config)
        self.model = AutoModel.from_config(config)
        self.classifier = nn.Linear(config.hidden_size, 1)
        self.init_weights()

    @property
    def all_tied_weights_keys(self):
        return {}

    def forward(self, input_ids, attention_mask=None, labels=None):
        outputs = self.model(input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs[0]
        # Mean pooling
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, dim=1)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        pooled_output = sum_embeddings / sum_mask

        logits = self.classifier(pooled_output)
        loss = None
        if labels is not None:
            loss_fct = nn.BCEWithLogitsLoss()
            loss = loss_fct(logits.view(-1), labels.float())

        output = {"logits": logits}
        if loss is not None:
            output["loss"] = loss
        return output

class LocalDebertaDetector:
    _instance = None

    def __init__(self, model_name: str = "desklib/ai-text-detector-v1.01", device: Optional[str] = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._is_loaded = False

    def load_model(self):
        if self._is_loaded:
            return

        print(f"Loading local AI detector '{self.model_name}' on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = DesklibAIDetectionModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        self._is_loaded = True
        print("Local AI detector loaded successfully!")

    def predict_chunk(self, text: str, max_len: int = 512) -> float:
        if not self._is_loaded:
            self.load_model()

        encoded = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=max_len,
            return_tensors="pt"
        )
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs["logits"]
            prob = torch.sigmoid(logits).item()

        return float(prob)

    def analyze_text(self, text: str, chunk_size: int = 350, max_chunks: int = 15) -> Dict[str, Any]:
        """
        Analyze text using local GPU model.
        For documents longer than chunk_size words, breaks into overlapping chunks and computes aggregate probability.
        """
        service_name = "Local Desklib DeBERTa (ZeroGPU / A10G)" if os.environ.get("SPACE_ID") else "Local Desklib DeBERTa (CUDA / GPU)"
        start_time = time.time()
        clean_text = text.strip()
        if not clean_text:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Empty Input",
                "status": "empty",
                "latency_sec": 0.0,
                "metrics": {"device": str(self.device)}
            }

        try:
            if not self._is_loaded:
                self.load_model()

            words = clean_text.split()
            # If text fits comfortably in single chunk
            if len(words) <= chunk_size:
                prob = self.predict_chunk(clean_text)
                chunk_scores = [prob]
            else:
                # Sliding window chunking
                step = int(chunk_size * 0.75)
                chunks = []
                for i in range(0, len(words), step):
                    chunk_text = " ".join(words[i:i + chunk_size])
                    if len(chunk_text.strip()) > 30:
                        chunks.append(chunk_text)
                    if len(chunks) >= max_chunks:
                        break

                chunk_scores = []
                for chunk in chunks:
                    chunk_scores.append(self.predict_chunk(chunk))

                # Compute weighted average (or mean)
                prob = sum(chunk_scores) / len(chunk_scores) if chunk_scores else 0.5

            prob = round(prob, 4)
            label = "AI-Generated" if prob >= 0.5 else "Human-Written"

            return {
                "service_name": service_name,
                "ai_probability": prob,
                "label": label,
                "status": "success",
                "latency_sec": round(time.time() - start_time, 3),
                "metrics": {
                    "device": str(self.device),
                    "chunks_analyzed": len(chunk_scores),
                    "score_min": round(min(chunk_scores), 4) if chunk_scores else prob,
                    "score_max": round(max(chunk_scores), 4) if chunk_scores else prob,
                }
            }

        except Exception as e:
            return {
                "service_name": service_name,
                "ai_probability": None,
                "label": "Error",
                "status": f"error: {str(e)}",
                "latency_sec": round(time.time() - start_time, 2)
            }

# Singleton accessor
_GLOBAL_DETECTOR: Optional[LocalDebertaDetector] = None

def is_local_available() -> bool:
    """Check if local DeBERTa model weights are present in local Hugging Face cache or running on HF Space."""
    try:
        if os.environ.get("SPACE_ID"):
            return True
        from huggingface_hub import try_to_load_from_cache
        filepath = try_to_load_from_cache("desklib/ai-text-detector-v1.01", "config.json")
        return filepath is not None
    except Exception:
        return False


def get_local_detector() -> LocalDebertaDetector:
    global _GLOBAL_DETECTOR
    if _GLOBAL_DETECTOR is None:
        _GLOBAL_DETECTOR = LocalDebertaDetector()
    return _GLOBAL_DETECTOR
