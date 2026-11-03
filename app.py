"""
The Lecturer's Stone - Main Application Entry Point.
Run directly to launch the interactive Gradio dashboard:
    python app.py

Or pass --cli to use the command line interface:
    python app.py --cli -f "path/to/document.docx"
"""

import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Remove --cli flag and pass remaining arguments to cli.py
        sys.argv.pop(1)
        import cli
        cli.main()
    else:
        import os
        import web_gui
        demo, theme, css, head = web_gui.create_ui()
        favicon = web_gui.current_dir / "assets" / "icon.ico"
        fav_path = str(favicon) if favicon.is_file() else None

        is_hf = bool(os.environ.get("SPACE_ID"))
        if is_hf:
            demo.launch(theme=theme, css=css, head=head, favicon_path=fav_path)
        else:
            demo.launch(server_name="127.0.0.1", server_port=7865, theme=theme, css=css, head=head, favicon_path=fav_path)
