"""
The Lecturer's Stone - Interactive Web GUI.
Default operation evaluates both AI text authorship across multiple detection models
and container metadata forensics (.docx, .xlsx, .pptx, .pdf) with metadata cleansing.
"""

import base64
import html
import sys
from pathlib import Path

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

import gradio as gr

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from checker_hub import AICheckerHub
from document_parser import extract_text_from_file
from metadata_forensics import inspect_metadata, cleanse_metadata, DEFAULT_AUTHOR
from local_detector import is_local_available

hub = AICheckerHub()

CUSTOM_CSS = """
:root {
    --stone-ruby: #d33538;
    --stone-amber: #ffe082;
    --stone-card-bg: #ffffff;
    --stone-card-border: #e2e8f0;
    --stone-divider: #f1f5f9;
    --stone-text-main: #0f172a;
    --stone-text-body: #334155;
    --stone-text-sub: #475569;
    --stone-text-muted: #64748b;
    --stone-progress-bg: #f1f5f9;
    --stone-table-th-bg: #f8fafc;
    --stone-table-hover: #f8fafc;
    --stone-safe-color: #475569;
    --stone-safe-badge-border: #94a3b8;
    --stone-safe-bar: #64748b;
}

/* Global unified 8px radius across interactive components */
.gradio-container, .block, .panel, .form, input, textarea, button, select {
    border-radius: 8px !important;
}

/* Gradio Container styling with UI gradient glow */
.gradio-container {
    width: 94% !important;
    max-width: 1680px !important;
    margin: 24px auto !important;
    padding: 28px 36px !important;
    border-radius: 14px !important;
    transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease !important;
}

/* Light mode container glow with #d33538 and #ffe082 */
html:not(.dark) .gradio-container {
    box-shadow: 0 4px 25px -4px rgba(211, 53, 56, 0.09), 0 0 15px -2px rgba(255, 224, 130, 0.14) !important;
    border: 1px solid #e2e8f0 !important;
    background-color: #ffffff !important;
}

html:not(.dark), body:not(.dark) {
    background-color: #f8fafc !important;
}

/* Dark mode styling and radiant UI gradient glow (pure neutral charcoal, zero blue tint) */
.dark, [data-theme="dark"] {
    color-scheme: dark !important;
    --body-background-fill: #111113 !important;
    --body-text-color: #f4f4f5 !important;
    --block-background-fill: #18181b !important;
    --block-border-color: #27272a !important;
    --background-fill-primary: #18181b !important;
    --background-fill-secondary: #111113 !important;
    --border-color-primary: #27272a !important;
    background-color: #111113 !important;
    color: #f4f4f5 !important;

    --stone-card-bg: #18181b;
    --stone-card-border: #27272a;
    --stone-divider: #27272a;
    --stone-text-main: #f4f4f5;
    --stone-text-body: #d4d4d8;
    --stone-text-sub: #a1a1aa;
    --stone-text-muted: #71717a;
    --stone-progress-bg: #222226;
    --stone-table-th-bg: #1e1e22;
    --stone-table-hover: #26262a;
    --stone-safe-color: #e4e4e7;
    --stone-safe-badge-border: #71717a;
    --stone-safe-bar: #a1a1aa;
}

.dark html, .dark body {
    background-color: #111113 !important;
}

.dark .gradio-container {
    box-shadow: 0 0 50px -6px rgba(211, 53, 56, 0.38), 0 0 25px -3px rgba(255, 224, 130, 0.28) !important;
    border: 1px solid rgba(211, 53, 56, 0.35) !important;
    background-color: #111113 !important;
}

/* Strip all intermediate Gradio wrappers to prevent double borders or background clashes */
.dark .gradio-container .contain,
.dark .gradio-container.gradio-container-6-30-0 .contain,
.gradio-container .contain,
.gradio-container .wrap,
.gradio-container .main,
.gradio-container .app,
.gradio-container > .main,
.gradio-container .main.app,
.gradio-container main.contain {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    max-width: 100% !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}

.gradio-container .block:has(> .html-container),
.block.hide-container,
.gradio-container .prose {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Hide standard theme toggles in footer / settings */
footer, .settings-btn, button[aria-label="Toggle theme"], button:has(.settings), .settings {
    display: none !important;
}

/* Accent Gradient on Primary Button with glow */
button.primary, .gradio-container button.primary {
    background: linear-gradient(135deg, #d33538 0%, #ea580c 45%, #ffe082 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 3px 12px rgba(211, 53, 56, 0.35), 0 0 10px rgba(255, 224, 130, 0.2) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button.primary:hover, .gradio-container button.primary:hover {
    filter: brightness(1.1) !important;
    box-shadow: 0 4px 18px rgba(211, 53, 56, 0.5), 0 0 18px rgba(255, 224, 130, 0.35) !important;
    transform: translateY(-1px) !important;
}

button.primary:active, .gradio-container button.primary:active {
    transform: translateY(0) !important;
}

/* Interactive Stone Logo Secret Button */
#stone-toggle-wrap {
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.25s ease;
}

#stone-toggle-wrap:hover #stone-img {
    transform: scale(1.08) rotate(1deg);
    filter: drop-shadow(0 0 24px rgba(211, 53, 56, 0.85)) drop-shadow(0 0 14px rgba(255, 224, 130, 0.8)) !important;
}

#stone-toggle-wrap:active #stone-img {
    transform: scale(0.95);
}

/* Accent Header Subtitle Gradient */
.stone-subtitle {
    font-size: 14.5px;
    font-weight: 700;
    margin-top: 4px;
    background: linear-gradient(90deg, #d33538 0%, #b45309 60%, #9a3412 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.dark .stone-subtitle {
    background: linear-gradient(90deg, #f87171 0%, #fde047 50%, #ffe082 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* UI Accent Gradient Bar */
.stone-glow-bar {
    height: 3px;
    width: 100%;
    background: linear-gradient(90deg, #d33538 0%, #ea580c 50%, #ffe082 100%);
    border-radius: 3px;
    box-shadow: 0 0 14px rgba(211, 53, 56, 0.55), 0 0 8px rgba(255, 224, 130, 0.65);
    margin-bottom: 16px;
}

/* Eliminate double container borders on custom HTML card blocks */
.clean-html-card {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* Custom Cards (Verdict & Forensics) */
.verdict-card, .metadata-card {
    background-color: var(--stone-card-bg) !important;
    border: 1px solid var(--stone-card-border) !important;
    border-radius: 8px !important;
    color: var(--stone-text-main) !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    transition: background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease !important;
}

.dark .verdict-card {
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid rgba(211, 53, 56, 0.35) !important;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 16px -4px rgba(211, 53, 56, 0.2) !important;
}

.dark .metadata-card {
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid #27272a !important;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 16px -4px rgba(211, 53, 56, 0.18) !important;
}

/* Transparent verdict badges */
.verdict-badge, .risk-badge, .service-badge {
    background: transparent !important;
    background-color: transparent !important;
}

/* Processing and loading indicators in Philosopher's Stone orange */
:root, .dark, [data-theme="dark"] {
    --loader-color: #f97316 !important;
    --color-accent: #f97316 !important;
    --color-accent-soft: rgba(249, 115, 22, 0.2) !important;
    --loading-indicator-color: #f97316 !important;
}

.loading,
.loader,
.loading-indicator,
.loading-spinner,
.spinner,
.spinner-button,
.loading-overlay,
.node-status-spinner,
.loading-dot {
    color: #f97316 !important;
    border-top-color: #f97316 !important;
    fill: #f97316 !important;
    stroke: #f97316 !important;
}

.loading svg,
.loader svg,
.loading-spinner svg,
.spinner svg,
.animate-spin {
    color: #f97316 !important;
    fill: #f97316 !important;
    stroke: #f97316 !important;
}

.loading svg circle,
.loader svg circle,
.animate-spin circle {
    stroke: #f97316 !important;
}

.loading svg path,
.loader svg path,
.animate-spin path {
    fill: #f97316 !important;
}

.progress-bar,
progress,
progress::-webkit-progress-value,
progress::-moz-progress-bar,
.progress-bar-wrap .progress-bar {
    background-color: #f97316 !important;
    background: linear-gradient(90deg, #ea580c 0%, #f97316 50%, #ffe082 100%) !important;
}

.progress-text,
.loading-text,
.meta-text {
    color: #f97316 !important;
    font-weight: 600 !important;
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

/* Service Table Card Container */
.service-table-card {
    border: 1px solid var(--stone-card-border) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    background: var(--stone-card-bg) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    margin-top: 4px;
    transition: background-color 0.25s ease, border-color 0.25s ease !important;
}

.dark .service-table-card {
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 16px -4px rgba(211, 53, 56, 0.18) !important;
}

.service-table-card table {
    width: 100% !important;
    border-collapse: collapse !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 13px !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    table-layout: fixed !important;
}

.service-table-card th {
    padding: 9px 10px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    color: var(--stone-text-sub) !important;
    background-color: var(--stone-table-th-bg) !important;
    border: none !important;
    border-bottom: 1px solid var(--stone-card-border) !important;
    text-align: left !important;
}

.service-table-card td {
    padding: 9px 10px !important;
    border: none !important;
    border-bottom: 1px solid var(--stone-divider) !important;
    color: var(--stone-text-main) !important;
    vertical-align: middle !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

.service-table-card tr:last-child td {
    border-bottom: none !important;
}

.service-table-card tr:hover td {
    background-color: var(--stone-table-hover) !important;
}

/* Dark mode inputs, textareas, dropzones (neutral obsidian charcoal) */
.dark textarea, .dark input[type="text"] {
    background-color: #18181b !important;
    color: #f4f4f5 !important;
    border-color: #27272a !important;
}

.dark .file-preview, .dark [data-testid="file-upload"], .dark .upload_zone {
    background-color: #18181b !important;
    border-color: #27272a !important;
    color: #d4d4d8 !important;
}

.dark .label-wrap, .dark .gr-accordion {
    background-color: #18181b !important;
    border-color: #27272a !important;
    color: #f4f4f5 !important;
}

.dark button:not(.primary) {
    background-color: #222226 !important;
    color: #e4e4e7 !important;
    border-color: #333338 !important;
}

.dark button:not(.primary):hover {
    background-color: #2a2a30 !important;
    border-color: #44444c !important;
}
"""

