from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/health")
async def health_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
