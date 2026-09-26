"""
file_extractor.py – extract raw text from uploaded files.

Supported extensions:  .ics .ical .pdf .docx .pptx .txt .csv .jpg .jpeg .png
Legacy (rejected):     .doc .ppt
Unsupported (rejected): anything else

Returns:
    (text: str, is_ocr: bool)

Raises:
    ValueError  for unsupported or legacy types (caller converts to HTTP 400)
"""
from __future__ import annotations

import io
import csv
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, time
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".ics", ".ical",
    ".pdf",
    ".docx",
    ".doc", ".xlsx", ".xls",
    ".pptx",
    ".txt", ".csv",
    ".jpg", ".jpeg", ".png", ".webp",
}

LEGACY_EXTENSIONS = {".ppt"}

SUPPORTED_READABLE = "ics, pdf, doc, docx, pptx, xls, xlsx, txt, csv, jpg, png, webp"


def _ext(filename: str) -> str:
    """Return lowercase file extension including the dot."""
    idx = filename.rfind(".")
    return filename[idx:].lower() if idx != -1 else ""


def extract_text(content: bytes, filename: str) -> tuple[str, bool]:
    """
    Dispatch to the correct extractor based on file extension.

    Returns
    -------
    (text, is_ocr)
        text   – raw extracted text (may be empty)
        is_ocr – True only when pytesseract was used
    """
    ext = _ext(filename)

    if ext in (".xlsx", ".docx", ".pptx"):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError("Expanded document exceeds the 50 MB limit.")

    if ext in LEGACY_EXTENSIONS:
        raise ValueError(
            f"Please save the file as .docx / .pptx and re-upload. "
            f"Old binary formats ({ext}) cannot be parsed."
        )

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {SUPPORTED_READABLE}"
        )

    if ext in (".ics", ".ical"):
        # Caller handles ICS separately; just return the raw bytes as text
        return content.decode("utf-8", errors="replace"), False

    if ext == ".pdf":
        return _extract_pdf(content)

    if ext == ".docx":
        return _extract_docx(content), False

    if ext == ".doc":
        executable = shutil.which("antiword")
        if not executable:
            raise ValueError("Legacy Word conversion is unavailable on this server. Save as DOCX or PDF and upload again.")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timetable.doc"
            path.write_bytes(content)
            result = subprocess.run([executable, str(path)], capture_output=True, timeout=20, check=True)
            return result.stdout.decode("utf-8", errors="replace"), False

    if ext == ".xlsx":
        import openpyxl
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            if any((s.max_row or 0) > 10000 or (s.max_column or 0) > 100 for s in workbook):
                raise ValueError("Upload at most 10,000 rows and 100 columns per sheet.")
            return "\n".join(rows_to_text(sheet.iter_rows(max_row=min(sheet.max_row or 1, 10000),
                max_col=min(sheet.max_column or 1, 100), values_only=True)) for sheet in workbook), False
        finally:
            workbook.close()

    if ext == ".xls":
        import xlrd
        workbook = xlrd.open_workbook(file_contents=content, on_demand=True)
        try:
            sheets = []
            for sheet in workbook.sheets():
                if sheet.nrows > 10000 or sheet.ncols > 100:
                    raise ValueError("Upload at most 10,000 rows and 100 columns per sheet.")
                rows = []
                for r in range(min(sheet.nrows, 10000)):
                    row = []
                    for c in range(min(sheet.ncols, 100)):
                        cell = sheet.cell(r, c)
                        value = cell.value
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            value = xlrd.xldate_as_datetime(value, workbook.datemode)
                            if cell.value < 1:
                                value = value.time()
                        row.append(value)
                    rows.append(row)
                sheets.append(rows_to_text(rows))
            return "\n".join(sheets), False
        finally:
            workbook.release_resources()

    if ext == ".pptx":
        return _extract_pptx(content), False

    if ext == ".csv":
        text = content.decode("utf-8-sig")
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return rows_to_text(csv.reader(io.StringIO(text), dialect)), False

    if ext == ".txt":
        return content.decode("utf-8", errors="replace"), False

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        return _extract_image(content), True

    # Unreachable but kept for safety
    raise ValueError(f"Unsupported file type '{ext}'. Supported: {SUPPORTED_READABLE}")