HEAD_SCRIPT = """
<script>
    (function() {
        const mediaQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

        function applyStoneTheme(theme) {
            const isDark = theme === 'dark';
            if (isDark) {
                document.documentElement.classList.add('dark');
                document.body.classList.add('dark');
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.classList.remove('dark');
                document.body.classList.remove('dark');
                document.documentElement.setAttribute('data-theme', 'light');
            }
            try {
                localStorage.setItem('lecturers_stone_theme', theme);
                localStorage.setItem('color-theme', theme);
                localStorage.setItem('gradio-theme', theme);
            } catch (e) {}
        }

        window.toggleStoneTheme = function() {
            const currentlyDark = document.documentElement.classList.contains('dark') || document.body.classList.contains('dark');
            const targetTheme = currentlyDark ? 'light' : 'dark';
            try {
                localStorage.setItem('lecturers_stone_manual_override', 'true');
            } catch (e) {}
            applyStoneTheme(targetTheme);
        };

        function getPreferredTheme() {
            try {
                const manual = localStorage.getItem('lecturers_stone_manual_override');
                const saved = localStorage.getItem('lecturers_stone_theme');
                if (manual === 'true' && (saved === 'dark' || saved === 'light')) {
                    return saved;
                }
            } catch (e) {}

            // Listen to browser preferred color scheme
            if (mediaQuery && mediaQuery.matches) {
                return 'dark';
            }
            return 'light';
        }

        function initTheme() {
            const initialTheme = getPreferredTheme();
            applyStoneTheme(initialTheme);

            // Listen to dynamic changes from the browser
            if (mediaQuery) {
                mediaQuery.addEventListener('change', function(e) {
                    try {
                        const manual = localStorage.getItem('lecturers_stone_manual_override');
                        if (manual !== 'true') {
                            applyStoneTheme(e.matches ? 'dark' : 'light');
                        }
                    } catch (err) {}
                });
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initTheme);
        } else {
            initTheme();
        }
    })();
</script>
"""


