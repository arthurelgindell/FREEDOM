from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.get("/health")
async def knowledge_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
