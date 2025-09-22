from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/freedom", tags=["freedom"])

@router.get("/health")
async def freedom_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