def format_metadata_html(meta: dict) -> str:
    if not meta or not meta.get("has_metadata"):
        return """
        <div class="metadata-card" style="padding: 14px 16px; margin-bottom: 14px;">
            <div style="font-weight: 600; font-size: 14px; color: var(--stone-text-main); margin-bottom: 3px;">Container Metadata Forensics</div>
            <div style="font-size: 13px; color: var(--stone-text-muted);">No container metadata or plain text file.</div>
        </div>
        """

    risk = meta.get("risk_level", "CLEAN")
    if risk == "HIGH_RISK":
        risk_color = "#dc2626"
    elif risk == "STANDARD":
        risk_color = "var(--stone-safe-color, #e4e4e7)"
    else:
        risk_color = "#3b82f6"

    clues = meta.get("clues", [])
    if clues:
        clues_html = "".join([f"<li style='color: #b91c1c; margin-top: 4px; font-weight: 500;'>[!] {c}</li>" for c in clues])
        clues_block = f"<ul style='margin: 6px 0 0 16px; padding: 0; font-size: 13px;'>{clues_html}</ul>"
    else:
        clues_block = "<div style='font-size: 13px; color: var(--stone-text-muted); margin-top: 5px;'>None (No automated generator fingerprints detected)</div>"

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
    <div class="metadata-card" style="padding: 18px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid var(--stone-divider); padding-bottom: 8px;">
            <span style="font-weight: 700; font-size: 15px; color: var(--stone-text-main);">Metadata Forensics & Container Environment</span>
            <span class="risk-badge" style="background: transparent !important; background-color: transparent !important; color: {risk_color}; border: 1.5px solid {risk_color}; padding: 3px 10px; border-radius: 6px; font-weight: 600; font-size: 12px;">
                {risk}: {meta.get('verdict')}
            </span>
        </div>
        <div style="margin-bottom: 10px; font-size: 13.5px; padding-bottom: 8px; border-bottom: 1px solid var(--stone-divider);">
            <span style="color: var(--stone-text-muted); font-weight: 500;">All Identified Authors / Owners:</span> <b style="color: var(--stone-text-main); margin-left: 6px;">{authors_str}</b>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
            <div><span style="color: var(--stone-text-muted);">Primary Creator:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">{meta.get('creator') or '[None / Stripped]'}</b></div>
            <div><span style="color: var(--stone-text-muted);">Last Modifier:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">{meta.get('last_modified_by') or '[None / Stripped]'}</b></div>
            <div><span style="color: var(--stone-text-muted);">Application / Tool:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">{app}</b></div>
            <div><span style="color: var(--stone-text-muted);">Revision / Edit Time:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">Rev {rev} | {edit_time}</b></div>
            <div><span style="color: var(--stone-text-muted);">Created Date:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">{created}</b></div>
            <div><span style="color: var(--stone-text-muted);">Modified Date:</span> <b style="color: var(--stone-text-body); margin-left: 4px;">{modified}</b></div>
        </div>
        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid var(--stone-divider);">
            <span style="color: var(--stone-text-sub); font-size: 13px; font-weight: 600;">Programmatic Clues:</span>
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
        bar_color = "#64748b"
        pct_display = "N/A"
        progress_width = 0
        consensus_summary = "No active text classifiers evaluated (0 extractable words)"
        spread_summary = "N/A"
    else:
        if consensus_pct >= 70:
            badge_color = "#dc2626"
            bar_color = "#dc2626"
        elif consensus_pct >= 50:
            badge_color = "#ea580c"
            bar_color = "#ea580c"
        elif consensus_pct >= 35:
            badge_color = "#ca8a04"
            bar_color = "#ca8a04"
        else:
            badge_color = "var(--stone-safe-color, #e4e4e7)"
            bar_color = "var(--stone-safe-bar, #a1a1aa)"
        pct_display = f"{consensus_pct}%"
        progress_width = consensus_pct
        consensus_summary = f"Consensus: <b style='color: var(--stone-text-main);'>{ai_votes} AI</b> vs <b style='color: var(--stone-text-main);'>{human_votes} Human</b> (out of {total_valid} engines)"
        spread_summary = f"Spread: <b style='color: var(--stone-text-main);'>{results['score_spread']['min']*100:.1f}%</b> - <b style='color: var(--stone-text-main);'>{results['score_spread']['max']*100:.1f}%</b>"

    verdict_html = f"""
    <div class="verdict-card" style="padding: 20px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 12px;">
            <div style="min-width: 0; flex: 1;">
                <span style="font-size: 13px; color: var(--stone-text-muted); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(source_desc)}">
                    Source: <b style="color: var(--stone-text-main);">{html.escape(source_desc)}</b> ({results['document_stats']['words']} words, {results['document_stats']['characters']} chars)
                </span>
            </div>
            <div style="flex-shrink: 0; white-space: nowrap;">
                <span class="verdict-badge" style="background: transparent !important; background-color: transparent !important; color: {badge_color}; border: 1.5px solid {badge_color}; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; white-space: nowrap; display: inline-block;">
                    {verdict}
                </span>
            </div>
        </div>
        <div style="display: flex; align-items: baseline; gap: 12px;">
            <h2 style="margin: 0; font-size: 38px; font-weight: 800; color: {badge_color};">{pct_display}</h2>
            <span style="font-size: 16px; color: var(--stone-text-sub); font-weight: 500;">Consensus AI Probability</span>
        </div>
        <div style="margin-top: 12px; background: var(--stone-progress-bg); border-radius: 6px; height: 10px; overflow: hidden; border: 1px solid var(--stone-card-border);">
            <div style="background: {bar_color}; height: 100%; width: {progress_width}%; border-radius: 5px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12.5px; color: var(--stone-text-muted);">
            <span>{consensus_summary}</span>
            <span>{spread_summary}</span>
        </div>
    </div>
    """

    meta_html = format_metadata_html(meta_info)

    name_map = {
        "Local Desklib DeBERTa (RTX 5070 Ti / CUDA)": "Local Desklib DeBERTa",
        "TrustSafeAI RADAR (Adversarial Detector)": "TrustSafeAI RADAR",
        "SzegedAI (DeBERTa AI Detector)": "SzegedAI DeBERTa",
        "PirateXX RoBERTa Detector": "PirateXX RoBERTa",
        "Heuristic & Burstiness Engine": "Heuristic & Burstiness",
        "Fakespot AI Text Classifier": "Fakespot Classifier",
        "YugamJ LLM Text Detector": "YugamJ Detector"
    }

    table_rows = []
    for s in results["services"]:
        s_name = s.get("service_name", "Service")
        prob = s.get("ai_probability")
        status = s.get("status")
        lat = s.get("latency_sec", 0.0)
        label = s.get("label", "Unknown")
        display_name = name_map.get(s_name, s_name)

        # Exclude empty/none, insufficient text, and non-running services
        if status == "success" and prob is not None and label not in ["Empty Input", "Empty / None", "Empty", "None", "No Extractable Text", "Insufficient Text", "Insufficient Text (< 10 words)"]:
            pct_val = f"{prob * 100:.1f}%"
            badge_text_color = "#ef4444" if prob >= 0.5 else "var(--stone-safe-color, #e4e4e7)"
            badge_border_color = "#ef4444" if prob >= 0.5 else "var(--stone-safe-badge-border, #71717a)"
            badge = f"<span class='service-badge' style='background: transparent !important; background-color: transparent !important; color: {badge_text_color}; border: 1px solid {badge_border_color}; padding: 2px 7px; border-radius: 5px; font-weight: 600; font-size: 11px; white-space: nowrap; display: inline-block;'>{label}</span>"

            table_rows.append(f"""
            <tr>
                <td style="color: var(--stone-text-main); font-weight: 600; padding-left: 12px;" title="{html.escape(s_name)}">{html.escape(display_name)}</td>
                <td>{badge}</td>
                <td style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 600; color: var(--stone-text-body); text-align: right; overflow: visible; text-overflow: clip;">{pct_val}</td>
                <td style="color: var(--stone-text-muted); text-align: right; padding-right: 12px; overflow: visible; text-overflow: clip;">{lat:.2f}s</td>
            </tr>
            """)

    if table_rows:
        table_html = f"""
        <div class="service-table-card">
            <table>
                <colgroup>
                    <col style="width: 45%;">
                    <col style="width: 29%;">
                    <col style="width: 15%;">
                    <col style="width: 11%;">
                </colgroup>
                <thead>
                    <tr>
                        <th style="padding-left: 12px;">Service Name</th>
                        <th>Verdict</th>
                        <th style="text-align: right;">AI Confidence</th>
                        <th style="text-align: right; padding-right: 12px;">Latency</th>
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
        <div class="service-table-card" style="padding: 16px; text-align: center; color: var(--stone-text-muted); font-size: 13.5px;">
            No classifiers completed successfully for this input.
        </div>
        """

    return verdict_html, meta_html, table_html