def rows_to_text(rows):
    """Preserve tabular structure; normalize common schedule headers for local parsing."""
    lines, header = [], None
    for index, row in enumerate(rows):
        if index >= 10000:
            raise ValueError("A timetable may contain at most 10,000 rows per sheet.")
        cells = [v.strftime("%H:%M") if isinstance(v, time) else
                 v.strftime("%A") if isinstance(v, datetime) else str(v or "").strip() for v in row]
        aliases = {"day": "day", "weekday": "day", "day_of_week": "day", "day of week": "day",
            "start": "start", "start time": "start", "start_time": "start",
            "end": "end", "end time": "end", "end_time": "end", "finish": "end",
            "title": "title", "subject": "title", "course": "title", "class": "title",
            "location": "location", "room": "location"}
        candidate = {aliases[v.lower()]: i for i, v in enumerate(cells) if v.lower() in aliases}
        if {"day", "start", "end"} <= candidate.keys():
            header = candidate
            continue
        if header:
            values = {key: cells[i] if i < len(cells) else "" for key, i in header.items()}
            lines.append(f"{values['day']} {values['start']} - {values['end']} {values.get('title', '')} {values.get('location', '')}")
        elif any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# PDF
# ──────────────────────────────────────────────────────────────────────────────

def _extract_pdf(content: bytes) -> tuple[str, bool]:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise ValueError("PDF support requires 'pdfplumber'. Run: pip install pdfplumber")

    lines: list[str] = []
    used_ocr = False
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if len(pdf.pages) > 50:
            raise ValueError("Upload at most 50 timetable pages at a time.")
        for page in pdf.pages:
            # 1. Paragraph text
            raw_text = page.extract_text()
            if raw_text:
                lines.append(raw_text)
            else:
                import pytesseract
                try:
                    lines.append(pytesseract.image_to_string(page.to_image(resolution=150).original, timeout=20))
                    used_ocr = True
                except (pytesseract.TesseractNotFoundError, RuntimeError):
                    pass

            # 2. Table rows (join cells with spaces, rows with newlines)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    cells = [str(c).strip() for c in row if c]
                    if cells:
                        lines.append("  ".join(cells))

    return "\n".join(lines), used_ocr


# ──────────────────────────────────────────────────────────────────────────────
# DOCX
# ──────────────────────────────────────────────────────────────────────────────

def _extract_docx(content: bytes) -> str:
    try:
        import docx  # type: ignore
    except ImportError:
        raise ValueError("DOCX support requires 'python-docx'. Run: pip install python-docx")

    doc = docx.Document(io.BytesIO(content))
    lines: list[str] = []

    # Paragraphs
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                lines.append("  ".join(cells))

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# PPTX
# ──────────────────────────────────────────────────────────────────────────────

def _extract_pptx(content: bytes) -> str:
    try:
        from pptx import Presentation  # type: ignore
    except ImportError:
        raise ValueError("PPTX support requires 'python-pptx'. Run: pip install python-pptx")

    prs = Presentation(io.BytesIO(content))
    lines: list[str] = []

    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        lines.append(text)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Image (OCR via pytesseract) – gracefully optional
# ──────────────────────────────────────────────────────────────────────────────

def _extract_image(content: bytes) -> str:
    """
    Run Tesseract OCR on the image bytes.
    Returns empty string (instead of crashing) when:
    - pytesseract is not installed
    - Tesseract binary is not in PATH
    """
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return ""  # OCR libraries not installed – caller will surface an empty preview

    try:
        img = Image.open(io.BytesIO(content))
        text: str = pytesseract.image_to_string(img, timeout=20)
        return text
    except pytesseract.TesseractNotFoundError:
        # Tesseract binary not in PATH
        return ""
    except Exception:
        return ""
