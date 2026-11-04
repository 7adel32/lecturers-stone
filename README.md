<p align="center">
  <img src="assets/logo_stone.png" width="180" alt="The Lecturer's Stone Logo" />
</p>

# The Lecturer's Stone [![Open in Spaces](https://huggingface.co/datasets/huggingface/badges/resolve/main/open-in-hf-spaces-sm.svg)](https://alfndly-lecturers-stone.hf.space/)

AI detector, with metadata checking, and cleansing.

Checks probability of being AI written with a number of independent models and checks document metadata (.docx, .xlsx, .pptx, .pdf) for usual AI tells.

---

## Why Check Metadata?

Most AI detectors only check the text itself (patterns, repetition, burstiness) while completely ignoring the file it came in. But in practice, file metadata is often the biggest giveaway:
- Script-generated Word documents leave `Author: python-docx` and a default `2013-12-23` date.
- Auto-generated spreadsheets embed `openpyxl` in the file properties.
- Generated presentations retain `generated using python-pptx` and `Steve Canny`.
- Compiled PDFs expose `iText`, `ReportLab`, `pyFPDF`, or headless browser PDF converters.
- Single edit revisions (`Rev = 1`) with `0` minutes spent editing.

The Lecturer's Stone checks both **File Metadata** and **Multiple AI Detectors** in one place, and lets you clean metadata while keeping the original creation date intact.

---

## What It Checks

### 1. Metadata & File Details
- **Author Discovery**: Finds all original authors, last modifiers, comment authors, and contributors across Word, Excel, PowerPoint, and PDF files.
- **Usual AI & Script Tells**: Flags known library signatures including:
  - `PptxGenJS`, `python-pptx` (PowerPoint generators & default 2013 date)
  - `openpyxl`, `XlsxWriter`, `SheetJS / xlsx`, `ExcelJS` (Excel generators)
  - `python-docx`, `docx.js`, `docx4j` (Word document generators & default 2013 date)
  - `ReportLab`, `pyFPDF`, `FPDF2`, `WeasyPrint`, `wkhtmltopdf`, `jsPDF`, `PDFKit`, `borb`, `pypdf` (PDF generators)
  - `Chromium / Skia / Headless Chrome / Puppeteer / Playwright` (Browser-printed PDFs)
  - `Apache POI`, `EPPlus`, `PhpSpreadsheet`, `Typst` (Multi-platform Office generators)
  - Common AI model tags (`ChatGPT`, `GPT-4`, `Claude`, `Anthropic`, `Gemini`, `DeepSeek`, `Copilot`, `Ollama`, etc.)
  - AI presentation & writing tools (`Gamma`, `Tome`, `Beautiful.ai`, `SlidesAI`, `Decktopus`, `PopAI`, `Plus AI`, `Canva`, `SciSpace`, `Jenni AI`, `Notion`, etc.)
- **Editing Time**: Flags files saved with 0 minutes of editing or only 1 revision.

### 2. AI Content Detectors
- **Local DeBERTa (`desklib/ai-text-detector-v1.01`)**: High-accuracy model from the RAID AI Detection Benchmark. Runs locally on CUDA GPU (or CPU) with sliding window chunking across long documents.
- **TrustSafeAI RADAR**: Adversarial AI detector trained to catch paraphrased AI text.
- **Fakespot AI Classifier**: Transformer text classifier.
- **SzegedAI DeBERTa**: DeBERTa-based detector for fine-grained probability scores.
- **PirateXX RoBERTa**: Multi-tier transformer detector.
- **YugamJ LLM Detector**: Fine-tuned detector calibrated for ChatGPT and modern LLMs.
- **Burstiness & Sentence Variation**: Offline analyzer measuring sentence length variety, word diversity, and common AI transition phrases.

---

## Cleaning Metadata

The built-in cleaner strips identifying metadata while keeping the document working and looking normal:

