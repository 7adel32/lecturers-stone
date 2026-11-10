"""
The Lecturer's Stone - Standalone CLI.
Analyzes raw strings and documents (.docx, .xlsx, .pptx, .pdf, .txt, .md).
Inspects container metadata, detects generator signatures (openpyxl, python-docx, etc.),
and provides one-click sanitization or super-sanitization (nuke).
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from document_parser import extract_text_from_file
from metadata_forensics import inspect_metadata, cleanse_metadata, DEFAULT_AUTHOR
sanitize_metadata = cleanse_metadata


def format_color_bar(probability: float, length: int = 24) -> str:
    filled = int(round(probability * length))
    empty = length - filled
    pct = round(probability * 100, 1)
    bar = "[" + "#" * filled + "-" * empty + f"] {pct}%"
    return bar


def print_metadata_section(meta: dict, action_note: str = None):
    print("\n" + "=" * 64)
    print(" THE LECTURER'S STONE - METADATA FORENSICS & CONTAINER")
    print("=" * 64)
    print(f"File:               {meta.get('file_name')} ({meta.get('file_type')})")

    all_auths = meta.get('all_authors', [])
    authors_str = ", ".join(all_auths) if all_auths else "[None / Stripped]"
    print(f"All Authors/Owners: {authors_str}")
    print(f"Primary Creator:    {meta.get('creator') or '[None / Stripped]'}")
    print(f"Last Modifier:      {meta.get('last_modified_by') or '[None / Stripped]'}")
    if meta.get('comment_authors'):
        print(f"Comment Authors:    {', '.join(meta['comment_authors'])}")
    if meta.get('contributors'):
        print(f"Contributors:       {', '.join(meta['contributors'])}")

    app_info = meta.get('application') or 'Unknown'
    if meta.get('app_version'):
        app_info += f" (v{meta.get('app_version')})"
    print(f"Application:        {app_info}")

    if meta.get('company'):
        print(f"Company:            {meta.get('company')}")
    if meta.get('manager'):
        print(f"Manager:            {meta.get('manager')}")

    created_str = meta.get('created_formatted') or meta.get('created') or '[None]'
    modified_str = meta.get('modified_formatted') or meta.get('modified') or '[None]'
    print(f"Created:            {created_str}")
    print(f"Modified:           {modified_str}")

    rev = meta.get('revision')
    edit_time = meta.get('total_edit_time_min')
    if rev or edit_time:
        rev_part = f"Rev {rev}" if rev else "Rev N/A"
        time_part = f"{edit_time} min edit time" if edit_time else "edit time N/A"
        print(f"Revision / Time:    {rev_part} | {time_part}")

    env_details = meta.get('environment_details', {})
    env_items = [f"{k}: {v}" for k, v in env_details.items() if k not in ["Application", "AppVersion", "Company", "Manager", "TotalTime"]]
    if env_items:
        print(f"Environment:        {', '.join(env_items[:3])}")

    risk = meta.get('risk_level', 'CLEAN')
    print(f"Forensic Risk:      [{risk}] {meta.get('verdict')}")
    clues = meta.get('clues', [])
    if clues:
        print("\nDetected Programmatic Clues:")
        for clue in clues:
            print(f" [!] {clue}")
    else:
        print("\nDetected Programmatic Clues: None (No automated generator fingerprints found)")

    if action_note:
        print("-" * 64)
        print(f"ACTION: {action_note}")

    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(
        description="The Lecturer's Stone - Multi-Service AI Content Detection, Container Metadata Forensics, and Cleanser."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", "--text", type=str, help="Plain text string to analyze.")
    group.add_argument(
        "-f", "--file", "--files",
        dest="files",
        nargs="+",
        help="Path(s) to document file(s), directory, or glob pattern (.txt, .md, .pdf, .docx, .xlsx, .pptx)."
    )

    # Metadata & Cleansing Options
    parser.add_argument("--cleanse", "--sanitize", dest="cleanse", nargs="?", const="", default=None, metavar="OUT_PATH",
                        help="Cleanse metadata (Creator/Modifier -> Author, preserves old creation date, cleans environment).")
    parser.add_argument("--author", type=str, default=DEFAULT_AUTHOR,
                        help=f"Author / Creator name to apply when cleansing (default: from LECTURERS_STONE_AUTHOR or '{DEFAULT_AUTHOR}').")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Skip AI NLP model analysis (perform metadata inspection / cleansing only).")

    # AI Detection Options
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    parser.add_argument("--services", nargs="+", choices=["local_deberta", "szegedai", "radar", "fakespot", "yugamj", "piratexx", "heuristic"], help="Specific services to check (default: all active).")
    parser.add_argument("--export", type=str, default=None, help="Export detailed report to file (e.g. report.json).")

    args = parser.parse_args()

    # Collect files if provided
    SUPPORTED_EXTENSIONS = {
        ".txt", ".md", ".markdown", ".rtf", ".rst", ".py", ".json", ".csv",
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm", ".xltx"
    }

    if args.files:
        collected_paths = []
        for item in args.files:
            p = Path(item)
            if p.is_file():
                collected_paths.append(p)
            elif p.is_dir():
                for f in sorted(p.iterdir()):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~$") and not f.name.startswith("."):
                        collected_paths.append(f)
            else:
                # Try glob expansion
                import glob
                matched = glob.glob(item)
                if matched:
                    for m in sorted(matched):
                        mp = Path(m)
                        if mp.is_file() and mp.suffix.lower() in SUPPORTED_EXTENSIONS:
                            collected_paths.append(mp)
                else:
                    print(f"Error: File or path not found: '{item}'", file=sys.stderr)
                    sys.exit(1)

        if not collected_paths:
            print("Error: No supported document files found to process.", file=sys.stderr)
            sys.exit(1)

        is_batch = len(collected_paths) > 1
        reports = []

        from checker_hub import AICheckerHub
        hub = None if args.skip_ai else AICheckerHub()

        for idx, file_path in enumerate(collected_paths, 1):
            source_name = file_path.name
            ext = file_path.suffix.lower()
            meta_info = None
            action_note = None

            if ext in [".docx", ".xlsx", ".xlsm", ".pptx", ".pdf"]:
                try:
                    meta_info = inspect_metadata(file_path)
                except Exception as e:
                    meta_info = {"error": f"Failed to inspect metadata: {e}"}

            # Document Cleansing
            if args.cleanse is not None:
                if is_batch:
                    # In batch mode, if out_target is a directory, place cleansed files inside;
                    # otherwise default to <stem>_cleansed<ext> alongside original.
                    if args.cleanse and Path(args.cleanse).is_dir():
                        out_target = Path(args.cleanse) / f"{file_path.stem}_cleansed{file_path.suffix}"
                    else:
                        out_target = file_path.parent / f"{file_path.stem}_cleansed{file_path.suffix}"
                else:
                    out_target = Path(args.cleanse) if args.cleanse else None

                try:
                    saved_to = cleanse_metadata(file_path, output_path=out_target, author=args.author, keep_created_date=True)
                    action_note = f"Cleansed file written to: {saved_to} (Author: {args.author}, Old creation date preserved)"
                except Exception as e:
                    action_note = f"Error during metadata cleansing: {e}"

            if args.skip_ai:
                file_report = {
                    "source": source_name,
                    "file_path": str(file_path.resolve()),
                    "metadata_forensics": meta_info,
                    "action": action_note
                }
                reports.append(file_report)
                if not args.json:
                    if meta_info:
                        print_metadata_section(meta_info, action_note=action_note)
                    elif action_note:
                        print(f"[{source_name}] {action_note}")
                continue

            try:
                text = extract_text_from_file(file_path)
            except Exception as e:
                err_msg = f"Error extracting text from file '{file_path}': {e}"
                if is_batch:
                    print(err_msg, file=sys.stderr)
                    reports.append({
                        "source": source_name,
                        "file_path": str(file_path.resolve()),
                        "error": err_msg,
                        "metadata_forensics": meta_info,
                        "action": action_note
                    })
                    continue
                else:
                    print(err_msg, file=sys.stderr)
                    sys.exit(1)

            if not text.strip():
                empty_msg = f"Warning: Input text in '{file_path.name}' is empty."
                if is_batch:
                    print(empty_msg, file=sys.stderr)
                    reports.append({
                        "source": source_name,
                        "file_path": str(file_path.resolve()),
                        "warning": "Empty document text",
                        "metadata_forensics": meta_info,
                        "action": action_note
                    })
                    continue
                else:
                    print(f"Error: Input text is empty.", file=sys.stderr)
                    sys.exit(1)

            results = hub.analyze_text(text, services=args.services)
            results["source"] = source_name
            results["file_path"] = str(file_path.resolve())
            if meta_info:
                results["metadata_forensics"] = meta_info
            if action_note:
                results["action"] = action_note

            reports.append(results)

            if not args.json:
                if is_batch:
                    print(f"\n>>> Processing ({idx}/{len(collected_paths)}): {source_name}")
                if meta_info:
                    print_metadata_section(meta_info, action_note=action_note)

                print("\n" + "=" * 64)
                print(" THE LECTURER'S STONE - AI CONTENT CONSENSUS REPORT")
                print("=" * 64)
                print(f"Source:        {source_name}")
                print(f"Document Size: {results['document_stats']['words']} words | {results['document_stats']['characters']} characters")
                print("-" * 64)
                print(f"VERDICT:       {results['verdict'].upper()}")
                score_str = format_color_bar(results['consensus_ai_probability']) if results['consensus_ai_probability'] is not None else "N/A"
                print(f"AI SCORE:      {score_str}")
                print(f"SERVICE VOTES: {results['votes']['ai']} AI vs {results['votes']['human']} Human (out of {results['votes']['total_valid_services']} active services)")
                print(f"SCORE RANGE:   {results['score_spread']['min'] * 100:.1f}% to {results['score_spread']['max'] * 100:.1f}% (Spread: {results['score_spread']['range'] * 100:.1f}%)")
                print("-" * 64)
                print("INDIVIDUAL SERVICE BREAKDOWN:")
                for s in results["services"]:
                    s_name = s.get("service_name")
                    status = s.get("status")
                    prob = s.get("ai_probability")
                    label = s.get("label")
                    lat = s.get("latency_sec", 0.0)
                    if status == "success" and prob is not None:
                        bar = format_color_bar(prob, length=15)
                        print(f" * {s_name:<36} {bar} | {label} ({lat}s)")
                    else:
                        print(f" * {s_name:<36} [STATUS: {status}] ({lat}s)")
                print("=" * 64 + "\n")

        # Output handling for files (single vs batch)
        final_output = reports if is_batch else reports[0]
        if args.json:
            output_data = json.dumps(final_output, indent=2)
            print(output_data)

        if args.export:
            export_path = Path(args.export)
            export_path.write_text(json.dumps(final_output, indent=2), encoding="utf-8")
            print(f"Report saved to {export_path.resolve()}", file=sys.stderr)

        return

    # Plain text branch
    source_name = "Raw Text Input"
    text = args.text
    if not text.strip():
        print("Error: Input text is empty.", file=sys.stderr)
        sys.exit(1)

    from checker_hub import AICheckerHub
    hub = AICheckerHub()
    results = hub.analyze_text(text, services=args.services)
    results["source"] = source_name

    if args.json:
        output_data = json.dumps(results, indent=2)
        print(output_data)
        if args.export:
            Path(args.export).write_text(output_data, encoding="utf-8")
            print(f"\nReport exported to {args.export}", file=sys.stderr)
        return

    # Formatted terminal report for AI detection
    print("\n" + "=" * 64)
    print(" THE LECTURER'S STONE - AI CONTENT CONSENSUS REPORT")
    print("=" * 64)
    print(f"Source:        {source_name}")
    print(f"Document Size: {results['document_stats']['words']} words | {results['document_stats']['characters']} characters")
    print("-" * 64)
    print(f"VERDICT:       {results['verdict'].upper()}")
    score_str = format_color_bar(results['consensus_ai_probability']) if results['consensus_ai_probability'] is not None else "N/A"
    print(f"AI SCORE:      {score_str}")
    print(f"SERVICE VOTES: {results['votes']['ai']} AI vs {results['votes']['human']} Human (out of {results['votes']['total_valid_services']} active services)")
    print(f"SCORE RANGE:   {results['score_spread']['min'] * 100:.1f}% to {results['score_spread']['max'] * 100:.1f}% (Spread: {results['score_spread']['range'] * 100:.1f}%)")
    print("-" * 64)
    print("INDIVIDUAL SERVICE BREAKDOWN:")
    for s in results["services"]:
        s_name = s.get("service_name")
        status = s.get("status")
        prob = s.get("ai_probability")
        label = s.get("label")
        lat = s.get("latency_sec", 0.0)
        if status == "success" and prob is not None:
            bar = format_color_bar(prob, length=15)
            print(f" * {s_name:<36} {bar} | {label} ({lat}s)")
        else:
            print(f" * {s_name:<36} [STATUS: {status}] ({lat}s)")

    print("=" * 64 + "\n")

    if args.export:
        export_path = Path(args.export)
        export_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Report saved to {export_path.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()
