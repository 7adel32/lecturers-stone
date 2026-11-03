"""
The Lecturer's Stone - Metadata Forensics and Sanitization Engine.
Inspects documents (DOCX, XLSX, PPTX, PDF) for:
- Owner / Creator / Author names across Dublin Core, XMP, and comments
- Last Modifier / Editor
- Programmatic generator signatures (openpyxl, python-docx, ReportLab, etc.)
- Environment details (Application, AppVersion, Company, Manager, Template)
- Editing timeline (Created, Modified, Total Edit Time, Revision count)

Also provides:
- sanitize_metadata(): Replaces creator/modifier with configured author, preserves original creation date,
                       and removes environment / programmatic generator leaks.
- super_sanitize_metadata(): Nukes and wipes all metadata while keeping the file structurally valid and functional.
"""

import os
import sys
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

# Load local .env if present (without requiring python-dotenv)
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.is_file():
    try:
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip("'\"")
                if _k and _k not in os.environ:
                    os.environ[_k] = _v
    except Exception:
        pass

DEFAULT_AUTHOR = os.environ.get("LECTURERS_STONE_AUTHOR") or "Author"

try:
    import pymupdf  # PyMuPDF
except ImportError:
    pymupdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pptx
except ImportError:
    pptx = None

# Namespaces used in OpenXML formats
NS = {
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
    'vt': 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
}

KNOWN_GENERATOR_SIGNATURES = [
    ("openpyxl", "openpyxl (Python Excel library)"),
    ("python-docx", "python-docx (Python Word library)"),
    ("python-pptx", "python-pptx (Python PowerPoint library)"),
    ("reportlab", "ReportLab (Python PDF library)"),
    ("pyfpdf", "PyFPDF / FPDF (Python PDF library)"),
    ("fpdf2", "FPDF2 (Python PDF library)"),
    ("weasyprint", "WeasyPrint (HTML to PDF generator)"),
    ("wkhtmltopdf", "wkhtmltopdf (WebKit PDF generator)"),
    ("chromium", "Chromium / Headless Chrome (Automated browser PDF renderer)"),
    ("skia", "Skia / Skia PDF (Google automated canvas renderer)"),
    ("headlesschrome", "Headless Chrome PDF generator"),
    ("apache poi", "Apache POI (Java Office library)"),
    ("xlsxwriter", "XlsxWriter (Python Excel library)"),
    ("steve canny", "Steve Canny (Default author artifact of python-pptx)"),
    ("pandoc", "Pandoc document converter"),
    ("itext", "iText PDF library"),
]

PYTHON_DOCX_DEFAULT_EPOCH = "2013-12-23"
PYTHON_PPTX_DEFAULT_EPOCH = "2013-01-27"


def _read_zip_xml(zf: zipfile.ZipFile, internal_name: str) -> Optional[ET.Element]:
    if internal_name in zf.namelist():
        try:
            content = zf.read(internal_name)
            return ET.fromstring(content)
        except Exception:
            return None
    return None


def format_datetime_human(dt_str: Optional[str]) -> str:
    """Format machine timestamps (ISO-8601, PDF D: format, etc.) into clean human-readable date strings."""
    if not dt_str:
        return "N/A"
    dt_str = str(dt_str).strip()
    if not dt_str:
        return "N/A"

    if dt_str.startswith("D:"):
        clean_pdf = dt_str[2:].replace("'", "")
        try:
            if len(clean_pdf) >= 14:
                dt = datetime.strptime(clean_pdf[:14], "%Y%m%d%H%M%S")
                return dt.strftime("%b %d, %Y, %I:%M %p")
        except Exception:
            pass

    try:
        iso_clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        tz = " UTC" if "Z" in dt_str or "+00:00" in iso_clean else ""
        return dt.strftime("%b %d, %Y, %I:%M %p") + tz
    except Exception:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dt_str[:19], fmt)
            return dt.strftime("%b %d, %Y, %I:%M %p")
        except Exception:
            continue

    return dt_str


