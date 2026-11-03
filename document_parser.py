"""
Document Parser supporting TXT, Markdown, PDF, DOCX, and raw strings.
"""

from pathlib import Path
from typing import Union
import pymupdf  # PyMuPDF
import docx
import pptx
import openpyxl


def extract_text_from_file(file_path: Union[str, Path]) -> str:
    """Extract plain text from various file formats (.txt, .md, .pdf, .docx)."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()

    if ext in [".txt", ".md", ".markdown", ".rtf", ".rst", ".py", ".json", ".csv"]:
        return path.read_text(encoding="utf-8", errors="replace")

    elif ext == ".pdf":
        text_parts = []
        with pymupdf.open(str(path)) as doc:
            for page in doc:
                t = page.get_text()
                if t:
                    text_parts.append(t)
        return "\n\n".join(text_parts).strip()

    elif ext in [".docx", ".doc"]:
        if ext == ".doc":
            # Best effort try python-docx or raw read
            try:
                doc = docx.Document(str(path))
                return "\n".join([p.text for p in doc.paragraphs if p.text]).strip()
            except Exception:
                return path.read_text(encoding="utf-8", errors="replace")
        doc = docx.Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        # Also parse tables if present
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    paragraphs.append(row_text)
        return "\n".join(paragraphs).strip()

    elif ext in [".pptx", ".ppt"]:
        prs = pptx.Presentation(str(path))
        text_runs = []
        for slide_idx, slide in enumerate(prs.slides, 1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        p_text = "".join(run.text for run in paragraph.runs).strip()
                        if p_text:
                            slide_texts.append(p_text)
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            slide_texts.append(row_text)
            if slide_texts:
                text_runs.append(f"--- Slide {slide_idx} ---\n" + "\n".join(slide_texts))
        return "\n\n".join(text_runs).strip()

    elif ext in [".xlsx", ".xlsm", ".xltx"]:
        wb = openpyxl.load_workbook(str(path), data_only=True)
        sheet_texts = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_text = []
            for row in ws.iter_rows(values_only=True):
                non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if non_empty:
                    rows_text.append(" | ".join(non_empty))
            if rows_text:
                sheet_texts.append(f"--- Sheet: {sheet_name} ---\n" + "\n".join(rows_text))
        return "\n\n".join(sheet_texts).strip()

    else:
        # Default fallback to plain text read
        return path.read_text(encoding="utf-8", errors="replace")
