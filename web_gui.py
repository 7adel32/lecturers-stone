"""
The Lecturer's Stone - Interactive Web GUI (Clean Light Theme with Unified Radii).
Default operation evaluates both AI text authorship across multiple detection models
and container metadata forensics (.docx, .xlsx, .pptx, .pdf).
"""

import html
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

CUSTOM_CSS = """
/* Global unified 8px radius across interactive components */
.gradio-container, .block, .panel, .form, input, textarea, button, select {
    border-radius: 8px !important;
}

/* Eliminate double container borders on custom HTML card blocks */
.clean-html-card {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* Service Table Card Container with unified 8px radius */
.service-table-card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    margin-top: 4px;
}

.service-table-card table {
    width: 100%;
    border-collapse: collapse !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 13.5px;
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    table-layout: fixed;
}

.service-table-card th {
    padding: 12px 16px;
    font-weight: 600;
    font-size: 12.5px;
    color: #475569;
    background-color: #f8fafc;
    border: none !important;
    border-bottom: 1px solid #e2e8f0 !important;
    text-align: left;
}

.service-table-card td {
    padding: 12px 16px;
    border: none !important;
    border-bottom: 1px solid #f1f5f9 !important;
    color: #1e293b;
    vertical-align: middle;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.service-table-card tr:last-child td {
    border-bottom: none !important;
}

.service-table-card tr:hover td {
    background-color: #f8fafc;
}
"""