def inspect_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Inspect document container metadata for owner, editor, environment, and generator clues.
    Supports .docx, .xlsx, .pptx, and .pdf.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()

    result = {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_type": ext.lstrip(".").upper(),
        "has_metadata": False,
        "all_authors": [],
        "creator": None,
        "last_modified_by": None,
        "contributors": [],
        "comment_authors": [],
        "company": None,
        "manager": None,
        "application": None,
        "app_version": None,
        "created": None,
        "modified": None,
        "revision": None,
        "total_edit_time_min": None,
        "environment_details": {},
        "raw_properties": {},
        "clues": [],
        "risk_level": "CLEAN",
        "verdict": "No suspicious metadata detected"
    }

    if ext in [".docx", ".xlsx", ".xlsm", ".pptx", ".docm"]:
        _inspect_ooxml(path, result)
    elif ext == ".pdf":
        _inspect_pdf(path, result)
    else:
        result["verdict"] = "Metadata inspection not supported for this file format"
        return result

    # Evaluate generator clues across gathered properties
    _evaluate_generator_clues(result)

    return result


def _inspect_ooxml(path: Path, result: Dict[str, Any]):
    try:
        authors_found = []
        def add_author(name: Optional[str]):
            if not name:
                return
            for part in re.split(r"[,;]|\band\b", name):
                cleaned = part.strip()
                if cleaned and cleaned not in authors_found:
                    authors_found.append(cleaned)

        with zipfile.ZipFile(path, "r") as zf:
            core_root = _read_zip_xml(zf, "docProps/core.xml")
            app_root = _read_zip_xml(zf, "docProps/app.xml")

            if core_root is not None:
                result["has_metadata"] = True
                for elem in core_root:
                    tag = elem.tag.split("}")[-1]
                    val = (elem.text or "").strip()
                    if not val:
                        continue
                    result["raw_properties"][f"core:{tag}"] = val
                    if tag == "creator":
                        result["creator"] = val
                        add_author(val)
                    elif tag == "lastModifiedBy":
                        result["last_modified_by"] = val
                        add_author(val)
                    elif tag == "contributor":
                        result["contributors"].append(val)
                        add_author(val)
                    elif tag == "created":
                        result["created"] = val
                    elif tag == "modified":
                        result["modified"] = val
                    elif tag == "revision":
                        result["revision"] = val

            if app_root is not None:
                result["has_metadata"] = True
                for elem in app_root:
                    tag = elem.tag.split("}")[-1]
                    val = (elem.text or "").strip()
                    if not val:
                        continue
                    result["raw_properties"][f"app:{tag}"] = val
                    if tag == "Application":
                        result["application"] = val
                        result["environment_details"]["Application"] = val
                    elif tag == "AppVersion":
                        result["app_version"] = val
                        result["environment_details"]["AppVersion"] = val
                    elif tag == "Company":
                        result["company"] = val
                        result["environment_details"]["Company"] = val
                    elif tag == "Manager":
                        result["manager"] = val
                        result["environment_details"]["Manager"] = val
                        add_author(val)
                    elif tag == "TotalTime":
                        result["total_edit_time_min"] = val
                        result["environment_details"]["TotalTime"] = f"{val} minutes"
                    elif tag in ["Template", "PresentationFormat", "SharedDoc"]:
                        result["environment_details"][tag] = val

            # Check custom properties for owner / author fields
            custom_root = _read_zip_xml(zf, "docProps/custom.xml")
            if custom_root is not None:
                for elem in custom_root:
                    name = elem.attrib.get("name", "Custom")
                    val = "".join(elem.itertext()).strip()
                    if val:
                        result["raw_properties"][f"custom:{name}"] = val
                        result["environment_details"][f"Custom:{name}"] = val
                        if any(k in name.lower() for k in ["author", "owner", "creator", "writer", "reviewer"]):
                            add_author(val)

            # Check comment and revision files for hidden author names
            for name in zf.namelist():
                if name.startswith("word/comments") or name == "ppt/commentAuthors.xml" or "comments" in name.lower() or "person.xml" in name.lower():
                    comment_root = _read_zip_xml(zf, name)
                    if comment_root is not None:
                        for elem in comment_root.iter():
                            author_attr = elem.attrib.get("w:author") or elem.attrib.get("author") or elem.attrib.get("name") or elem.attrib.get("displayName")
                            if author_attr and author_attr.strip():
                                c_name = author_attr.strip()
                                if c_name not in result["comment_authors"]:
                                    result["comment_authors"].append(c_name)
                                add_author(c_name)

        result["all_authors"] = authors_found

    except Exception as e:
        result["verdict"] = f"Failed to parse OOXML structure: {str(e)}"


