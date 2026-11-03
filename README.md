<p align="center">
  <img src="assets/logo.png" width="220" alt="The Lecturer's Stone Logo" />
</p>

# The Lecturer's Stone

An academic-grade multi-engine AI content detector, container metadata forensics framework, and document sanitizer.

Combines transformer sequence classifiers, statistical NLP burstiness algorithms, and container XML forensics to inspect submissions, detect automated generator fingerprints (`openpyxl`, `python-docx`, `python-pptx`, `iText`, `ReportLab`), and sanitize document metadata while preserving original creation timelines.

---

## Architecture Overview

Traditional AI detectors evaluate text semantics (perplexity, burstiness, token distribution) while remaining blind to document containers. In practical academic evaluation, container metadata is often the primary source of exposure:
- Script-generated Word documents leave `Author: python-docx` and the default `2013-12-23` epoch.
- Automated spreadsheets embed `openpyxl` in `docProps/app.xml`.
- Generated presentations retain `generated using python-pptx` and `Steve Canny`.
- Compiled PDFs expose `iText`, `ReportLab`, `pyFPDF`, or headless browser PDF converters.

The Lecturer's Stone unifies **Container Forensics** and **Multi-Service AI Consensus** into a single evaluation pipeline.

---

## Detection Capabilities

### 1. Container Metadata Forensics
- **Comprehensive Author Discovery**: Scans Dublin Core (`docProps/core.xml`), Extended Properties (`docProps/app.xml`), Custom Properties (`docProps/custom.xml`), comment threads (`word/comments.xml`, `ppt/commentAuthors.xml`, `xl/persons/person.xml`), and PDF XMP streams (`dc:creator`, `pdf:Author`).
- **Programmatic Generator Clues**: Flags hardcoded library fingerprints including:
  - `openpyxl` (Python Excel Library)
  - `python-docx` (Python Word Library & default 2013 epoch)
  - `python-pptx` (Python PowerPoint Library & default 2013 epoch)
  - `ReportLab`, `pyFPDF`, `FPDF2`, `WeasyPrint`, `wkhtmltopdf` (PDF generation engines)
  - `Chromium / Skia / Headless Chrome` (Automated browser PDF renderers)
  - `Apache POI` (Java Office Library)
  - `iText` (Java/C# PDF Library)
  - `XlsxWriter` (Python Excel Library)
- **Timeline & Editing Anomalies**: Identifies single revision counters (`Rev = 1`) with zero editing duration (`TotalTime = 0`), which indicate automated script exports.

### 2. Multi-Service AI Content Detection
- **Local Desklib DeBERTa (`desklib/ai-text-detector-v1.01`)**: Number 1 ranked model on the RAID AI Detection Benchmark. Runs locally on CUDA GPU (or CPU) with sliding window chunking across long documents.
- **TrustSafeAI RADAR**: Adversarial AI text detector robust against paraphrasing and prompt manipulation.
- **Fakespot AI Classifier**: Commercial-grade transformer sequence classifier.
- **SzegedAI DeBERTa**: DeBERTa-based AI detector providing high-precision probability breakdowns.
- **PirateXX RoBERTa**: Multi-tier transformer detector.
- **YugamJ LLM Detector**: Fine-tuned classification model calibrated for ChatGPT and modern LLM text.
- **Heuristic & Burstiness Engine**: Offline statistical NLP engine measuring sentence length variance (burstiness coefficient of variation), type-token lexical diversity, and AI transition marker density.

---

## Sanitization Engine

The tool provides two non-destructive sanitization modes that maintain full document structural validity:

### Mode 1: Smart Sanitize
- Replaces Creator and Last Modifier with the configured author name (read from `LECTURERS_STONE_AUTHOR` or `--author`).
- **Preserves Original Creation Date**: Keeps the authentic `dcterms:created` timestamp so the file does not appear artificially created at the moment of cleaning.
- Scrubs automated library markers (`openpyxl`, `python-docx`, `python-pptx`, `iText`, `ReportLab`).
- Clears environment leaks (Company, Manager, custom properties, template paths).
- Sets realistic revision counters and standard application tags (`Microsoft Word`, `Microsoft Excel`, `Microsoft PowerPoint`).

### Mode 2: Super-Sanitize (Nuke)
- Completely purges all metadata fields, Dublin Core tags, and XMP packets.
- Retains proper OpenXML and PDF container structures to guarantee the file opens cleanly without XML corruption or repair dialogs.

---

## Quickstart

### Installation

Clone the repository and install the dependencies:

```powershell
git clone https://github.com/7adel32/lecturers-stone.git
cd lecturers-stone
pip install -r requirements.txt
```

Copy the example environment configuration:

```powershell
cp .env.example .env
```

Edit `.env` to configure your default author name:

```env
LECTURERS_STONE_AUTHOR="Your Name"
```

---

## Command Line Usage

### 1. Default Evaluation (AI + Metadata Forensics)

Analyzes both container metadata clues and runs all AI text detection engines:

```powershell
# Analyze Word Document
python cli.py -f "path\to\document.docx"

# Analyze PDF Document
python cli.py -f "path\to\document.pdf"

# Analyze Spreadsheet or Presentation
python cli.py -f "path\to\sheet.xlsx"
python cli.py -f "path\to\slides.pptx"
```

### 2. Fast Metadata Inspection Only (Skip AI Inference)

Inspects container metadata, author lists, and library fingerprints in under 0.2 seconds:

```powershell
python cli.py -f "path\to\document.docx" --skip-ai
```

### 3. Sanitize Document (Preserve Creation Date)

```powershell
python cli.py -f "draft.docx" --sanitize "submission.docx" --skip-ai
```

### 4. Super-Sanitize / Nuke All Metadata

```powershell
python cli.py -f "draft.pdf" --nuke "clean.pdf" --skip-ai
```

### 5. Plain Text Check

```powershell
python cli.py -t "Paste essay or article string here..."
```

### 6. JSON Export

```powershell
python cli.py -f "document.docx" --json --export "report.json"
```

---

## Interactive Web GUI

Launch the Gradio dashboard locally at `http://127.0.0.1:7865`:

```powershell
python app.py
```

The Web interface allows:
- Drag-and-drop document uploads (`.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt`, `.md`).
- Real-time consensus score bar and individual engine breakdowns.
- Metadata forensics card displaying all detected authors, creation dates, and library fingerprints.
- One-click buttons to download Sanitized or Nuked files directly from the browser.

---

## Project Structure

```text
lecturers-stone/
├── app.py                # Main entry point (launches Web GUI or CLI)
├── cli.py                # Standalone command-line interface
├── web_gui.py            # Gradio Web dashboard
├── checker_hub.py        # Multi-service AI detection consensus framework
├── metadata_forensics.py # Metadata inspector, clue finder, and sanitizer
├── local_detector.py     # Local DeBERTa GPU model runner (CUDA / CPU)
├── heuristic_engine.py   # Statistical burstiness & lexical diversity engine
├── document_parser.py    # Multi-format document parser (DOCX, XLSX, PPTX, PDF, TXT)
├── requirements.txt      # Project dependencies
├── LICENSE               # MIT License
├── .env.example          # Sample environment configuration
└── assets/
    ├── logo.svg          # Vector icon
    ├── logo.png          # High-resolution raster banner
    └── icon.ico          # Multi-resolution application icon
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
