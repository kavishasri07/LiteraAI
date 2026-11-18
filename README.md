# LiteraAI — Local-First Research Intelligence MVP

LiteraAI turns uploaded academic PDFs into searchable research material. This MVP includes:
- PDF upload and text extraction with PyMuPDF, preserving page numbers.
- SQLite storage for papers and extracted chunks.
- Local retrieval using SQLite FTS5 when available, with a token-overlap fallback.
- Optional local Ollama generation; answers include source/page citations.
- Basic cross-paper comparison, corpus-bounded research-gap suggestions, knowledge graph data, and retrieval evaluation endpoints.
- React + Vite frontend with Dashboard, Library/Workspace, Assistant, Compare, Gaps, Graph and Evaluation views.

## Architecture note

This is an intentionally runnable MVP, not a claim that every advanced capability in the master specification is complete. This first build uses text-based PDF extraction and local lexical retrieval. Advanced table/figure/equation extraction, dense BGE embeddings + Qdrant, BM25 + RRF, cross-encoder reranking, semantic claim verification, and full benchmark datasets are planned next increments. The code marks these boundaries explicitly.

No paid API is required. Ollama is optional; without it, LiteraAI returns an extractive, citation-linked response from retrieved passages.

## Requirements

- Python 3.11+
- Node.js 20+
- Optional: Ollama installed locally and a model pulled, e.g. `ollama pull llama3.2:1b`

## 1. Start the backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows; on macOS/Linux use: cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Configuration

Edit `backend/.env`:
- `OLLAMA_ENABLED=false` by default. Set true to enable local Ollama.
- `OLLAMA_MODEL=llama3.2:1b`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `MAX_UPLOAD_MB=30`

## Current MVP behavior

1. Upload a text-based academic PDF from Workspace.
2. Backend extracts page text, splits it into overlapping chunks, and stores paper/chunk metadata in SQLite.
3. Ask a question in Assistant. LiteraAI retrieves matching chunks and returns citations such as `[1] Paper title, p. 4`.
4. Compare two or more uploaded papers using extracted text heuristics.
5. Generate potential research directions from limitations/gap-related passages. These are corpus-bounded suggestions, not proof of global novelty.
6. View a simple paper-to-topic graph.
7. Run a small retrieval smoke evaluation against your uploaded corpus.

Scanned PDFs without an embedded text layer need OCR; OCR is not included in this MVP.

## API overview

- `POST /api/ingestion/upload` — upload PDF
- `GET /api/papers` — list papers
- `GET /api/papers/{paper_id}` — paper details
- `GET /api/papers/{paper_id}/elements` — extracted page/chunk elements
- `GET /api/papers/{paper_id}/pdf` — original PDF
- `DELETE /api/papers/{paper_id}` — delete paper and file
- `POST /api/chat` — evidence-linked question answering
- `POST /api/compare` — compare selected papers
- `POST /api/research-gaps/analyze` — corpus-bounded gap suggestions
- `GET /api/graph` — graph nodes and edges
- `POST /api/evaluation/run` — retrieval smoke evaluation
- `GET /api/evaluation/history` — recent evaluation runs

## Data locations

Created automatically under `backend/data/`:
- `literaai.db` — SQLite database
- `uploads/` — uploaded source PDFs

Do not commit real research PDFs or private datasets unless you have permission.

## Tests

From `backend/`:

```bash
pip install -r requirements-dev.txt
pytest
```

## Roadmap after MVP

1. Add structured table, figure, caption and equation extraction modules.
2. Add BGE embeddings and persistent Qdrant collection.
3. Add BM25 + dense retrieval with Reciprocal Rank Fusion.
4. Add cross-encoder reranking and stronger claim-level evidence verification.
5. Add dedicated comparison schemas and richer graph entity extraction.
6. Build a labelled benchmark dataset before reporting performance metrics.