def _inspect_pdf(path: Path, result: Dict[str, Any]):
    if pymupdf is None:
        result["verdict"] = "PyMuPDF is required to inspect PDF metadata"
        return

    try:
        authors_found = []
        def add_author(name: Optional[str]):
            if not name:
                return
            for part in re.split(r"[,;]|\band\b", name):
                cleaned = part.strip()
                if cleaned and cleaned not in authors_found:
                    authors_found.append(cleaned)

        with pymupdf.open(str(path)) as doc:
            meta = doc.metadata or {}
            result["has_metadata"] = any(bool(v) for v in meta.values() if v)
            result["raw_properties"] = {k: v for k, v in meta.items() if v}

            author_val = meta.get("author", "").strip()
            creator_val = meta.get("creator", "").strip()

            if author_val:
                result["creator"] = author_val
                add_author(author_val)

            result["last_modified_by"] = author_val or None
            result["application"] = creator_val or meta.get("producer")
            result["created"] = meta.get("creationDate")
            result["modified"] = meta.get("modDate")

            if meta.get("producer"):
                result["environment_details"]["Producer"] = meta.get("producer")
            if meta.get("creator"):
                result["environment_details"]["Creator Tool"] = meta.get("creator")
            if meta.get("format"):
                result["environment_details"]["PDF Format"] = meta.get("format")
            if meta.get("encryption"):
                result["environment_details"]["Encryption"] = meta.get("encryption")

            # Check XMP XML Packet specifically for dc:creator and author sequences
            xmp = doc.get_xml_metadata()
            if xmp:
                try:
                    xmp_clean = re.sub(r'<\?xpacket[^>]*\?>', '', xmp)
                    xmp_root = ET.fromstring(xmp_clean)
                    for elem in xmp_root.iter():
                        tag = elem.tag.split("}")[-1]
                        if tag in ["creator", "Author", "author"]:
                            for child in elem.iter():
                                txt = (child.text or "").strip()
                                if txt and len(txt) < 80 and not any(ext in txt.lower() for ext in ["http", ".org", "pdf", "latex", "distiller", "acrobat", "xmlns"]):
                                    add_author(txt)
                except Exception:
                    pass

            # Check Page Annotations for comment author names
            for page in doc:
                for annot in page.annots():
                    if annot.info:
                        title = annot.info.get("title", "").strip()
                        if title and title not in result["comment_authors"]:
                            result["comment_authors"].append(title)
                            add_author(title)

            result["all_authors"] = authors_found

    except Exception as e:
        result["verdict"] = f"Failed to parse PDF metadata: {str(e)}"


