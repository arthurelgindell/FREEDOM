from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/castle", tags=["castle"])

@router.get("/health")
async def castle_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