def format_metadata_html(meta: dict) -> str:
    if not meta or not meta.get("has_metadata"):
        return """
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; color: #334155; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="font-weight: 600; font-size: 14px; color: #1e293b; margin-bottom: 3px;">Container Metadata Forensics</div>
            <div style="font-size: 13px; color: #64748b;">No container metadata or plain text file.</div>
        </div>
        """

    risk = meta.get("risk_level", "CLEAN")
    if risk == "HIGH_RISK":
        risk_color = "#dc2626"
        badge_bg = "#fee2e2"
        badge_border = "#fca5a5"
    elif risk == "STANDARD":
        risk_color = "#16a34a"
        badge_bg = "#dcfce7"
        badge_border = "#86efac"
    else:
        risk_color = "#2563eb"
        badge_bg = "#dbeafe"
        badge_border = "#93c5fd"

    clues = meta.get("clues", [])
    if clues:
        clues_html = "".join([f"<li style='color: #b91c1c; margin-top: 4px; font-weight: 500;'>[!] {c}</li>" for c in clues])
        clues_block = f"<ul style='margin: 6px 0 0 16px; padding: 0; font-size: 13px;'>{clues_html}</ul>"
    else:
        clues_block = "<div style='font-size: 13px; color: #64748b; margin-top: 5px;'>None (No automated generator fingerprints detected)</div>"

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
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 14px; color: #1e293b; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
            <span style="font-weight: 700; font-size: 15px; color: #0f172a;">Metadata Forensics & Container Environment</span>
            <span style="background-color: {badge_bg}; color: {risk_color}; border: 1px solid {badge_border}; padding: 3px 10px; border-radius: 6px; font-weight: 600; font-size: 12px;">
                {risk}: {meta.get('verdict')}
            </span>
        </div>
        <div style="margin-bottom: 10px; font-size: 13.5px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9;">
            <span style="color: #64748b; font-weight: 500;">All Identified Authors / Owners:</span> <b style="color: #0f172a; margin-left: 6px;">{authors_str}</b>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
            <div><span style="color: #64748b;">Primary Creator:</span> <b style="color: #334155; margin-left: 4px;">{meta.get('creator') or '[None / Stripped]'}</b></div>
            <div><span style="color: #64748b;">Last Modifier:</span> <b style="color: #334155; margin-left: 4px;">{meta.get('last_modified_by') or '[None / Stripped]'}</b></div>
            <div><span style="color: #64748b;">Application / Tool:</span> <b style="color: #334155; margin-left: 4px;">{app}</b></div>
            <div><span style="color: #64748b;">Revision / Edit Time:</span> <b style="color: #334155; margin-left: 4px;">Rev {rev} | {edit_time}</b></div>
            <div><span style="color: #64748b;">Created Date:</span> <b style="color: #334155; margin-left: 4px;">{created}</b></div>
            <div><span style="color: #64748b;">Modified Date:</span> <b style="color: #334155; margin-left: 4px;">{modified}</b></div>
        </div>
        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #f1f5f9;">
            <span style="color: #475569; font-size: 13px; font-weight: 600;">Programmatic Clues:</span>
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
                f"<div style='color:#dc2626; font-weight:bold;'>Error reading file: {e}</div>",
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
            "<div style='color:#d97706; font-weight:bold;'>Please enter text or upload a document (.docx, .xlsx, .pptx, .pdf, .txt).</div>",
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
        badge_color = "#dc2626"
        badge_bg = "#fee2e2"
    elif consensus_pct >= 50:
        badge_color = "#ea580c"
        badge_bg = "#ffedd5"
    elif consensus_pct >= 35:
        badge_color = "#ca8a04"
        badge_bg = "#fef9c3"
    else:
        badge_color = "#16a34a"
        badge_bg = "#dcfce7"

    verdict_html = f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; color: #0f172a; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 13.5px; color: #64748b;">Source: <b style="color: #0f172a;">{source_desc}</b> ({results['document_stats']['words']} words, {results['document_stats']['characters']} chars)</span>
            <span style="background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12.5px;">
                {verdict}
            </span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 12px;">
            <h2 style="margin: 0; font-size: 38px; font-weight: 800; color: {badge_color};">{consensus_pct}%</h2>
            <span style="font-size: 16px; color: #475569; font-weight: 500;">Consensus AI Probability</span>
        </div>
        <div style="margin-top: 12px; background: #f1f5f9; border-radius: 6px; height: 10px; overflow: hidden; border: 1px solid #e2e8f0;">
            <div style="background: {badge_color}; height: 100%; width: {consensus_pct}%; border-radius: 5px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12.5px; color: #64748b;">
            <span>Consensus: <b style="color: #0f172a;">{ai_votes} AI</b> vs <b style="color: #0f172a;">{human_votes} Human</b> (out of {total_valid} engines)</span>
            <span>Spread: <b style="color: #0f172a;">{results['score_spread']['min']*100:.1f}%</b> - <b style="color: #0f172a;">{results['score_spread']['max']*100:.1f}%</b></span>
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
            badge = f"<span style='background-color: {'#fee2e2' if prob >= 0.5 else '#dcfce7'}; color: {'#dc2626' if prob >= 0.5 else '#16a34a'}; border: 1px solid {'#fca5a5' if prob >= 0.5 else '#86efac'}; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 11.5px; display: inline-block;'>{label}</span>"
        else:
            pct_val = "N/A"
            escaped_status = html.escape(str(status))
            badge = f"<span style='background-color: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; padding: 2px 8px; border-radius: 6px; font-weight: 500; font-size: 11.5px; display: inline-block;' title='{escaped_status}'>Unavailable</span>"

        table_rows.append(f"""
        <tr>
            <td style="color: #0f172a; font-weight: 600;">{s_name}</td>
            <td>{badge}</td>
            <td style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 600; color: #334155;">{pct_val}</td>
            <td style="color: #64748b;">{lat}s</td>
        </tr>
        """)

    table_html = f"""
    <div class="service-table-card">
        <table>
            <colgroup>
                <col style="width: 38%;">
                <col style="width: 28%;">
                <col style="width: 20%;">
                <col style="width: 14%;">
            </colgroup>
            <thead>
                <tr>
                    <th>Service Name</th>
                    <th>Verdict</th>
                    <th>AI Confidence</th>
                    <th>Latency</th>
                </tr>
            </thead>
            <tbody>
                {"".join(table_rows)}
            </tbody>
        </table>
    </div>
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
    light_theme = gr.themes.Default(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
        radius_size=gr.themes.sizes.radius_sm
    ).set(
        body_background_fill="#f8fafc",
        block_background_fill="#ffffff",
        block_border_color="#e2e8f0",
        block_shadow="0 1px 3px rgba(0,0,0,0.04)",
        block_radius="8px",
        container_radius="8px",
        input_radius="8px",
        button_large_radius="8px",
        button_medium_radius="8px",
        button_small_radius="8px",
        checkbox_border_radius="4px",
        table_radius="8px"
    )

    with gr.Blocks(title="The Lecturer's Stone", theme=light_theme, css=CUSTOM_CSS) as demo:
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
                verdict_output = gr.HTML(show_label=False, elem_classes=["clean-html-card"])
                meta_output = gr.HTML(show_label=False, elem_classes=["clean-html-card"])
                scores_chart = gr.Label(label="AI Detection Probabilities by Engine", num_top_classes=6)
                breakdown_table = gr.HTML(show_label=False, elem_classes=["clean-html-card"])

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
