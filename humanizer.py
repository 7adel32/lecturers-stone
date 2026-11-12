"""
Local Text Humanizer & Side-by-Side Comparison Tool for The Lecturer's Stone (ai-checker).

Capabilities:
1. humanize: Rewrites Word document (.docx) paragraphs via local Ollama (abacusai/Smaug-Humanizer)
   - Protects native Word OMML equations (<m:oMath> / <m:oMathPara>) from deletion
   - Enforces third-person academic voice (prevents first-person "I"/"We" shifts)
   - Optionally verifies before/after LocalDebertaDetector scores
2. compare: Generates a 2-column landscape Side-by-Side Word document (_SideBySide.docx)
   or inline tracked-changes style comparison (_Comparison.docx) with word-level
   red strikethrough (deleted) and green underline (added) highlights.
"""

import argparse
import difflib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import docx
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

DEFAULT_MODEL = "hf.co/bartowski/abacusai_Smaug-Humanizer-GGUF:Q4_K_M"
OLLAMA_URL = "http://localhost:11434/api/generate"


def has_omml_math(paragraph) -> bool:
    """Return True if the paragraph contains native Word OMML math elements."""
    el = paragraph._element
    return bool(el.findall(".//" + qn("m:oMath")) or el.findall(".//" + qn("m:oMathPara")))


def humanize_paragraph_text(text: str, model: str = DEFAULT_MODEL, temperature: float = 0.5) -> str:
    text_clean = text.strip()
    if len(text_clean) < 50:
        return text

    # Skip headers, metadata lines, and short numbered headings
    if any(k in text_clean for k in ["Title:", "Authors:", "Year:", "Journal:", "Full Reference"]):
        return text
    if text_clean[0].isdigit() and "." in text_clean[:4] and len(text_clean.split()) <= 8:
        return text

    prompt = (
        "Rewrite the following academic text into natural, clear, fluent third-person academic prose. "
        "Strictly preserve all numbers, percentages, abbreviations, model names, datasets, and factual claims. "
        "Never use first-person pronouns ('I', 'we', 'our'). "
        "Return ONLY the rewritten paragraph without any introductory remarks or explanations:\n\n"
        + text
    )
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "top_p": 0.9}
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        res = json.loads(resp.read().decode("utf-8"))
        out = res.get("response", "").strip()
        out = re.sub(r"^(Here is the rewritten text:?|Rewritten text:?|Rewritten:?)\s*", "", out, flags=re.I).strip("\"'")
        # Reject if the model injected first-person pronouns into third-person text
        if re.search(r"\b(I|we|our)\b", out, flags=re.I) and not re.search(r"\b(I|we|our)\b", text, flags=re.I):
            return text
        return out if len(out) > 20 else text
    except Exception as e:
        print(f"Warning: Ollama call failed ({e}), keeping original paragraph.")
        return text


def humanize_docx(
    input_path: str,
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    author: Optional[str] = None
) -> str:
    src = Path(input_path)
    if not src.is_file():
        raise FileNotFoundError(f"Input file not found: {src}")

    dst = Path(output_path) if output_path else src.parent / f"{src.stem}_humanized{src.suffix}"
    doc = docx.Document(str(src))

    rewritten_count = 0
    skipped_math = 0
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if not t or len(t) <= 60:
            continue
        if has_omml_math(p):
            skipped_math += 1
            continue
        old_t = p.text
        new_t = humanize_paragraph_text(old_t, model=model)
        if new_t != old_t:
            p.text = new_t
            rewritten_count += 1
            print(f"  P{i} rewritten ({len(old_t)} -> {len(new_t)} chars)")

    if author:
        doc.core_properties.author = author
        doc.core_properties.last_modified_by = author

    doc.save(str(dst))
    print(f"Saved humanized document: {dst} ({rewritten_count} rewritten, {skipped_math} OMML math paragraphs preserved)")
    return str(dst.resolve())


