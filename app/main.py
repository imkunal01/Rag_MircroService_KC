from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

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

app.include_router(router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Root health-check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Lightweight liveness probe — confirms the API is running."""
    return {"status": "ok", "message": "API running"}


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health-check endpoint."""
    return {
        "status": "healthy",
        "version": app.version,
        "service": app.title,
    }
