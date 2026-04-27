from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", tags=["Health"])
async def ping():
    """Quick sanity-check for the v1 router."""
    return {"ping": "pong"}
