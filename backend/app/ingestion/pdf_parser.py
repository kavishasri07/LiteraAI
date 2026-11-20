import re
import pymupdf as fitz
from app.core.config import settings

class PDFParseError(ValueError):
    """Raised when a PDF cannot be safely opened or contains no usable text."""

def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_page(text: str, page_number: int):
    text = clean_text(text)
    if not text:
        return []
    size = settings.chunk_size
    overlap = min(settings.chunk_overlap, max(0, size // 3))
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        segment = text[start:end].strip()
        if segment:
            chunks.append({"page_number": page_number, "section": None, "content": segment})
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks

def parse_pdf(path: str):
    try:
        doc = fitz.open(path)
    except (fitz.FileDataError, RuntimeError) as exc:
        raise PDFParseError("The uploaded file is not a readable PDF.") from exc
    try:
        page_count = doc.page_count
        if not doc.is_pdf or page_count == 0:
            raise PDFParseError("The uploaded PDF does not contain any pages.")
        if page_count > settings.max_pdf_pages:
            raise PDFParseError(f"The PDF has too many pages. The limit is {settings.max_pdf_pages} pages.")
        pages = []
        all_chunks = []
        for idx, page in enumerate(doc):
            text = clean_text(page.get_text("text"))
            pages.append({"page_number": idx + 1, "text": text})
            all_chunks.extend(chunk_page(text, idx + 1))
    finally:
        doc.close()
    return {"page_count": page_count, "pages": pages, "chunks": all_chunks}
