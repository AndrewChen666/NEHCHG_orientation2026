from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    return {
        "ok": True,
        "service": request.app.title,
        "database_connected": getattr(request.app.state, "db_pool", None) is not None,
    }

