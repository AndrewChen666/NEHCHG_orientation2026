from collections.abc import AsyncIterator

import asyncpg
from fastapi import HTTPException, Request


async def open_pool(database_url: str | None) -> asyncpg.Pool | None:
    if not database_url:
        return None
    return await asyncpg.create_pool(database_url, min_size=1, max_size=10, command_timeout=10)


async def close_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()


async def get_pool(request: Request) -> AsyncIterator[asyncpg.Pool]:
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "DATABASE_UNAVAILABLE", "message": "遊戲資料庫尚未連線。"})
    yield pool

