import fitz

from app.ingestion.pdf_parser import chunk_page, clean_text
from app.retrieval.retriever import terms

def test_clean_text():
    assert clean_text("hello   world\n\n\nnext") == "hello world\n\nnext"

def test_chunk_page_has_page_number():
    chunks = chunk_page("A short research passage.", 3)
    assert chunks[0]["page_number"] == 3
    assert "research" in chunks[0]["content"]

def test_terms_removes_common_words():
    result = terms("What is the proposed neural network model?")
    assert "proposed" in result
    assert "what" not in result

def test_parse_pdf_preserves_page_provenance(tmp_path):
    path = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A study of neural networks and scientific methods.")
    doc.save(path)
    doc.close()

    from app.ingestion.pdf_parser import parse_pdf
    parsed = parse_pdf(str(path))
    assert parsed["page_count"] == 1
    assert parsed["chunks"]
    assert parsed["chunks"][0]["page_number"] == 1

def test_parse_pdf_rejects_non_pdf(tmp_path):
    from app.ingestion.pdf_parser import PDFParseError, parse_pdf
    path = tmp_path / "not-a-pdf.pdf"
    path.write_text("not a PDF")
    try:
        parse_pdf(str(path))
    except PDFParseError:
        pass
    else:
        raise AssertionError("parse_pdf should reject invalid PDF data")
