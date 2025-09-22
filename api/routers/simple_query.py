from fastapi import APIRouter

# Legacy stub router for import compatibility
router = APIRouter(prefix="/simple_query", tags=["simple_query"])

@router.get("/health")
async def simple_query_health():
    return {"status": "legacy_stub", "message": "Active service at localhost:8080"}
