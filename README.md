# RAG-Powered Product Recommendation API

A Retrieval-Augmented Generation (RAG) backend built with **FastAPI** that returns personalised product recommendations based on natural-language queries.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/routes.py            # Route definitions
│   ├── models/schema.py         # Pydantic schemas
│   ├── services/
│   │   └── recommendation_service.py
│   ├── rag/
│   │   ├── embeddings.py        # Embedding utilities
│   │   ├── vector_store.py      # FAISS / Chroma wrapper
│   │   ├── retriever.py         # Semantic retrieval
│   │   ├── generator.py         # LLM response generation
│   │   └── query_parser.py      # Query pre-processing
│   ├── data/products.json       # Product dataset
│   └── utils/helpers.py         # Shared utilities
├── requirements.txt
└── README.md
```

---

## Phases

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Running FastAPI server (`GET /` → "API running") | ✅ Done |
| 1 | Product CRUD endpoints + Pydantic schemas | 🔜 |
| 2 | RAG pipeline — embeddings + vector store | 🔜 |
| 3 | LLM-based recommendation generation | 🔜 |
| 4 | Query parsing + ranking | 🔜 |

---

## Quickstart (Phase 0)

### 1. Create & activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

### 4. Verify

```
GET http://127.0.0.1:8000/
→ { "status": "ok", "message": "API running" }

GET http://127.0.0.1:8000/health
→ { "status": "healthy", "version": "0.1.0", "service": "RAG Recommendation API" }

GET http://127.0.0.1:8000/api/v1/ping
→ { "ping": "pong" }
```

Interactive docs: **http://127.0.0.1:8000/docs**

---

## Environment Variables

Create a `.env` file in the project root (never commit this):

```env
# Example — will be used from Phase 1 onwards
# OPENAI_API_KEY=sk-...
```
