import uuid, shutil
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.database.db import init_db, db_session
from app.ingestion.pdf_parser import PDFParseError, parse_pdf
from app.retrieval.retriever import retrieve
from app.llm.extractive_answer import extractive_answer
from app.llm.ollama_client import generate_answer
from app.reasoning.analysis import compare_papers, research_gaps, build_graph
from app.api.schemas import ChatRequest, CompareRequest, GapRequest

app = FastAPI(title="LiteraAI API", version="0.1.0", description="Local-first, evidence-grounded research intelligence MVP")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    init_db()

def get_papers(ids=None):
    with db_session() as conn:
        if ids:
            marks = ",".join("?" for _ in ids)
            rows = conn.execute(f"SELECT * FROM papers WHERE id IN ({marks}) ORDER BY created_at DESC", ids).fetchall()
        else:
            rows = conn.execute("SELECT * FROM papers ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def get_chunks(ids=None):
    with db_session() as conn:
        if ids:
            marks = ",".join("?" for _ in ids)
            rows = conn.execute(f"SELECT * FROM chunks WHERE paper_id IN ({marks}) ORDER BY page_number", ids).fetchall()
        else:
            rows = conn.execute("SELECT * FROM chunks ORDER BY paper_id,page_number").fetchall()
        result = {}
        for r in rows:
            result.setdefault(r["paper_id"], []).append(dict(r))
        return result

@app.get("/")
def root():
    return {"name": "LiteraAI", "status": "running", "docs": "/docs"}

@app.get("/api/health")
def health():
    return {"status": "ok", "ollama_enabled": settings.ollama_enabled, "model": settings.ollama_model if settings.ollama_enabled else None}

@app.post("/api/ingestion/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(400, "The uploaded file does not have a valid PDF header.")
    paper_id = str(uuid.uuid4())
    safe_name = Path(file.filename).name
    dest = settings.uploads_path / f"{paper_id}.pdf"
    dest.write_bytes(content)
    try:
        parsed = parse_pdf(str(dest))
    except PDFParseError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, str(exc))
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "Could not parse the uploaded PDF.")
    if not parsed["chunks"]:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "No selectable text was found. Scanned PDFs need OCR, which is not included in this MVP.")
    title = next((p["text"].splitlines()[0][:180] for p in parsed["pages"] if p["text"].strip()), Path(safe_name).stem)
    try:
        with db_session() as conn:
            conn.execute("INSERT INTO papers(id,title,filename,file_path,page_count,status,created_at) VALUES(?,?,?,?,?,?,?)",
                         (paper_id,title,safe_name,str(dest),parsed["page_count"],"processed",datetime.now(timezone.utc).isoformat()))
            for chunk in parsed["chunks"]:
                cur = conn.execute("INSERT INTO chunks(paper_id,page_number,section,content) VALUES(?,?,?,?)",
                                   (paper_id,chunk["page_number"],chunk["section"],chunk["content"]))
                try:
                    conn.execute("INSERT INTO chunks_fts(content,paper_id,chunk_id) VALUES(?,?,?)",(chunk["content"],paper_id,cur.lastrowid))
                except Exception:
                    pass
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, "The PDF was read, but could not be saved to the local research library.")
    return {"paper_id": paper_id, "title": title, "page_count": parsed["page_count"], "chunks_created": len(parsed["chunks"]), "status": "processed",
            "warning": "No text was extracted. This may be a scanned PDF; OCR is not included in the MVP." if not parsed["chunks"] else None}

@app.get("/api/papers")
def list_papers():
    return get_papers()

@app.get("/api/papers/{paper_id}")
def paper_detail(paper_id: str):
    papers = get_papers([paper_id])
    if not papers:
        raise HTTPException(404, "Paper not found")
    return papers[0]

@app.get("/api/papers/{paper_id}/elements")
def paper_elements(paper_id: str):
    paper = get_papers([paper_id])
    if not paper:
        raise HTTPException(404, "Paper not found")
    return get_chunks([paper_id]).get(paper_id, [])

