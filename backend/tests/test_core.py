import fitz

from app.ingestion.pdf_parser import chunk_page, clean_text
from app.retrieval.retriever import terms
from app.llm.extractive_answer import extractive_answer

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

def test_extractive_answer_selects_sentence_for_question():
    evidence = [{
        "title": "Example study", "page_number": 2, "score": 1.0,
        "content": "The authors use a transformer architecture. The model achieves 92 percent accuracy.",
    }]
    method_answer = extractive_answer("What architecture was used?", evidence)
    result_answer = extractive_answer("What accuracy was reported?", evidence)
    assert "transformer architecture" in method_answer
    assert "92 percent accuracy" in result_answer
    assert method_answer != result_answer

def test_extractive_answer_does_not_present_unmatched_evidence_as_answer():
    evidence = [{"title": "Example study", "page_number": 1, "content": "The study evaluates a transformer model."}]
    answer = extractive_answer("What is the funding source?", evidence)
    assert "couldn't find a passage" in answer
