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
# Single Word, PDF, Spreadsheet, or Presentation Document
python cli.py -f "path\to\document.docx"
python cli.py -f "path\to\document.pdf"
python cli.py -f "path\to\sheet.xlsx"
python cli.py -f "path\to\slides.pptx"

# Batch Documents (Mix of different types, directories, or glob patterns)
python cli.py -f "doc1.docx" "sheet.xlsx" "slides.pptx" "paper.pdf" "notes.md"
python cli.py -f "submissions_folder/"
python cli.py -f "documents/*.docx" "documents/*.pdf"
```

### 2. Fast Metadata Check Only (Skip AI Models)

Checks file metadata and script tells across single files or batches in under 0.2 seconds:

```powershell
python cli.py -f "path\to\document.docx" --skip-ai

# Batch metadata forensics
python cli.py -f "submissions/" --skip-ai
```

### 3. Clean Document Metadata (Keep Original Date)

Cleanses metadata for single documents or entire batches:

```powershell
# Single document
python cli.py -f "draft.docx" --cleanse "submission.docx" --skip-ai

# Batch cleansing (writes cleansed files into output directory)
python cli.py -f "drafts/" --cleanse "cleaned_submissions/" --author "Your Name" --skip-ai
```

### 4. Check Plain Text

```powershell
python cli.py -t "Paste essay or article text here..."
```

### 5. Export JSON Report

```powershell
python cli.py -f "document.docx" --json --export "report.json"

# Batch export for multiple files
python cli.py -f "submissions/" --json --export "batch_report.json"
```

---

## Web Dashboard

Launch the dashboard locally at `http://127.0.0.1:7865`:

```powershell
python app.py
```

Features:
- Click the Stone logo to toggle Dark / Light mode.
- Drag-and-drop single or multiple document uploads (`.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt`, `.md`) with batch summary overview.
- Overall AI probability bar and individual detector breakdowns.
- Metadata details showing found authors, timestamps, and generator tells.
- One-click button to cleanse metadata and download cleansed document batches.
- Side-by-Side Word Diff (`.docx`) generator with inline word-level highlights (runs on CPU).

---

## Side-by-Side Word Diff & Optional Local Humanizer

`humanizer.py` provides two standalone utilities:

1. **Side-by-Side Word Diff (`compare`, CPU-only)**:
   Generates a landscape 2-column comparison `.docx` (`*_SideBySide.docx`) with inline word-level highlights (red strikethrough = deleted, green underline = added):

   ```powershell
   python humanizer.py compare -orig "report.docx" -rev "report_revised.docx" -o "report_SideBySide.docx"
   ```

2. **Optional Local Text Humanizer (`humanize`, requires local Ollama + GPU)**:
   Rewrites `.docx` paragraphs into third-person academic prose via a local Ollama server (`http://localhost:11434`, `Smaug-Humanizer`) while preserving native Word OMML math (`<m:oMath>`). This is **not** enabled by default in the Web GUI or CLI:

   ```powershell
   python humanizer.py humanize -i "report.docx" -o "report_humanized.docx"
   ```

---

## Hermes Agent Automation

The repository includes a Hermes Agent automation script under `integrations/hermes/aicheck.py`. Hermes is a good way to automate this for 24/7 background monitoring, recurring folder checks, or receiving instant analysis reports via messaging channels (such as WhatsApp).

### Running via Hermes CLI

```bash
# Evaluate document text and metadata (single or batch)
python3 integrations/hermes/aicheck.py -f "path/to/document.docx"
python3 integrations/hermes/aicheck.py -f "doc1.docx" "sheet.xlsx" "slides.pptx" "paper.pdf"

# Fast metadata check only (0.1s, skips AI models)
python3 integrations/hermes/aicheck.py -f "submissions/" --skip-ai

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
├── humanizer.py          # Side-by-side DOCX diff & optional local Ollama humanizer
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