@app.get("/api/papers/{paper_id}/pdf")
def paper_pdf(paper_id: str):
    paper = get_papers([paper_id])
    if not paper:
        raise HTTPException(404, "Paper not found")
    path = Path(paper[0]["file_path"])
    if not path.exists():
        raise HTTPException(404, "PDF file missing from local storage")
    return FileResponse(path, media_type="application/pdf", filename=paper[0]["filename"])

@app.delete("/api/papers/{paper_id}")
def delete_paper(paper_id: str):
    papers = get_papers([paper_id])
    if not papers:
        raise HTTPException(404, "Paper not found")
    with db_session() as conn:
        try:
            conn.execute("DELETE FROM chunks_fts WHERE paper_id=?", (paper_id,))
        except Exception:
            pass
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
    Path(papers[0]["file_path"]).unlink(missing_ok=True)
    return {"deleted": True, "paper_id": paper_id}

@app.post("/api/chat")
def chat(req: ChatRequest):
    evidence = retrieve(req.question, req.paper_ids, limit=6)
    if not evidence:
        return {"answer": f"I couldn't find passages matching the key terms in “{req.question}” in the uploaded papers. Try a more specific question or upload additional papers.",
                "citations": [], "verification": "insufficient_evidence", "retrieval_mode": "local_lexical_mvp"}
    answer = generate_answer(req.question, evidence)
    if not answer:
        answer = extractive_answer(req.question, evidence)
    citations = [{"id": i, "paper_id": e["paper_id"], "paper_title": e["title"], "page_number": e["page_number"],
                  "section": e["section"], "snippet": e["content"][:500], "confidence": "retrieved_match"} for i,e in enumerate(evidence,1)]
    return {"answer": answer, "citations": citations, "verification": "retrieval_match_not_semantic_verification",
            "retrieval_mode": "local_lexical_mvp"}

@app.post("/api/compare")
def compare(req: CompareRequest):
    papers = get_papers(req.paper_ids)
    if len(papers) < 2:
        raise HTTPException(400, "Select at least two existing papers.")
    return {"comparison": compare_papers(papers, get_chunks(req.paper_ids)), "note": "MVP heuristic extraction; verify each field against the cited source papers."}

@app.post("/api/research-gaps/analyze")
def gaps(req: GapRequest):
    papers = get_papers(req.paper_ids)
    if not papers:
        raise HTTPException(400, "Upload papers before running gap analysis.")
    return {"papers_analyzed": len(papers), "scope": "selected uploaded corpus only", "gaps": research_gaps(papers, get_chunks([p["id"] for p in papers])),
            "disclaimer": "These are heuristic, corpus-bounded leads—not proof of global novelty or independently verified research gaps."}

@app.get("/api/graph")
def graph(paper_ids: str | None = None):
    ids = [x for x in (paper_ids or "").split(",") if x] or None
    papers = get_papers(ids)
    return build_graph(papers, get_chunks([p["id"] for p in papers]))

@app.post("/api/evaluation/run")
def evaluation_run():
    papers = get_papers()
    chunks = get_chunks()
    queries = []
    for p in papers[:5]:
        sample = chunks.get(p["id"], [])
        if sample:
            words = [w for w in sample[0]["content"].split() if len(w) > 5][:4]
            if words:
                queries.append(" ".join(words))
    results = []
    for q in queries:
        hits = retrieve(q, limit=5)
        results.append({"query": q, "retrieved": len(hits), "top_paper": hits[0]["title"] if hits else None})
    return {"evaluation_type": "smoke_test_not_a_research_benchmark", "queries": results, "papers_in_corpus": len(papers),
            "warning": "Use a manually labelled query/relevance dataset before reporting Precision@K, Recall@K, MRR, faithfulness or citation accuracy."}

@app.get("/api/evaluation/history")
def evaluation_history():
    return []

@app.get("/api/evaluation/summary")
def evaluation_summary():
    return {"status": "MVP", "available_metrics": ["retrieval smoke-test counts"], "not_yet_implemented": ["Precision@K", "Recall@K", "MRR", "answer correctness", "faithfulness", "citation accuracy", "latency benchmark"]}
