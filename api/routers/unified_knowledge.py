from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/unified_knowledge", tags=["unified_knowledge"])

@router.get("/health")
async def unified_knowledge_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
