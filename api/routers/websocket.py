from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/websocket", tags=["websocket"])

@router.get("/health")
async def websocket_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