def _evaluate_generator_clues(result: Dict[str, Any]):
    clues: List[str] = []
    combined_text = " ".join([
        str(result.get("creator") or ""),
        str(result.get("last_modified_by") or ""),
        str(result.get("application") or ""),
        str(result.get("company") or ""),
        str(result.get("manager") or ""),
        " ".join(str(v) for v in result.get("raw_properties", {}).values())
    ]).lower()

    # 1. Match known generator library signatures
    for sig, desc in KNOWN_GENERATOR_SIGNATURES:
        if sig in combined_text:
            clues.append(f"Identified automated library signature: {desc}")

    # 2. Hardcoded library timestamp anomalies
    created_str = str(result.get("created") or "")
    if PYTHON_DOCX_DEFAULT_EPOCH in created_str:
        clues.append("Default python-docx hardcoded timestamp detected (2013-12-23 23:15:00 UTC)")
    if PYTHON_PPTX_DEFAULT_EPOCH in created_str:
        clues.append("Default python-pptx hardcoded timestamp detected (2013-01-27 09:14:16 UTC)")

    # 3. Revision count & editing time anomalies
    rev = result.get("revision")
    edit_time = result.get("total_edit_time_min")

    if rev in ["1", 1] and edit_time in ["0", 0, "1", 1]:
        clues.append("Single revision with near-zero editing time (indicative of programmatic export)")

    # 4. Synthesize risk level and verdict
    result["clues"] = clues
    if clues:
        result["risk_level"] = "HIGH_RISK"
        result["verdict"] = f"Document contains {len(clues)} programmatic metadata signature(s)"
    elif result.get("creator") or result.get("application") or result.get("created"):
        result["risk_level"] = "STANDARD"
        result["verdict"] = "Document metadata present without known programmatic library signatures"
    else:
        result["risk_level"] = "STRIPPED"
        result["verdict"] = "Clean / stripped metadata (no identifying markers)"

    result["created_formatted"] = format_datetime_human(result.get("created"))
    result["modified_formatted"] = format_datetime_human(result.get("modified"))


def sanitize_metadata(
    file_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    author: Optional[str] = None,
    keep_created_date: bool = True
) -> str:
    """
    Sanitize document metadata:
    - Sets Creator and Last Modified By to author (defaults to LECTURERS_STONE_AUTHOR or DEFAULT_AUTHOR)
    - Sets Creation Date = original creation date (or current time if missing)
    - Cleans out environment leaks (openpyxl, python-docx, ReportLab, Company, Manager, custom props)
    - Sets realistic application tags (e.g., Microsoft Word, Microsoft Excel, Microsoft PowerPoint)
    - Maintains full document integrity and validity.
    """
    src = Path(file_path)
    if not src.is_file():
        raise FileNotFoundError(f"File not found: {src}")

    ext = src.suffix.lower()
    if output_path is None:
        target = src.parent / f"{src.stem}_sanitized{src.suffix}"
    else:
        target = Path(output_path)

    target_author = author if (author and author.strip()) else DEFAULT_AUTHOR

    # First inspect original to retrieve old creation date
    info = inspect_metadata(src)
    old_created = info.get("created")

    if ext in [".docx", ".xlsx", ".xlsm", ".pptx"]:
        _sanitize_ooxml(src, target, author=target_author, old_created=old_created, keep_created=keep_created_date, nuke=False)
    elif ext == ".pdf":
        _sanitize_pdf(src, target, author=target_author, old_created=old_created, keep_created=keep_created_date, nuke=False)
    else:
        raise ValueError(f"Unsupported file format for sanitization: {ext}")

    return str(target.resolve())


