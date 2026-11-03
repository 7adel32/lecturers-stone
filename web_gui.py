"""
The Lecturer's Stone - Interactive Web GUI.
Default operation evaluates both AI text authorship across multiple detection models
and container metadata forensics (.docx, .xlsx, .pptx, .pdf).
"""

import sys
from pathlib import Path
import gradio as gr

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from checker_hub import AICheckerHub
from document_parser import extract_text_from_file
from metadata_forensics import inspect_metadata, sanitize_metadata, super_sanitize_metadata, DEFAULT_AUTHOR

hub = AICheckerHub()


def format_metadata_html(meta: dict) -> str:
    if not meta or not meta.get("has_metadata"):
        return """
        <div style="background-color: #1e1e2e; border: 1px solid #313244; border-radius: 12px; padding: 16px; margin-bottom: 15px; color: #cdd6f4; font-family: sans-serif;">
            <div style="font-weight: bold; font-size: 15px; color: #89b4fa; margin-bottom: 6px;">Container Metadata Forensics</div>
            <div style="font-size: 13px; color: #a6adc8;">No container metadata or plain text file.</div>
        </div>
        """

    risk = meta.get("risk_level", "CLEAN")
    if risk == "HIGH_RISK":
        risk_color = "#e74c3c"
        badge_bg = "rgba(231, 76, 60, 0.2)"
    elif risk == "STANDARD":
        risk_color = "#2ecc71"
        badge_bg = "rgba(46, 204, 113, 0.2)"
    else:
        risk_color = "#89b4fa"
        badge_bg = "rgba(137, 180, 250, 0.2)"

    clues = meta.get("clues", [])
    if clues:
        clues_html = "".join([f"<li style='color: #e74c3c; margin-top: 4px;'>[!] {c}</li>" for c in clues])
        clues_block = f"<ul style='margin: 8px 0 0 16px; padding: 0; font-size: 13px;'>{clues_html}</ul>"
    else:
        clues_block = "<div style='font-size: 13px; color: #a6adc8; margin-top: 6px;'>None (No automated generator fingerprints detected)</div>"

    created = meta.get("created") or "N/A"
    modified = meta.get("modified") or "N/A"
    app = meta.get("application") or "N/A"
    if meta.get("app_version"):
        app += f" (v{meta['app_version']})"

    rev = meta.get("revision") or "N/A"
    edit_time = f"{meta['total_edit_time_min']} min" if meta.get("total_edit_time_min") else "N/A"

    all_auths = meta.get("all_authors", [])
    authors_str = ", ".join(all_auths) if all_auths else "[None / Stripped]"

    return f"""
    <div style="background-color: #1e1e2e; border: 1px solid #313244; border-radius: 12px; padding: 18px; margin-bottom: 15px; color: #cdd6f4; font-family: sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #313244; padding-bottom: 8px;">
            <span style="font-weight: bold; font-size: 16px; color: #89b4fa;">Metadata Forensics & Container Environment</span>
            <span style="background-color: {badge_bg}; color: {risk_color}; border: 1px solid {risk_color}; padding: 3px 10px; border-radius: 16px; font-weight: bold; font-size: 12px;">
                {risk}: {meta.get('verdict')}
            </span>
        </div>
        <div style="margin-bottom: 10px; font-size: 14px; padding-bottom: 8px; border-bottom: 1px solid #313244;">
            <span style="color: #a6adc8;">All Identified Authors / Owners:</span> <b style="color: #f5c2e7;">{authors_str}</b>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
            <div><span style="color: #a6adc8;">Primary Creator:</span> <b>{meta.get('creator') or '[None / Stripped]'}</b></div>
            <div><span style="color: #a6adc8;">Last Modifier:</span> <b>{meta.get('last_modified_by') or '[None / Stripped]'}</b></div>
            <div><span style="color: #a6adc8;">Application / Tool:</span> <b>{app}</b></div>
            <div><span style="color: #a6adc8;">Revision / Edit Time:</span> <b>Rev {rev} | {edit_time}</b></div>
            <div><span style="color: #a6adc8;">Created Date:</span> <b>{created}</b></div>
            <div><span style="color: #a6adc8;">Modified Date:</span> <b>{modified}</b></div>
        </div>
        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #313244;">
            <span style="color: #a6adc8; font-size: 13px; font-weight: bold;">Programmatic Clues:</span>
            {clues_block}
        </div>
    </div>
    """


