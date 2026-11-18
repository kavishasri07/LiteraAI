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
