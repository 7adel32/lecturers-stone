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

.stone-gh-link:hover {
    color: var(--stone-text-main) !important;
    border-color: var(--stone-ruby) !important;
    box-shadow: 0 0 8px rgba(211, 53, 56, 0.3) !important;
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

/* Hide Hugging Face floating space header pill */
#huggingface-space-header {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
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

# Base64 encoded 32x32 PNG favicon of the Philosopher's Stone
FAVICON_BASE64 = (
    "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"
)

FAVICON_DATA_URI = f"data:image/png;base64,{FAVICON_BASE64}"

FAVICON_HEAD = f"""
<link rel="icon" type="image/png" sizes="32x32" href="{FAVICON_DATA_URI}" />
<link rel="shortcut icon" type="image/png" href="{FAVICON_DATA_URI}" />
<link rel="apple-touch-icon" href="{FAVICON_DATA_URI}" />
<style>
#huggingface-space-header {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}}
</style>
<script>
    (function() {{
        const stoneIconUri = "{FAVICON_DATA_URI}";
        function forceStoneFavicon() {{
            try {{
                const links = document.querySelectorAll("link[rel*='icon']");
                if (!links.length) {{
                    const l = document.createElement("link");
                    l.rel = "shortcut icon";
                    l.type = "image/png";
                    l.href = stoneIconUri;
                    document.head.appendChild(l);
                }} else {{
                    links.forEach(function(l) {{
                        l.type = "image/png";
                        l.href = stoneIconUri;
                    }});
                }}
            }} catch (e) {{}}
        }}

        function removeHfHeader() {{
            try {{
                const hf = document.getElementById('huggingface-space-header');
                if (hf) hf.remove();
            }} catch (e) {{}}
        }}

        forceStoneFavicon();
        removeHfHeader();
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                forceStoneFavicon();
                removeHfHeader();
            }});
        }}
        window.addEventListener('load', function() {{
            forceStoneFavicon();
            removeHfHeader();
        }});

        // Keep favicon pinned and hide floating HF header against dynamic framework injections
        try {{
            const observer = new MutationObserver(function() {{
                document.querySelectorAll("link[rel*='icon']").forEach(function(l) {{
                    if (l.getAttribute("href") !== stoneIconUri) {{
                        l.type = "image/png";
                        l.href = stoneIconUri;
                    }}
                }});
                const hf = document.getElementById('huggingface-space-header');
                if (hf) hf.remove();
            }});
            if (document.head) {{
                observer.observe(document.head, {{ childList: true, subtree: true }});
            }}
            if (document.body) {{
                observer.observe(document.body, {{ childList: true, subtree: true }});
            }}
        }} catch (e) {{}}
    }})();
</script>
"""

HEAD_SCRIPT = FAVICON_HEAD + """
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


@spaces.GPU(duration=15)
def _run_zerogpu_analysis(content: str, services: list):
    return hub.analyze_text(content, services=services)

def _run_cpu_analysis(content: str, services: list):
    return hub.analyze_text(content, services=services)

def render_single_doc_result(results: dict, meta_info: dict, source_desc: str) -> tuple:
    consensus_pct = results.get("consensus_percentage", 0.0)
    verdict = results.get("verdict", "Unknown")
    votes = results.get("votes", {})
    ai_votes = votes.get("ai", 0)
    human_votes = votes.get("human", 0)
    total_valid = votes.get("total_valid_services", 0)

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

    doc_stats = results.get("document_stats", {"words": 0, "characters": 0})
    verdict_html = f"""
    <div class="verdict-card" style="padding: 20px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 12px;">
            <div style="min-width: 0; flex: 1;">
                <span style="font-size: 13px; color: var(--stone-text-muted); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(source_desc)}">
                    Source: <b style="color: var(--stone-text-main);">{html.escape(source_desc)}</b> ({doc_stats['words']} words, {doc_stats['characters']} chars)
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
        "Local Desklib DeBERTa (CUDA / GPU)": "Local Desklib DeBERTa",
        "Local Desklib DeBERTa (ZeroGPU / A10G)": "Local Desklib DeBERTa",
        "TrustSafeAI RADAR (Adversarial Detector)": "TrustSafeAI RADAR",
        "SzegedAI (DeBERTa AI Detector)": "SzegedAI DeBERTa",
        "PirateXX RoBERTa Detector": "PirateXX RoBERTa",
        "Heuristic & Burstiness Engine": "Heuristic & Burstiness",
        "Fakespot AI Text Classifier": "Fakespot Classifier",
        "YugamJ LLM Text Detector": "YugamJ Detector"
    }

    table_rows = []
    for s in results.get("services", []):
        s_name = s.get("service_name", "Service")
        prob = s.get("ai_probability")
        status = s.get("status")
        lat = s.get("latency_sec", 0.0)
        label = s.get("label", "Unknown")
        display_name = name_map.get(s_name, s_name)

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