def analyze_input(text_input, file_input, services_selected, sapling_key):
    meta_info = None
    if file_input is not None:
        file_path = file_input.name if hasattr(file_input, "name") else str(file_input)
        path_obj = Path(file_path)
        try:
            content = extract_text_from_file(path_obj)
            source_desc = f"File: {path_obj.name}"
            if path_obj.suffix.lower() in [".docx", ".xlsx", ".xlsm", ".pptx", ".pdf"]:
                meta_info = inspect_metadata(path_obj)
        except Exception as e:
            return (
                f"<div style='color:red; font-weight:bold;'>Error reading file: {e}</div>",
                "",
                {},
                "",
                ""
            )
    elif text_input and text_input.strip():
        content = text_input.strip()
        source_desc = "Direct Text Input"
    else:
        return (
            "<div style='color:#e67e22; font-weight:bold;'>Please enter text or upload a document (.docx, .xlsx, .pptx, .pdf, .txt).</div>",
            "",
            {},
            "",
            ""
        )

    hub.sapling_api_key = sapling_key if sapling_key and sapling_key.strip() else None
    results = hub.analyze_text(content, services=services_selected)

    consensus_pct = results["consensus_percentage"]
    verdict = results["verdict"]
    ai_votes = results["votes"]["ai"]
    human_votes = results["votes"]["human"]
    total_valid = results["votes"]["total_valid_services"]

    if consensus_pct >= 70:
        badge_color = "#e74c3c"
    elif consensus_pct >= 50:
        badge_color = "#e67e22"
    elif consensus_pct >= 35:
        badge_color = "#f1c40f"
    else:
        badge_color = "#2ecc71"

    verdict_html = f"""
    <div style="background-color: #1e1e2e; border: 1px solid #313244; border-radius: 12px; padding: 20px; color: #cdd6f4; font-family: sans-serif; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 14px; color: #a6adc8;">Source: <b>{source_desc}</b> ({results['document_stats']['words']} words, {results['document_stats']['characters']} chars)</span>
            <span style="background-color: {badge_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 13px;">
                {verdict}
            </span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 15px;">
            <h2 style="margin: 0; font-size: 38px; color: {badge_color};">{consensus_pct}%</h2>
            <span style="font-size: 18px; color: #bac2de;">Consensus AI Probability</span>
        </div>
        <div style="margin-top: 14px; background: #313244; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: {badge_color}; height: 100%; width: {consensus_pct}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 13px; color: #a6adc8;">
            <span>Consensus: <b>{ai_votes} AI</b> vs <b>{human_votes} Human</b> (out of {total_valid} engines)</span>
            <span>Spread: <b>{results['score_spread']['min']*100:.1f}%</b> - <b>{results['score_spread']['max']*100:.1f}%</b></span>
        </div>
    </div>
    """

    meta_html = format_metadata_html(meta_info)

    service_scores = {}
    table_rows = []
    for s in results["services"]:
        s_name = s.get("service_name")
        prob = s.get("ai_probability")
        status = s.get("status")
        lat = s.get("latency_sec", 0.0)
        label = s.get("label", "Unknown")

        if status == "success" and prob is not None:
            service_scores[s_name] = prob
            pct_val = f"{prob * 100:.1f}%"
            badge = f"<span style='color: {'#e74c3c' if prob >= 0.5 else '#2ecc71'}; font-weight: bold;'>{label}</span>"
        else:
            pct_val = "N/A"
            badge = f"<span style='color: #7f8c8d;'>{status}</span>"

        table_rows.append(f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #313244;"><b>{s_name}</b></td>
            <td style="padding: 10px; border-bottom: 1px solid #313244;">{badge}</td>
            <td style="padding: 10px; border-bottom: 1px solid #313244; font-family: monospace;">{pct_val}</td>
            <td style="padding: 10px; border-bottom: 1px solid #313244; color: #a6adc8;">{lat}s</td>
        </tr>
        """)

    table_html = f"""
    <table style="width: 100%; border-collapse: collapse; margin-top: 10px; color: #cdd6f4; font-size: 14px;">
        <thead>
            <tr style="text-align: left; background-color: #181825; color: #89b4fa;">
                <th style="padding: 10px; border-bottom: 2px solid #313244;">Service Name</th>
                <th style="padding: 10px; border-bottom: 2px solid #313244;">Verdict</th>
                <th style="padding: 10px; border-bottom: 2px solid #313244;">AI Confidence</th>
                <th style="padding: 10px; border-bottom: 2px solid #313244;">Latency</th>
            </tr>
        </thead>
        <tbody>
            {"".join(table_rows)}
        </tbody>
    </table>
    """

    preview_text = content[:1000] + ("..." if len(content) > 1000 else "")
    return verdict_html, meta_html, service_scores, table_html, preview_text


def sanitize_action(file_input, author_name):
    if file_input is None:
        return None, "No file uploaded to sanitize."
    file_path = file_input.name if hasattr(file_input, "name") else str(file_input)
    author = author_name if author_name and author_name.strip() else DEFAULT_AUTHOR
    out_file = sanitize_metadata(file_path, author=author, keep_created_date=True)
    return out_file, f"Sanitized: Author set to '{author}', old creation date preserved."


def nuke_action(file_input):
    if file_input is None:
        return None, "No file uploaded to nuke."
    file_path = file_input.name if hasattr(file_input, "name") else str(file_input)
    out_file = super_sanitize_metadata(file_path)
    return out_file, "Super-Sanitized: All metadata completely wiped. File is structurally valid."


def create_ui():
    with gr.Blocks(title="The Lecturer's Stone") as demo:
        gr.Markdown(
            """
            # The Lecturer's Stone
            ### Multi-Service AI Content Detection, Container Metadata Forensics, and Sanitizer
            Evaluates both text authorship probability across independent models and container **metadata forensics** (.docx, .xlsx, .pptx, .pdf).
            """
        )

        with gr.Row():
            with gr.Column(scale=5):
                file_input = gr.File(
                    label="Upload Document (.docx, .xlsx, .pptx, .pdf, .txt, .md)",
                    file_types=[".docx", ".xlsx", ".xlsm", ".pptx", ".pdf", ".txt", ".md"],
                    file_count="single"
                )
                text_input = gr.Textbox(
                    label="Or Enter Plain Text String",
                    placeholder="Paste an essay, article, paragraph, or sentence to evaluate for AI authorship...",
                    lines=6
                )

                with gr.Accordion("Sanitize & Metadata Tools", open=False):
                    author_name_input = gr.Textbox(
                        label="Author Name for Sanitization",
                        value=DEFAULT_AUTHOR
                    )
                    with gr.Row():
                        sanitize_btn = gr.Button("Sanitize Metadata (Preserve Date)", variant="secondary")
                        nuke_btn = gr.Button("Super-Sanitize / Nuke All Metadata", variant="stop")
                    cleaned_file_output = gr.File(label="Download Cleaned Document", interactive=False)
                    action_status = gr.Markdown("")

                with gr.Accordion("Engine Selection & Settings", open=False):
                    services_checkbox = gr.CheckboxGroup(
                        choices=["local_deberta", "radar", "fakespot", "yugamj", "piratexx", "heuristic", "sapling"],
                        value=["local_deberta", "radar", "fakespot", "yugamj", "piratexx", "heuristic"],
                        label="Active Detection Services"
                    )
                    sapling_key_input = gr.Textbox(
                        label="Optional Sapling AI API Key",
                        placeholder="Leave empty unless you have a Sapling API key",
                        type="password"
                    )

                with gr.Row():
                    check_btn = gr.Button("Analyze AI & Metadata", variant="primary", size="lg")
                    clear_btn = gr.ClearButton([text_input, file_input], value="Clear Input")

            with gr.Column(scale=6):
                verdict_output = gr.HTML(label="Consensus Verdict")
                meta_output = gr.HTML(label="Metadata Forensics")
                scores_chart = gr.Label(label="AI Detection Probabilities by Engine", num_top_classes=6)
                breakdown_table = gr.HTML(label="Detailed Service Breakdown")

                with gr.Accordion("Extracted Document Content Preview", open=False):
                    text_preview = gr.Textbox(label="Extracted Text", lines=6, interactive=False)

        check_btn.click(
            fn=analyze_input,
            inputs=[text_input, file_input, services_checkbox, sapling_key_input],
            outputs=[verdict_output, meta_output, scores_chart, breakdown_table, text_preview]
        )

        sanitize_btn.click(
            fn=sanitize_action,
            inputs=[file_input, author_name_input],
            outputs=[cleaned_file_output, action_status]
        )

        nuke_btn.click(
            fn=nuke_action,
            inputs=[file_input],
            outputs=[cleaned_file_output, action_status]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7865)
