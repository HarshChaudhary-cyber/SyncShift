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

SUPPORTED_EXTENSIONS = {
    ".ics", ".ical",
    ".pdf",
    ".docx",
    ".pptx",
    ".txt", ".csv",
    ".jpg", ".jpeg", ".png",
}

LEGACY_EXTENSIONS = {".doc", ".ppt"}

SUPPORTED_READABLE = "ics, pdf, docx, pptx, txt, csv, jpg, png"


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
        return _extract_pdf(content), False

    if ext == ".docx":
        return _extract_docx(content), False

    if ext == ".pptx":
        return _extract_pptx(content), False

    if ext in (".txt", ".csv"):
        return content.decode("utf-8", errors="replace"), False

    if ext in (".jpg", ".jpeg", ".png"):
        return _extract_image(content), True

    # Unreachable but kept for safety
    raise ValueError(f"Unsupported file type '{ext}'. Supported: {SUPPORTED_READABLE}")


# ──────────────────────────────────────────────────────────────────────────────
# PDF
# ──────────────────────────────────────────────────────────────────────────────

def _extract_pdf(content: bytes) -> str:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise ValueError("PDF support requires 'pdfplumber'. Run: pip install pdfplumber")

    lines: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            # 1. Paragraph text
            raw_text = page.extract_text()
            if raw_text:
                lines.append(raw_text)

            # 2. Table rows (join cells with spaces, rows with newlines)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    cells = [str(c).strip() for c in row if c]
                    if cells:
                        lines.append("  ".join(cells))

    return "\n".join(lines)


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
        text: str = pytesseract.image_to_string(img)
        return text
    except pytesseract.TesseractNotFoundError:
        # Tesseract binary not in PATH
        return ""
    except Exception:
        return ""