def analyze_input(text_input, file_input, services_selected):
    # Normalize files to list
    files = []
    if file_input is not None:
        if isinstance(file_input, list):
            files = file_input
        else:
            files = [file_input]

    if files:
        import os
        is_hf = bool(os.environ.get("SPACE_ID"))
        use_gpu = is_hf and ("local_deberta" in (services_selected or []))

        # Check if single file
        if len(files) == 1:
            f = files[0]
            file_path = f.name if hasattr(f, "name") else str(f)
            path_obj = Path(file_path)
            meta_info = None
            try:
                content = extract_text_from_file(path_obj)
                source_desc = f"File: {path_obj.name}"
                if path_obj.suffix.lower() in [".docx", ".xlsx", ".xlsm", ".pptx", ".pdf"]:
                    meta_info = inspect_metadata(path_obj)
            except Exception as e:
                return (
                    f"<div style='color:#dc2626; font-weight:bold;'>Error reading file '{path_obj.name}': {e}</div>",
                    "",
                    ""
                )

            if use_gpu:
                results = _run_zerogpu_analysis(content, services=services_selected)
            else:
                results = _run_cpu_analysis(content, services=services_selected)

            return render_single_doc_result(results, meta_info, source_desc)

        # Batch Mode: Process each file
        batch_cards = []
        batch_meta = []
        batch_tables = []

        summary_rows = []
        for idx, f in enumerate(files, 1):
            file_path = f.name if hasattr(f, "name") else str(f)
            path_obj = Path(file_path)
            meta_info = None
            try:
                content = extract_text_from_file(path_obj)
                source_desc = f"{path_obj.name} ({idx}/{len(files)})"
                if path_obj.suffix.lower() in [".docx", ".xlsx", ".xlsm", ".pptx", ".pdf"]:
                    meta_info = inspect_metadata(path_obj)
            except Exception as e:
                summary_rows.append(f"<tr><td>{html.escape(path_obj.name)}</td><td style='color:#dc2626;'>Error: {e}</td><td>-</td><td>-</td></tr>")
                continue

            if use_gpu:
                results = _run_zerogpu_analysis(content, services=services_selected)
            else:
                results = _run_cpu_analysis(content, services=services_selected)

            v_html, m_html, t_html = render_single_doc_result(results, meta_info, source_desc)
            batch_cards.append(v_html)
            batch_meta.append(m_html)
            batch_tables.append(t_html)

            # Row for summary
            score = results.get("consensus_percentage", 0.0)
            score_color = "#dc2626" if score >= 70 else ("#ea580c" if score >= 50 else ("#ca8a04" if score >= 35 else "#10b981"))
            summary_rows.append(f"""
            <tr>
                <td style="font-weight: 600; color: var(--stone-text-main);">{html.escape(path_obj.name)}</td>
                <td><span style="border: 1px solid {score_color}; color: {score_color}; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">{results.get('verdict', 'N/A')}</span></td>
                <td style="font-weight: 700; color: {score_color}; text-align: right;">{score:.1f}%</td>
                <td style="color: var(--stone-text-muted); text-align: right;">{results.get('document_stats', {}).get('words', 0)} words</td>
            </tr>
            """)

        overview_html = f"""
        <div class="verdict-card" style="padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--stone-divider); padding-bottom: 8px;">
                <span style="font-weight: 700; font-size: 16px; color: var(--stone-text-main);">Batch Analysis Overview ({len(files)} Documents)</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="text-align: left; color: var(--stone-text-muted); border-bottom: 1px solid var(--stone-divider);">
                        <th style="padding: 6px 0;">Document</th>
                        <th>Verdict</th>
                        <th style="text-align: right;">AI Score</th>
                        <th style="text-align: right;">Words</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(summary_rows)}
                </tbody>
            </table>
        </div>
        """ + "".join(batch_cards)

        return overview_html, "".join(batch_meta), "".join(batch_tables)

    elif text_input and text_input.strip():
        content = text_input.strip()
        source_desc = "Direct Text Input"
        meta_info = None

        import os
        is_hf = bool(os.environ.get("SPACE_ID"))
        use_gpu = is_hf and ("local_deberta" in (services_selected or []))

        if use_gpu:
            results = _run_zerogpu_analysis(content, services=services_selected)
        else:
            results = _run_cpu_analysis(content, services=services_selected)

        return render_single_doc_result(results, meta_info, source_desc)

    else:
        return (
            "<div style='color:#d97706; font-weight:bold;'>Please enter text or upload document(s) (.docx, .xlsx, .pptx, .pdf, .txt, .md).</div>",
            "",
            ""
        )


def cleanse_action(file_input, author_name):
    if file_input is None:
        return None, "No file uploaded to cleanse."

    files = file_input if isinstance(file_input, list) else [file_input]
    author = author_name if author_name and author_name.strip() else DEFAULT_AUTHOR

    if len(files) == 1:
        f = files[0]
        file_path = f.name if hasattr(f, "name") else str(f)
        try:
            out_file = cleanse_metadata(file_path, author=author, keep_created_date=True)
            return [out_file], f"Cleansed {Path(file_path).name}: Author set to '{author}', original creation date preserved."
        except Exception as e:
            return None, f"Error cleansing file: {e}"

    # Batch cleanse multiple files
    cleansed_files = []
    messages = []
    for f in files:
        file_path = f.name if hasattr(f, "name") else str(f)
        p = Path(file_path)
        try:
            out_file = cleanse_metadata(file_path, author=author, keep_created_date=True)
            cleansed_files.append(out_file)
            messages.append(f"✓ Cleansed: {p.name}")
        except Exception as e:
            messages.append(f"✗ Failed {p.name}: {e}")

    summary = f"Processed {len(cleansed_files)}/{len(files)} files.\n" + "\n".join(messages)
    return cleansed_files, summary


