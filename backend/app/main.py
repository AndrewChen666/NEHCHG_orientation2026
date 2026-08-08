from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_pool, open_pool
from .dependencies import get_auth_context
from .realtime import EventBroker
from .routers import actions, auth, health, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.db_pool = await open_pool(settings.database_url)
    app.state.event_broker = EventBroker()
    yield
    await close_pool(app.state.db_pool)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(actions.router)

    @app.websocket("/api/v1/sessions/{session_id}/stream")
    async def session_stream(websocket: WebSocket, session_id: str):
        await websocket.accept()
        broker: EventBroker | None = None
        parsed_session_id = None
        try:
            context = await get_auth_context(websocket.headers.get("authorization"), settings)
            if str(context.session_id) != session_id:
                await websocket.close(code=1008, reason="session mismatch")
                return
            from uuid import UUID

            parsed_session_id = UUID(session_id)
            broker = websocket.app.state.event_broker
            await broker.subscribe(parsed_session_id, websocket)
            await websocket.send_json({"type": "stream.ready", "session_id": session_id})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            if broker is not None and parsed_session_id is not None:
                await broker.unsubscribe(parsed_session_id, websocket)
        except Exception:
            if broker is not None and parsed_session_id is not None:
                await broker.unsubscribe(parsed_session_id, websocket)
            await websocket.close(code=1011)

    return app


app = create_app()
