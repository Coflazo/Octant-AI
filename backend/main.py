"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from backend.health import router as health_router, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.pulse import ConnectionManager

logger = logging.getLogger(__name__)


# ── Global singleton connection manager ──────────────────────────────────

manager = ConnectionManager()




# ── Lifespan context manager ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: setup on startup, teardown on shutdown.

    On startup: log the configuration summary and ensure output directories
    exist. On shutdown: disconnect all active WebSocket sessions gracefully.

    Args:
        app: The FastAPI application instance.

    Yields:
        Nothing — the app runs during the yield.
    """
    settings = get_settings()
    logger.info(
        "Octant AI starting — log_level=%s, cors_origins=%s",
        settings.LOG_LEVEL,
        settings.cors_origin_list,
    )

    
    # Ensure output directories exist
    import os
    os.makedirs(settings.REPORTS_OUTPUT_PATH, exist_ok=True)
    os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)

    yield

    
    # Graceful shutdown: close all WebSocket connections
    logger.info("Octant AI shutting down — disconnecting %d sessions", len(manager.active_connections))
    for session_id in list(manager.active_connections.keys()):
        await manager.disconnect(session_id)
    logger.info("Shutdown complete.")




# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Octant AI",
    description="Autonomous quantitative research workbench",
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS middleware ──────────────────────────────────────────────────────

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mount static files for generated reports ─────────────────────────────

import os
if os.path.isdir(settings.REPORTS_OUTPUT_PATH):
    app.mount(
        "/static/reports",
        StaticFiles(directory=settings.REPORTS_OUTPUT_PATH),
        name="reports",
    )


# ── Register API routers ────────────────────────────────────────────────

from backend.routers.pipeline import router as pipeline_router
from backend.routers.voice import router as voice_router
from backend.routers.reports import router as reports_router

app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])




# ── WebSocket endpoint — PULSE protocol ─────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Accept a WebSocket connection and register it for PULSE event delivery.

    The connection is held open for the duration of the pipeline run. All
    PULSE events (status updates, hypothesis cards, citation cards, ticker
    cards, metric results, report sections) are pushed through this socket.
    Binary audio chunks from the Reson8 voice input flow upstream through
    the same connection.

    Args:
        websocket: The incoming WebSocket connection.
        session_id: Unique session identifier for this pipeline run.
    """
    await manager.connect(websocket, session_id)
    logger.info("WebSocket connected — session_id=%s", session_id)

    try:
        while True:
                        # Keep the connection alive and receive any client messages
                        # (e.g., binary audio chunks for voice transcription, control messages)
            data = await websocket.receive()

            if "text" in data:
                                # Text messages are control commands (e.g., stop, restart)
                text = data["text"]
                logger.debug("WebSocket text received — session=%s, msg=%s", session_id, text[:100])

            elif "bytes" in data:
                                # Binary messages are audio chunks for Reson8 transcription
                audio_chunk = data["bytes"]
                logger.debug(
                    "WebSocket audio chunk received — session=%s, bytes=%d",
                    session_id,
                    len(audio_chunk),
                )
                                # Audio processing is handled by the voice router subscription
                await manager.handle_audio_chunk(session_id, audio_chunk)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected — session_id=%s", session_id)
        await manager.disconnect(session_id)
    except Exception as exc:
        logger.error(
            "WebSocket error — session_id=%s, error=%s",
            session_id,
            str(exc),
            exc_info=True,
        )
        await manager.disconnect(session_id)