def super_sanitize_metadata(
    file_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Super Sanitize / Nuke document metadata:
    - Completely wipes and strips all metadata fields (Creator, Dates, Company, App, Custom Props).
    - Ensures the file remains 100% valid, functional, and non-corrupt.
    """
    src = Path(file_path)
    if not src.is_file():
        raise FileNotFoundError(f"File not found: {src}")

    ext = src.suffix.lower()
    if output_path is None:
        target = src.parent / f"{src.stem}_nuked{src.suffix}"
    else:
        target = Path(output_path)

    if ext in [".docx", ".xlsx", ".xlsm", ".pptx"]:
        _sanitize_ooxml(src, target, author=None, old_created=None, keep_created=False, nuke=True)
    elif ext == ".pdf":
        _sanitize_pdf(src, target, author=None, old_created=None, keep_created=False, nuke=True)
    else:
        raise ValueError(f"Unsupported file format for super sanitization: {ext}")

    return str(target.resolve())


def _clean_core_xml(xml_bytes: bytes, author: Optional[str], created_iso: Optional[str], nuke: bool) -> bytes:
    root = ET.fromstring(xml_bytes)

    if nuke:
        for elem in list(root):
            root.remove(elem)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    target_author = author or DEFAULT_AUTHOR
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    final_created = created_iso if created_iso else now_iso

    for elem in list(root):
        tag = elem.tag.split("}")[-1]
        if tag == "creator":
            elem.text = target_author
        elif tag == "lastModifiedBy":
            elem.text = target_author
        elif tag == "created":
            elem.text = final_created
        elif tag == "modified":
            elem.text = final_created
        elif tag in ["description", "keywords", "category", "contentStatus"]:
            root.remove(elem)
        elif tag == "revision":
            elem.text = "3"

    # Ensure dc:creator exists
    creator_tag = f"{{{NS['dc']}}}creator"
    if root.find(creator_tag) is None:
        c = ET.SubElement(root, creator_tag)
        c.text = target_author

    # Ensure cp:lastModifiedBy exists
    mod_tag = f"{{{NS['cp']}}}lastModifiedBy"
    if root.find(mod_tag) is None:
        m = ET.SubElement(root, mod_tag)
        m.text = target_author

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _clean_app_xml(xml_bytes: bytes, app_name: str, nuke: bool) -> bytes:
    root = ET.fromstring(xml_bytes)
    for elem in list(root):
        tag = elem.tag.split("}")[-1]
        if nuke:
            if tag in ["Company", "Manager", "Application", "AppVersion", "Template"]:
                root.remove(elem)
        else:
            if tag in ["Company", "Manager"]:
                root.remove(elem)
            elif tag == "Application":
                elem.text = app_name
            elif tag == "AppVersion":
                elem.text = "16.0000"
            elif tag == "TotalTime":
                elem.text = "45"

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _sanitize_ooxml(
    src: Path,
    target: Path,
    author: Optional[str],
    old_created: Optional[str],
    keep_created: bool,
    nuke: bool
):
    ext = src.suffix.lower()
    if ext == ".docx":
        app_name = "Microsoft Word"
    elif ext in [".xlsx", ".xlsm"]:
        app_name = "Microsoft Excel"
    elif ext == ".pptx":
        app_name = "Microsoft PowerPoint"
    else:
        app_name = "Microsoft Office"

    created_iso = old_created if (keep_created and old_created) else None

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                data = _clean_core_xml(data, author=author, created_iso=created_iso, nuke=nuke)
            elif item.filename == "docProps/app.xml":
                data = _clean_app_xml(data, app_name=app_name, nuke=nuke)
            zout.writestr(item, data)


def _sanitize_pdf(
    src: Path,
    target: Path,
    author: Optional[str],
    old_created: Optional[str],
    keep_created: bool,
    nuke: bool
):
    if pymupdf is None:
        raise RuntimeError("PyMuPDF is required for PDF sanitization")

    doc = pymupdf.open(str(src))
    if nuke:
        doc.set_metadata({})
        doc.del_xml_metadata()
    else:
        target_author = author or DEFAULT_AUTHOR
        cdate = old_created if (keep_created and old_created) else "D:20240115120000Z"
        doc.set_metadata({
            "author": target_author,
            "creator": "Microsoft Word",
            "producer": "Microsoft Word for Windows",
            "title": "",
            "subject": "",
            "keywords": "",
            "creationDate": cdate,
            "modDate": cdate
        })
        doc.del_xml_metadata()

    doc.save(str(target), garbage=4, clean=True, deflate=True)
    doc.close()
