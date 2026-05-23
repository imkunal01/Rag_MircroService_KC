import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.rag.pinecone_store import get_pinecone_store

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Recommendation API",
    description="A Retrieval-Augmented Generation (RAG) powered product recommendation engine.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins during development; tighten before production
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(router, prefix="/api")


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_validation():
    """Fail fast when required Pinecone configuration or connectivity is invalid."""
    get_pinecone_store().init()


# ---------------------------------------------------------------------------
# Root health-check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Lightweight liveness probe — confirms the API is running."""
    return {"status": "ok", "message": "API running"}


@app.get("/health", tags=["Health"])
async def health():
    """Liveness probe for the API process."""
    return {
        "status": "healthy",
        "version": app.version,
        "service": app.title,
    }


@app.get("/health/deps", tags=["Health"])
async def dependency_health():
    """Dependency health-check endpoint."""
    pinecone = get_pinecone_store().health_check()
    status_value = "healthy" if pinecone["status"] == "healthy" else "degraded"
    return {
        "status": status_value,
        "version": app.version,
        "service": app.title,
        "dependencies": {
            "pinecone": pinecone,
        },
    }


# ---------------------------------------------------------------------------
# Dev entrypoint  (python -m app.main)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