def compare_docx_action(orig_file, rev_file):
    if orig_file is None or rev_file is None:
        return None, "Please upload both an original `.docx` and a revised `.docx` file."
    orig_path = orig_file.name if hasattr(orig_file, "name") else str(orig_file)
    rev_path = rev_file.name if hasattr(rev_file, "name") else str(rev_file)
    try:
        from humanizer import generate_side_by_side_docx
        out_path = str(Path(orig_path).with_name(f"{Path(orig_path).stem}_SideBySide.docx"))
        generate_side_by_side_docx(orig_path, rev_path, out_path)
        return out_path, f"Generated side-by-side diff: `{Path(out_path).name}`"
    except Exception as e:
        return None, f"Error generating side-by-side diff: {e}"


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

    import os
    is_hf = bool(os.environ.get("SPACE_ID"))
    if is_hf:
        github_badge_html = """
        <a href="https://github.com/7adel32/lecturers-stone" target="_blank" rel="noopener noreferrer" class="stone-gh-link" style="display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; text-decoration: none; color: var(--stone-text-muted); padding: 3px 9px; border-radius: 6px; border: 1px solid var(--stone-card-border); background: var(--stone-card-bg); transition: all 0.2s ease;">
            <svg height="14" width="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
            </svg>
            GitHub
        </a>
        """
    else:
        github_badge_html = ""

    header_html = f"""
    <div class="stone-glow-bar"></div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--stone-card-border);">
        <div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: var(--stone-text-main); letter-spacing: -0.02em;">The Lecturer's Stone</h1>
                {github_badge_html}
            </div>
            <div class="stone-subtitle">AI detector, with metadata checking, and cleansing</div>
            <div style="font-size: 13px; color: var(--stone-text-muted); margin-top: 4px;">check probability of being AI written with a number of independant models and check metadata for usual AI tells.</div>
        </div>
        <div id="stone-toggle-wrap" onclick="window.toggleStoneTheme && window.toggleStoneTheme()" style="flex-shrink: 0; margin-left: 20px; cursor: pointer; user-select: none;">
            {logo_html}
        </div>
    </div>
    """

    import os
    has_local = is_local_available()
    is_hf = bool(os.environ.get("SPACE_ID"))

    service_choices = []
    if has_local or is_hf:
        if is_hf:
            deberta_label = "DeBERTa Model (Consumes HF ZeroGPU Quota/Credits)"
        else:
            deberta_label = "Local Desklib DeBERTa (CUDA / GPU)"
        service_choices.append((deberta_label, "local_deberta"))

    service_choices.extend([
        ("TrustSafeAI RADAR (Adversarial Detector)", "radar"),
        ("Fakespot AI Text Classifier", "fakespot"),
        ("YugamJ LLM Text Detector", "yugamj"),
        ("PirateXX RoBERTa Detector", "piratexx"),
        ("Heuristic & Burstiness Engine (Offline)", "heuristic")
    ])

    service_defaults = ["radar", "fakespot", "yugamj", "piratexx", "heuristic"]

    with gr.Blocks(title="The Lecturer's Stone") as demo:
        gr.HTML(header_html)

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="Upload Document(s) (.docx, .xlsx, .pptx, .pdf, .txt, .md)",
                    file_types=[".docx", ".xlsx", ".xlsm", ".pptx", ".pdf", ".txt", ".md"],
                    file_count="multiple"
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
                    cleaned_file_output = gr.File(label="Download Cleansed Document(s)", file_count="multiple", interactive=False)
                    action_status = gr.Markdown("")

                with gr.Accordion("Side-by-Side Word Diff (DOCX)", open=False):
                    orig_docx_input = gr.File(label="Original .docx", file_types=[".docx"])
                    rev_docx_input = gr.File(label="Revised .docx", file_types=[".docx"])
                    compare_btn = gr.Button("Generate Side-by-Side Diff", variant="secondary")
                    compare_file_output = gr.File(label="Download Side-by-Side Diff (.docx)", interactive=False)
                    compare_status = gr.Markdown("")

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

        def handle_file_change(files):
            if files:
                return gr.update(interactive=False, placeholder="Document(s) loaded. Text input is disabled while documents are loaded. Click 'Clear Input' to type text.")
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

        compare_btn.click(
            fn=compare_docx_action,
            inputs=[orig_docx_input, rev_docx_input],
            outputs=[compare_file_output, compare_status]
        )

        # Bind _run_zerogpu_analysis to hidden probe button to satisfy ZeroGPU startup scan
        _probe_btn = gr.Button("probe", visible=False)
        _probe_btn.click(fn=_run_zerogpu_analysis)

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
