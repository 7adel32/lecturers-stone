"""
Hugging Face Space Synchronization Script.
Automatically runs via GitHub Actions on push to master.
Uploads repository contents to Hugging Face Spaces with proper YAML frontmatter.
"""

import os
from pathlib import Path
from huggingface_hub import HfApi

def sync():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN secret not found. Skipping Hugging Face sync.")
        return

    root_dir = Path(__file__).resolve().parent.parent
    readme_path = root_dir / "README.md"

    # Prepend Hugging Face Space metadata to README.md before uploading
    original_readme = readme_path.read_text(encoding="utf-8")
    hf_frontmatter = (
        "---\n"
        "title: The Lecturers Stone\n"
        "colorFrom: red\n"
        "colorTo: yellow\n"
        "sdk: gradio\n"
        "app_file: app.py\n"
        "pinned: false\n"
        "---\n\n"
    )

    try:
        readme_path.write_text(hf_frontmatter + original_readme, encoding="utf-8")

        api = HfApi(token=token)
        commit_info = api.upload_folder(
            folder_path=str(root_dir),
            repo_id="alfndly/lecturers-stone",
            repo_type="space",
            ignore_patterns=[
                ".git",
                ".git/**",
                ".github",
                ".github/**",
                "__pycache__",
                "*.pyc",
                ".env"
            ]
        )
        print("Successfully synced to Hugging Face Space!")
        print("Commit URL:", commit_info)
    finally:
        # Restore clean README.md locally
        readme_path.write_text(original_readme, encoding="utf-8")

if __name__ == "__main__":
    sync()