- Changes Creator and Last Modifier to your chosen author name (from `LECTURERS_STONE_AUTHOR` or `--author`).
- **Keeps Original Creation Date**: Preserves the original file creation timestamp so it doesn't look like it was created two minutes ago.
- Cleans script and generator tags (`openpyxl`, `python-docx`, `python-pptx`, `iText`, `ReportLab`, AI tools).
- Removes company names, manager fields, and template paths.
- Sets standard revision numbers and application names (`Microsoft Word`, `Microsoft Excel`, `Microsoft PowerPoint`).

---

## Quickstart

### Installation

Clone the repository and install dependencies:

```powershell
git clone https://github.com/7adel32/lecturers-stone.git
cd lecturers-stone
pip install -r requirements.txt
```

Set up your default author name:

```powershell
cp .env.example .env
```

Edit `.env` to configure your name:

```env
LECTURERS_STONE_AUTHOR="Your Name"
```

---

## Command Line Usage

### 1. Check Document (AI + Metadata)

Checks metadata tells and runs all text detectors:

```powershell
# Word Document
python cli.py -f "path\to\document.docx"

# PDF Document
python cli.py -f "path\to\document.pdf"

# Spreadsheet or Presentation
python cli.py -f "path\to\sheet.xlsx"
python cli.py -f "path\to\slides.pptx"
```

### 2. Fast Metadata Check Only (Skip AI Models)

Checks file metadata and script tells in under 0.2 seconds:

```powershell
python cli.py -f "path\to\document.docx" --skip-ai
```

### 3. Clean Document Metadata (Keep Original Date)

```powershell
python cli.py -f "draft.docx" --cleanse "submission.docx" --skip-ai
```

### 4. Check Plain Text

```powershell
python cli.py -t "Paste essay or article text here..."
```

### 5. Export JSON Report

```powershell
python cli.py -f "document.docx" --json --export "report.json"
```

---

## Web Dashboard

Launch the dashboard locally at `http://127.0.0.1:7865`:

```powershell
python app.py
```

Features:
- Click the Stone logo to toggle Dark / Light mode.
- Drag-and-drop document upload (`.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt`, `.md`).
- Overall AI probability bar and individual detector breakdowns.
- Metadata details showing found authors, timestamps, and generator tells.
- One-click button to download cleaned documents directly.

---

## Hermes Agent Automation

The repository includes a Hermes Agent automation script under `integrations/hermes/aicheck.py`. Hermes is a good way to automate this for 24/7 background monitoring, recurring folder checks, or receiving instant analysis reports via messaging channels (such as WhatsApp).

### Running via Hermes CLI

```bash
# Evaluate document text and metadata
python3 integrations/hermes/aicheck.py -f "path/to/document.docx"

# Fast metadata check only (0.1s, skips AI models)
python3 integrations/hermes/aicheck.py -f "path/to/document.pptx" --skip-ai

# Clean document metadata and preserve creation date
python3 integrations/hermes/aicheck.py -f "draft.docx" --cleanse "cleaned.docx" --author "Author Name"

# Check raw text string
python3 integrations/hermes/aicheck.py "Paste text to evaluate..."
```

### Background Monitoring & Notifications

You can leverage Hermes cron jobs (`hermes cron`) to automatically monitor submission folders and deliver concise summaries to your notification channels without manual intervention.

---

## Project Structure

```text
lecturers-stone/
├── app.py                # Main entry point (launches Web GUI or CLI)
├── cli.py                # Standalone command-line interface
├── web_gui.py            # Gradio Web dashboard
├── checker_hub.py        # Multi-model AI detection framework
├── metadata_forensics.py # Metadata inspector, clue finder, and cleaner
├── local_detector.py     # Local DeBERTa GPU model runner (CUDA / CPU)
├── heuristic_engine.py   # Burstiness & sentence variation engine
├── document_parser.py    # Document text parser (DOCX, XLSX, PPTX, PDF, TXT)
├── integrations/
│   └── hermes/
│       └── aicheck.py    # Hermes Agent automation & notification script
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