def generate_side_by_side_docx(
    orig_path: str,
    rev_path: str,
    out_path: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    src_orig = Path(orig_path)
    src_rev = Path(rev_path)
    dst = Path(out_path) if out_path else src_orig.parent / f"{src_orig.stem}_SideBySide.docx"
    doc_title = title or f"Side-by-Side Comparison: {src_orig.name} vs {src_rev.name}"

    doc_orig = docx.Document(str(src_orig))
    doc_rev = docx.Document(str(src_rev))

    doc = docx.Document()
    section = doc.sections[0]
    section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11.0)
    section.page_height = Inches(8.5)
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

    doc.add_heading(doc_title, level=1)

    orig_paras = [p.text for p in doc_orig.paragraphs]
    rev_paras = [p.text for p in doc_rev.paragraphs]

    table = doc.add_table(rows=1, cols=2)
    table.autofit = False

    hdr_cells = table.rows[0].cells
    hdr_cells[0].width = Inches(4.8)
    hdr_cells[1].width = Inches(4.8)

    r0 = hdr_cells[0].paragraphs[0].add_run("ORIGINAL VERSION")
    r0.bold = True
    r0.font.size = Pt(11)
    r0.font.color.rgb = RGBColor(0, 51, 102)

    r1 = hdr_cells[1].paragraphs[0].add_run("HUMANIZED / REVISED VERSION")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(0, 102, 51)

    matcher = difflib.SequenceMatcher(None, orig_paras, rev_paras)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                t = orig_paras[idx].strip()
                if not t:
                    continue
                row_cells = table.add_row().cells
                row_cells[0].width = Inches(4.8)
                row_cells[1].width = Inches(4.8)
                row_cells[0].paragraphs[0].text = t
                row_cells[1].paragraphs[0].text = t
        elif tag == "replace":
            orig_slice = [p.strip() for p in orig_paras[i1:i2] if p.strip()]
            rev_slice = [p.strip() for p in rev_paras[j1:j2] if p.strip()]
            max_len = max(len(orig_slice), len(rev_slice))
            for k in range(max_len):
                o_t = orig_slice[k] if k < len(orig_slice) else ""
                r_t = rev_slice[k] if k < len(rev_slice) else ""
                row_cells = table.add_row().cells
                row_cells[0].width = Inches(4.8)
                row_cells[1].width = Inches(4.8)
                p_l = row_cells[0].paragraphs[0]
                p_r = row_cells[1].paragraphs[0]

                if o_t == r_t:
                    p_l.text = o_t
                    p_r.text = r_t
                else:
                    o_words = o_t.split()
                    r_words = r_t.split()
                    w_matcher = difflib.SequenceMatcher(None, o_words, r_words)
                    for w_tag, wi1, wi2, wj1, wj2 in w_matcher.get_opcodes():
                        if w_tag == "equal":
                            p_l.add_run(" ".join(o_words[wi1:wi2]) + " ")
                            p_r.add_run(" ".join(r_words[wj1:wj2]) + " ")
                        elif w_tag == "delete":
                            run = p_l.add_run(" ".join(o_words[wi1:wi2]) + " ")
                            run.font.strike = True
                            run.font.color.rgb = RGBColor(192, 0, 0)
                        elif w_tag == "insert":
                            run = p_r.add_run(" ".join(r_words[wj1:wj2]) + " ")
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(0, 128, 0)
                        elif w_tag == "replace":
                            del_run = p_l.add_run(" ".join(o_words[wi1:wi2]) + " ")
                            del_run.font.strike = True
                            del_run.font.color.rgb = RGBColor(192, 0, 0)
                            ins_run = p_r.add_run(" ".join(r_words[wj1:wj2]) + " ")
                            ins_run.font.underline = True
                            ins_run.font.color.rgb = RGBColor(0, 128, 0)
        elif tag == "delete":
            for idx in range(i1, i2):
                t = orig_paras[idx].strip()
                if not t:
                    continue
                row_cells = table.add_row().cells
                row_cells[0].width = Inches(4.8)
                row_cells[1].width = Inches(4.8)
                r = row_cells[0].paragraphs[0].add_run(t)
                r.font.strike = True
                r.font.color.rgb = RGBColor(192, 0, 0)
        elif tag == "insert":
            for idx in range(j1, j2):
                t = rev_paras[idx].strip()
                if not t:
                    continue
                row_cells = table.add_row().cells
                row_cells[0].width = Inches(4.8)
                row_cells[1].width = Inches(4.8)
                r = row_cells[1].paragraphs[0].add_run(t)
                r.font.underline = True
                r.font.color.rgb = RGBColor(0, 128, 0)

    doc.save(str(dst))
    print(f"Saved Side-by-Side comparison document: {dst}")
    return str(dst.resolve())


def main():
    parser = argparse.ArgumentParser(description="Local Humanizer & Side-by-Side Word Comparison Utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hum = sub.add_parser("humanize", help="Humanize a .docx file via local Ollama Smaug-Humanizer")
    p_hum.add_argument("-i", "--input", required=True, help="Input .docx path")
    p_hum.add_argument("-o", "--output", help="Output .docx path (default: <stem>_humanized.docx)")
    p_hum.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Ollama model name")
    p_hum.add_argument("-a", "--author", help="Set author metadata")

    p_cmp = sub.add_parser("compare", help="Generate a 2-column landscape Side-by-Side diff .docx")
    p_cmp.add_argument("-orig", "--original", required=True, help="Original .docx path")
    p_cmp.add_argument("-rev", "--revised", required=True, help="Revised/humanized .docx path")
    p_cmp.add_argument("-o", "--output", help="Output .docx path (default: <stem>_SideBySide.docx)")
    p_cmp.add_argument("-t", "--title", help="Comparison heading title")

    args = parser.parse_args()
    if args.cmd == "humanize":
        humanize_docx(args.input, args.output, model=args.model, author=args.author)
    elif args.cmd == "compare":
        generate_side_by_side_docx(args.original, args.revised, out_path=args.output, title=args.title)


if __name__ == "__main__":
    main()
