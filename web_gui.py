"""
The Lecturer's Stone - Interactive Web GUI (Clean Light Theme with Unified Radii).
Default operation evaluates both AI text authorship across multiple detection models
and container metadata forensics (.docx, .xlsx, .pptx, .pdf).
"""

import base64
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
from local_detector import is_local_available

hub = AICheckerHub()

CUSTOM_CSS = """
/* Global unified 8px radius across interactive components */
.gradio-container, .block, .panel, .form, input, textarea, button, select {
    border-radius: 8px !important;
}

/* Force light theme and completely disable dark mode */
:root, html, body {
    color-scheme: light !important;
}

.dark, [data-theme="dark"] {
    --body-background-fill: #f8fafc !important;
    --body-text-color: #0f172a !important;
    --block-background-fill: #ffffff !important;
    --block-border-color: #e2e8f0 !important;
    --background-fill-primary: #ffffff !important;
    --background-fill-secondary: #f8fafc !important;
    background-color: #f8fafc !important;
    color: #0f172a !important;
}

/* Hide theme toggles in footer / settings */
footer, .settings-btn, button[aria-label="Toggle theme"], button:has(.settings), .settings {
    display: none !important;
}

/* Eliminate double container borders on custom HTML card blocks */
.clean-html-card {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* Override Gradio built-in prose black borders on tables and cells */
.gradio-container .prose table,
.gradio-container .prose tr,
.gradio-container .prose td,
.gradio-container .prose th,
.service-table-card table,
.service-table-card tr,
.service-table-card td,
.service-table-card th {
    border: none !important;
}

/* Service Table Card Container with unified 8px radius */
.service-table-card {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    background: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    margin-top: 4px;
}

.service-table-card table {
    width: 100% !important;
    border-collapse: collapse !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 13.5px !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    table-layout: fixed !important;
}

.service-table-card th {
    padding: 12px 16px !important;
    font-weight: 600 !important;
    font-size: 12.5px !important;
    color: #475569 !important;
    background-color: #f8fafc !important;
    border: none !important;
    border-bottom: 1px solid #e2e8f0 !important;
    text-align: left !important;
}

.service-table-card td {
    padding: 12px 16px !important;
    border: none !important;
    border-bottom: 1px solid #f1f5f9 !important;
    color: #1e293b !important;
    vertical-align: middle !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

.service-table-card tr:last-child td {
    border-bottom: none !important;
}

.service-table-card tr:hover td {
    background-color: #f8fafc !important;
}
"""

