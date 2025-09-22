from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/council", tags=["council"])

@router.get("/health")
async def council_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}