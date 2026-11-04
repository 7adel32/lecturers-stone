#!/usr/bin/env python3
"""
Hermes Agent Integration: /aicheck
Runs multi-service AI content detection and metadata forensics via The Lecturer's Stone.
Designed for 24/7 background automation, cron jobs, and WhatsApp notifications.
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path

# Paths to Windows host environment
WINDOWS_PYTHON = "/mnt/c/Users/Percent/AppData/Local/Python/pythoncore-3.14-64/python.exe"
WINDOWS_CLI = "C:/Users/Percent/dev/lecturers-stone/cli.py"


def run_ai_checker(target_text=None, target_file=None, skip_ai=False, cleanse_target=None, author=None):
    cmd = [WINDOWS_PYTHON, WINDOWS_CLI, "--json"]

    if target_file:
        clean_file = str(target_file).strip()
        if clean_file.startswith("/mnt/c/"):
            win_file = "C:/" + clean_file[len("/mnt/c/"):]
        else:
            win_file = clean_file
        cmd.extend(["-f", win_file])
    elif target_text:
        cmd.extend(["-t", str(target_text).strip()])
    else:
        return "Usage: /aicheck <text to check> OR /aicheck -f <path_to_doc>"

    if skip_ai:
        cmd.append("--skip-ai")

    if cleanse_target:
        clean_target = str(cleanse_target).strip()
        if clean_target.startswith("/mnt/c/"):
            win_clean = "C:/" + clean_target[len("/mnt/c/"):]
        else:
            win_clean = clean_target
        cmd.extend(["--cleanse", win_clean])
        if author:
            cmd.extend(["--author", str(author).strip()])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # Parse JSON output
        json_start = stdout.find("{")
        json_end = stdout.rfind("}")
        if json_start != -1 and json_end != -1:
            raw_json = stdout[json_start:json_end + 1]
            data = json.loads(raw_json)
        else:
            return stdout if stdout else f"Error running AI Checker: {stderr}"

        lines = ["[THE LECTURER'S STONE REPORT]"]

        # 1. Document Metadata Forensics Section
        meta = data.get("metadata_forensics")
        if meta and meta.get("has_metadata"):
            lines.append("")
            lines.append("--- Metadata & File Details ---")
            lines.append(f"File: {meta.get('file_name', 'Unknown')} ({meta.get('file_type', '')})")

            authors = meta.get("all_authors", [])
            auth_str = ", ".join(authors) if authors else "[None / Stripped]"
            lines.append(f"Authors/Owners: {auth_str}")
            if meta.get("creator"):
                lines.append(f"Creator: {meta['creator']}")
            if meta.get("last_modified_by"):
                lines.append(f"Last Modified By: {meta['last_modified_by']}")
            if meta.get("application"):
                app_str = meta["application"]
                if meta.get("app_version"):
                    app_str += f" (v{meta['app_version']})"
                lines.append(f"Software/Tool: {app_str}")
            if meta.get("revision"):
                lines.append(f"Revisions: {meta['revision']} | Edit Time: {meta.get('total_edit_time_min', 'N/A')} min")
            if meta.get("created_formatted") or meta.get("created"):
                lines.append(f"Created: {meta.get('created_formatted') or meta.get('created')}")
            if meta.get("modified_formatted") or meta.get("modified"):
                lines.append(f"Last Saved: {meta.get('modified_formatted') or meta.get('modified')}")

            # AI Tells and Clues
            clues = meta.get("clues", [])
            if clues:
                lines.append("")
                lines.append(f"Risk Level: {meta.get('risk_level', 'HIGH_RISK')}")
                lines.append(f"Verdict: {meta.get('verdict', '')}")
                lines.append("Detected Tells & Clues:")
                for c in clues:
                    lines.append(f" [!] {c}")
            else:
                lines.append(f"Risk Level: {meta.get('risk_level', 'CLEAN')}")
                lines.append("Detected Tells: None (no automated generator fingerprints found)")

        # Action / Cleansing Note
        action = data.get("action")
        if action:
            lines.append("")
            lines.append(f"Action: {action}")

        # 2. AI Content Detection Section
        if not skip_ai and "consensus_percentage" in data:
            verdict = data.get("verdict", "Unknown").upper()
            consensus_pct = data.get("consensus_percentage", 0.0)
            votes = data.get("votes", {})
            ai_votes = votes.get("ai", 0)
            human_votes = votes.get("human", 0)
            total_valid = votes.get("total_valid_services", 0)
            doc_stats = data.get("document_stats", {})
            words = doc_stats.get("words", 0)
            chars = doc_stats.get("characters", 0)
            spread = data.get("score_spread", {})

            lines.append("")
            lines.append("--- AI Content Detection ---")
            lines.append(f"Verdict: {verdict}")
            lines.append(f"Overall AI Score: {consensus_pct}%")
            lines.append(f"Votes: {ai_votes} AI vs {human_votes} Human (of {total_valid} detectors)")
            lines.append(f"Score Range: {spread.get('min', 0) * 100:.1f}% to {spread.get('max', 0) * 100:.1f}%")
            lines.append(f"Text Size: {words} words | {chars} characters")
            lines.append("")
            lines.append("Individual Detectors:")

            for s in data.get("services", []):
                name = s.get("service_name", "Service")
                status = s.get("status")
                prob = s.get("ai_probability")
                label = s.get("label", "")
                lat = s.get("latency_sec", 0.0)
                if status == "success" and prob is not None:
                    lines.append(f"- {name}: {prob * 100:.1f}% ({label}) [{lat:.2f}s]")
                else:
                    lines.append(f"- {name}: {status} [{lat:.2f}s]")

        return "\n".join(lines)

    except subprocess.TimeoutExpired:
        return "Error: AI Checker timed out while querying remote services."
    except Exception as e:
        return f"Error executing AI Checker: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="Hermes AI Content Checker & Forensics")
    parser.add_argument("query", nargs="*", help="Text string to evaluate.")
    parser.add_argument("-f", "--file", type=str, default=None, help="Document file to evaluate.")
    parser.add_argument("--skip-ai", action="store_true", help="Fast metadata check only (skip AI models).")
    parser.add_argument("--cleanse", type=str, default=None, help="Path to save cleansed document.")
    parser.add_argument("--author", type=str, default=None, help="Target author name for cleansing.")

    args = parser.parse_args()

    if args.file:
        res = run_ai_checker(
            target_file=args.file,
            skip_ai=args.skip_ai,
            cleanse_target=args.cleanse,
            author=args.author
        )
    elif args.query:
        query_text = " ".join(args.query)
        res = run_ai_checker(target_text=query_text)
    else:
        res = (
            "Usage:\n"
            "  /aicheck <text to check>\n"
            "  /aicheck -f <path_to_doc>           (AI + Metadata)\n"
            "  /aicheck -f <path_to_doc> --skip-ai (Metadata only, 0.1s)\n"
            "  /aicheck -f <in_file> --cleanse <out_file> --author \"Author Name\""
        )

    print(res)


if __name__ == "__main__":
    main()
