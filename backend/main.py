"""Octant AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.health import router as health_router
from backend.ws_manager import manager

logger = logging.getLogger(__name__)








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

# Mount sparkline images directory
sparkline_dir = "/tmp/octant_reports/sparklines"
os.makedirs(sparkline_dir, exist_ok=True)
app.mount(
    "/static/sparklines",
    StaticFiles(directory=sparkline_dir),
    name="sparklines",
)




# ── Register API routers ────────────────────────────────────────────────

from backend.routers.pipeline import router as pipeline_router
from backend.routers.reports import router as reports_router

app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(health_router, tags=["Health"])








# ── WebSocket endpoint — PULSE protocol ─────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Accept a WebSocket connection and register it for PULSE event delivery.

    Args:
        websocket: The incoming WebSocket connection.
        session_id: Unique session identifier for this pipeline run.
    """
    await manager.connect(websocket, session_id)
    logger.info("WebSocket connected — session_id=%s", session_id)

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                text = data["text"]
                logger.debug("WebSocket text received — session=%s, msg=%s", session_id, text[:100])

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