def cleanse_action(file_input, author_name):
    if file_input is None:
        return None, "No file uploaded to cleanse."
    file_path = file_input.name if hasattr(file_input, "name") else str(file_input)
    author = author_name if author_name and author_name.strip() else DEFAULT_AUTHOR
    out_file = cleanse_metadata(file_path, author=author, keep_created_date=True)
    return out_file, f"Cleansed: Author set to '{author}', original creation date preserved."


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
        logo_html = f'<img id="stone-img" src="data:image/png;base64,{logo_b64}" alt="The Lecturer\'s Stone" style="height: 102px; width: auto; object-fit: contain; border-radius: 8px; filter: drop-shadow(0 0 12px rgba(211, 53, 56, 0.45)) drop-shadow(0 0 6px rgba(255, 224, 130, 0.35)); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); pointer-events: auto;" />'
    else:
        logo_html = ""

    header_html = f"""
    <div class="stone-glow-bar"></div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--stone-card-border);">
        <div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: var(--stone-text-main); letter-spacing: -0.02em;">The Lecturer's Stone</h1>
            <div class="stone-subtitle">AI detector, with metadata checking, and cleansing</div>
            <div style="font-size: 13px; color: var(--stone-text-muted); margin-top: 4px;">check probability of being AI written with a number of independant models and check metadata for usual AI tells.</div>
        </div>
        <div id="stone-toggle-wrap" onclick="window.toggleStoneTheme && window.toggleStoneTheme()" style="flex-shrink: 0; margin-left: 20px; cursor: pointer; user-select: none;">
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

    with gr.Blocks(title="The Lecturer's Stone") as demo:
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

                with gr.Accordion("Cleanse Document Metadata", open=False):
                    author_name_input = gr.Textbox(
                        label="Author Name for Cleansing",
                        value=DEFAULT_AUTHOR,
                        placeholder="e.g. Author or Student"
                    )
                    cleanse_btn = gr.Button("Cleanse Document Metadata (Preserve Date)", variant="secondary")
                    cleaned_file_output = gr.File(label="Download Cleansed Document", interactive=False)
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

        cleanse_btn.click(
            fn=cleanse_action,
            inputs=[file_input, author_name_input],
            outputs=[cleaned_file_output, action_status]
        )

        # ZeroGPU probe satisfies Hugging Face ZeroGPU startup scanner
        # while keeping real document and text analysis on CPU so users never hit GPU quota limits
        @spaces.GPU(duration=10)
        def _zerogpu_probe():
            return None

        _probe_btn = gr.Button("probe", visible=False)
        _probe_btn.click(fn=_zerogpu_probe)

    return demo, light_theme, CUSTOM_CSS, HEAD_SCRIPT


if __name__ == "__main__":
    import os
    demo, theme, css, head = create_ui()
    favicon = current_dir / "assets" / "icon.ico"
    fav_path = str(favicon) if favicon.is_file() else None

    is_hf = bool(os.environ.get("SPACE_ID"))
    if is_hf:
        demo.launch(theme=theme, css=css, head=head, favicon_path=fav_path)
    else:
        demo.launch(server_name="127.0.0.1", server_port=7865, theme=theme, css=css, head=head, favicon_path=fav_path)
