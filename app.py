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
        import web_gui
        demo = web_gui.create_ui()
        demo.launch(server_name="127.0.0.1", server_port=7865)
