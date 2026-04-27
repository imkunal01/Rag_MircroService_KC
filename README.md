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
# LLM provider (Gemini)
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-latest

# External product backend API (required for products endpoints)
PRODUCTS_API_URL=http://localhost:5000/api/products
PRODUCTS_API_TIMEOUT_SECONDS=2.0
PRODUCTS_SYNC_INTERVAL_SECONDS=30
```

If `PRODUCTS_API_URL` is not set or unreachable, `/api/products` and related recommendation flows return `503 Service Unavailable` and log an error.
