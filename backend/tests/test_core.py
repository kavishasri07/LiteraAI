import pymupdf as fitz

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

def test_request_models_bound_collection_size_and_reject_unknown_fields():
    from pydantic import ValidationError
    from app.api.schemas import ChatRequest, CompareRequest

    assert ChatRequest(question="  How does this work?  ").question == "How does this work?"
    try:
        ChatRequest(question="A valid question", unexpected="value")
    except ValidationError:
        pass
    else:
        raise AssertionError("unknown request fields should be rejected")
    try:
        CompareRequest(paper_ids=[str(i) for i in range(51)])
    except ValidationError:
        pass
    else:
        raise AssertionError("oversized paper collections should be rejected")

def test_security_headers_are_set_on_api_responses():
    import asyncio
    from app.main import security_headers
    from starlette.responses import Response

    async def next_response(_request):
        return Response()

    response = asyncio.run(security_headers(None, next_response))
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"

def test_retrieval_counts_terms_once_per_token(monkeypatch):
    from contextlib import contextmanager
    from app.retrieval import retriever

    class FakeConnection:
        def execute(self, *_args):
            return self
        def fetchall(self):
            return [{"id": 1, "paper_id": "p1", "page_number": 1, "section": "Results",
                     "content": "neural neural network model improves accuracy", "title": "Study"}]

    @contextmanager
    def fake_session():
        yield FakeConnection()

    monkeypatch.setattr(retriever, "db_session", fake_session)
    results = retriever.retrieve("neural model", limit=1)
    assert len(results) == 1
    assert results[0]["paper_id"] == "p1"
    assert results[0]["score"] > 0

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

def test_parse_pdf_rejects_page_count_over_limit(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.ingestion.pdf_parser import PDFParseError, parse_pdf

    path = tmp_path / "too-many-pages.pdf"
    doc = fitz.open()
    for _ in range(settings.max_pdf_pages + 1):
        doc.new_page()
    doc.save(path)
    doc.close()
    try:
        parse_pdf(str(path))
    except PDFParseError as exc:
        assert "too many pages" in str(exc)
    else:
        raise AssertionError("parse_pdf should reject PDFs over the configured page limit")

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