HEAD_SCRIPT = """
<script>
    document.documentElement.classList.remove('dark');
    const observer = new MutationObserver(() => {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
        }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
</script>
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

    created = meta.get("created_formatted") or meta.get("created") or "N/A"
    modified = meta.get("modified_formatted") or meta.get("modified") or "N/A"
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


def analyze_input(text_input, file_input, services_selected):
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
                ""
            )
    elif text_input and text_input.strip():
        content = text_input.strip()
        source_desc = "Direct Text Input"
    else:
        return (
            "<div style='color:#d97706; font-weight:bold;'>Please enter text or upload a document (.docx, .xlsx, .pptx, .pdf, .txt).</div>",
            "",
            ""
        )

    results = hub.analyze_text(content, services=services_selected)

    consensus_pct = results["consensus_percentage"]
    verdict = results["verdict"]
    ai_votes = results["votes"]["ai"]
    human_votes = results["votes"]["human"]
    total_valid = results["votes"]["total_valid_services"]

    if total_valid == 0:
        badge_color = "#64748b"
        badge_bg = "#f1f5f9"
        pct_display = "N/A"
        progress_width = 0
        consensus_summary = "No active text classifiers evaluated (0 extractable words)"
        spread_summary = "N/A"
    else:
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
        pct_display = f"{consensus_pct}%"
        progress_width = consensus_pct
        consensus_summary = f"Consensus: <b style='color: #0f172a;'>{ai_votes} AI</b> vs <b style='color: #0f172a;'>{human_votes} Human</b> (out of {total_valid} engines)"
        spread_summary = f"Spread: <b style='color: #0f172a;'>{results['score_spread']['min']*100:.1f}%</b> - <b style='color: #0f172a;'>{results['score_spread']['max']*100:.1f}%</b>"

    verdict_html = f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; color: #0f172a; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 13.5px; color: #64748b;">Source: <b style="color: #0f172a;">{source_desc}</b> ({results['document_stats']['words']} words, {results['document_stats']['characters']} chars)</span>
            <span style="background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12.5px;">
                {verdict}
            </span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 12px;">
            <h2 style="margin: 0; font-size: 38px; font-weight: 800; color: {badge_color};">{pct_display}</h2>
            <span style="font-size: 16px; color: #475569; font-weight: 500;">Consensus AI Probability</span>
        </div>
        <div style="margin-top: 12px; background: #f1f5f9; border-radius: 6px; height: 10px; overflow: hidden; border: 1px solid #e2e8f0;">
            <div style="background: {badge_color}; height: 100%; width: {progress_width}%; border-radius: 5px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12.5px; color: #64748b;">
            <span>{consensus_summary}</span>
            <span>{spread_summary}</span>
        </div>
    </div>
    """

    meta_html = format_metadata_html(meta_info)

    table_rows = []
    for s in results["services"]:
        s_name = s.get("service_name")
        prob = s.get("ai_probability")
        status = s.get("status")
        lat = s.get("latency_sec", 0.0)
        label = s.get("label", "Unknown")

        # Exclude empty/none and non-running services
        if status == "success" and prob is not None and label not in ["Empty Input", "Empty / None", "Empty", "None", "No Extractable Text"]:
            pct_val = f"{prob * 100:.1f}%"
            badge = f"<span style='background-color: {'#fee2e2' if prob >= 0.5 else '#dcfce7'}; color: {'#dc2626' if prob >= 0.5 else '#16a34a'}; border: 1px solid {'#fca5a5' if prob >= 0.5 else '#86efac'}; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 11.5px; display: inline-block;'>{label}</span>"

            table_rows.append(f"""
            <tr>
                <td style="color: #0f172a; font-weight: 600;">{s_name}</td>
                <td>{badge}</td>
                <td style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 600; color: #334155;">{pct_val}</td>
                <td style="color: #64748b;">{lat}s</td>
            </tr>
            """)

    if table_rows:
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
    else:
        table_html = """
        <div class="service-table-card" style="padding: 16px; text-align: center; color: #64748b; font-size: 13.5px;">
            No classifiers completed successfully for this input.
        </div>
        """

    return verdict_html, meta_html, table_html


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

    logo_path = current_dir / "assets" / "logo_stone.png"
    if not logo_path.is_file():
        logo_path = current_dir / "assets" / "logo.png"
    if logo_path.is_file():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="Logo" style="height: 102px; width: auto; object-fit: contain; border-radius: 8px;" />'
    else:
        logo_html = ""

    header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0;">
        <div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">The Lecturer's Stone</h1>
            <div style="font-size: 14.5px; font-weight: 600; color: #2563eb; margin-top: 4px;">Multi-Service AI Content Detection, Container Metadata Forensics, and Sanitizer</div>
            <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Evaluates both text authorship probability across independent models and container <b>metadata forensics</b> (.docx, .xlsx, .pptx, .pdf).</div>
        </div>
        <div style="flex-shrink: 0; margin-left: 20px;">
            {logo_html}
        </div>
    </div>
    """

    has_local = is_local_available()
    service_choices = []
    if has_local:
        service_choices.append("local_deberta")
    service_choices.extend(["radar", "fakespot", "yugamj", "piratexx", "heuristic"])
    service_defaults = list(service_choices)

    with gr.Blocks(title="The Lecturer's Stone", theme=light_theme, css=CUSTOM_CSS, head=HEAD_SCRIPT) as demo:
        gr.HTML(header_html)

        with gr.Row():
            with gr.Column(scale=1):
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
                        value=DEFAULT_AUTHOR,
                        placeholder="e.g. Author or Student"
                    )
                    with gr.Row():
                        sanitize_btn = gr.Button("Sanitize Metadata (Preserve Date)", variant="secondary")
                        nuke_btn = gr.Button("Super-Sanitize / Nuke All Metadata", variant="stop")
                    cleaned_file_output = gr.File(label="Download Cleaned Document", interactive=False)
                    action_status = gr.Markdown("")

                with gr.Accordion("Engine Selection & Settings", open=False):
                    services_checkbox = gr.CheckboxGroup(
                        choices=service_choices,
                        value=service_defaults,
                        label="Active Detection Services"
                    )

                with gr.Row():
                    check_btn = gr.Button("Analyze AI & Metadata", variant="primary", size="lg")
                    clear_btn = gr.Button("Clear Input", variant="secondary")

            with gr.Column(scale=1):
                verdict_output = gr.HTML(show_label=False, elem_classes=["clean-html-card"])
                meta_output = gr.HTML(show_label=False, elem_classes=["clean-html-card"])
                breakdown_table = gr.HTML(show_label=False, elem_classes=["clean-html-card"])

        def handle_file_change(file):
            if file is not None:
                return gr.update(interactive=False, placeholder="File uploaded. Text input is disabled while document is loaded. Click 'Clear Input' to type text.")
            return gr.update(interactive=True, placeholder="Paste an essay, article, paragraph, or sentence to evaluate for AI authorship...")

        def handle_clear():
            return (
                None,
                "",
                gr.update(interactive=True, placeholder="Paste an essay, article, paragraph, or sentence to evaluate for AI authorship..."),
                "",
                "",
                ""
            )

        file_input.change(
            fn=handle_file_change,
            inputs=[file_input],
            outputs=[text_input]
        )

        file_input.clear(
            fn=lambda: gr.update(interactive=True, placeholder="Paste an essay, article, paragraph, or sentence to evaluate for AI authorship..."),
            outputs=[text_input]
        )

        clear_btn.click(
            fn=handle_clear,
            outputs=[file_input, text_input, text_input, verdict_output, meta_output, breakdown_table]
        )

        check_btn.click(
            fn=analyze_input,
            inputs=[text_input, file_input, services_checkbox],
            outputs=[verdict_output, meta_output, breakdown_table]
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

    return demo, light_theme, CUSTOM_CSS


if __name__ == "__main__":
    demo, theme, css = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7865, theme=theme, css=css)
