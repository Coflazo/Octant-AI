"""
Octant AI — Pipeline API Router.

Provides endpoints to start, stop, and query the status of pipeline runs.
POST /start validates the incoming PipelineRequest, creates a session,
and enqueues the five-agent pipeline as a FastAPI background task.
POST /stop/{session_id} sets the stop flag so agents halt gracefully.
GET /status/{session_id} returns the current session state.
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.pulse import PulseEmitter

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_manager() -> "ConnectionManager":
    """Lazily import the global ConnectionManager to avoid circular imports.

    Returns:
        The global ConnectionManager singleton from backend.main.
    """
    from backend.main import manager
    return manager

# ── In-memory session store (replaced by SessionManager in Section 15) ──

_sessions: dict[str, dict] = {}


# ── Request / Response models ────────────────────────────────────────────

class TimeRange(BaseModel):
    """Backtest time range specification.

    Attributes:
        start_date: ISO date string for backtest start (e.g., "2015-01-01").
        end_date: ISO date string for backtest end (e.g., "2025-01-01").
    """
    start_date: str = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Backtest end date (YYYY-MM-DD)")


class PipelineRequest(BaseModel):
    """Request body for starting a new pipeline run.

    Attributes:
        thesis_str: Natural-language investment thesis from the researcher.
        exchanges: List of exchange codes to search for tickers.
        time_range: Backtest period start and end dates.
        sector_filter: Optional sector to filter the equity universe.
        session_id: Optional session ID; auto-generated if not provided.
    """
    thesis_str: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural-language investment thesis",
    )
    exchanges: List[str] = Field(
        default=["NYSE", "NASDAQ"],
        description="Exchange codes to build the universe from",
    )
    time_range: TimeRange = Field(
        default_factory=lambda: TimeRange(start_date="2015-01-01", end_date="2025-01-01"),
        description="Backtest time range",
    )
    sector_filter: Optional[str] = Field(
        default=None,
        description="Optional sector filter (e.g., 'Energy', 'Technology')",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID (auto-generated if not provided)",
    )


class PipelineStatusResponse(BaseModel):
    """Response body for pipeline status queries.

    Attributes:
        session_id: The session identifier.
        status: Current pipeline status string.
        current_agent: Which agent is currently running.
        pdf_url: URL to the compiled PDF report (null until complete).
    """
    session_id: str
    status: str
    current_agent: Optional[str] = None
    pdf_url: Optional[str] = None


class PipelineStartResponse(BaseModel):
    """Response body after successfully starting a pipeline.

    Attributes:
        session_id: The assigned session identifier.
        status: Initial status (always "started").
        message: Confirmation message.
    """
    session_id: str
    status: str = "started"
    message: str = "Pipeline started. Connect to WebSocket for PULSE events."


# ── Background pipeline task (placeholder until Section 15 orchestrator) ─

async def _run_pipeline_background(
    session_id: str,
    request: PipelineRequest,
) -> None:
    """Execute the full five-agent pipeline as a background task.

    This is a placeholder that will be replaced by the OctantOrchestrator
    in Section 15. For now, it emits a PULSE status event to confirm the
    WebSocket connection is working.

    Args:
        session_id: Unique session identifier for this run.
        request: The validated pipeline request parameters.
    """
    pulse = PulseEmitter(session_id, _get_manager())

    try:
        _sessions[session_id]["status"] = "running"
        _sessions[session_id]["current_agent"] = "hypothesis_engine"

        await pulse.emit_status(
            agent="hypothesis_engine",
            status="active",
            step=1,
            total=5,
            message_title="Pipeline started",
            message_subtitle=f"Thesis: {request.thesis_str[:60]}...",
            percent=0,
        )

        # Full orchestration will be wired in Section 15

        logger.info(
            "Pipeline background task running — session=%s, thesis=%s",
            session_id,
            request.thesis_str[:80],
        )

    except Exception as exc:
        _sessions[session_id]["status"] = "error"
        await pulse.emit_error(
            agent="pipeline",
            error_message=str(exc),
            traceback_str="",
            recovery_action="Check logs and retry.",
        )
        logger.error(
            "Pipeline failed — session=%s, error=%s",
            session_id,
            str(exc),
            exc_info=True,
        )


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
) -> PipelineStartResponse:
    """Start a new pipeline run.

    Validates the request, creates a session in the in-memory store,
    and enqueues the pipeline as a background task.

    Args:
        request: The pipeline configuration from the frontend.
        background_tasks: FastAPI background task manager.

    Returns:
        PipelineStartResponse with the assigned session_id.

    Raises:
        HTTPException: If a pipeline is already running for this session.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Prevent duplicate runs on the same session
    if session_id in _sessions and _sessions[session_id].get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for session {session_id}",
        )

    _sessions[session_id] = {
        "status": "starting",
        "current_agent": None,
        "pdf_url": None,
        "request": request.model_dump(),
    }

    background_tasks.add_task(_run_pipeline_background, session_id, request)

    logger.info("Pipeline enqueued — session=%s", session_id)

    return PipelineStartResponse(
        session_id=session_id,
        status="started",
        message=f"Pipeline started for session {session_id}. Connect to /ws/{session_id} for PULSE events.",
    )


@router.get("/status/{session_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(session_id: str) -> PipelineStatusResponse:
    """Query the current status of a pipeline run.

    Args:
        session_id: The session to query.

    Returns:
        PipelineStatusResponse with current status and agent info.

    Raises:
        HTTPException: If the session_id is not found.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    return PipelineStatusResponse(
        session_id=session_id,
        status=session["status"],
        current_agent=session.get("current_agent"),
        pdf_url=session.get("pdf_url"),
    )


@router.post("/stop/{session_id}")
async def stop_pipeline(session_id: str) -> dict:
    """Request the pipeline to stop gracefully.

    Sets the stop flag that each agent checks between major steps.
    The pipeline does not abort immediately — agents complete their
    current atomic operation before checking the flag.

    Args:
        session_id: The session to stop.

    Returns:
        Confirmation dict with the session_id and new status.

    Raises:
        HTTPException: If the session_id is not found.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    session["status"] = "stopping"
    logger.info("Stop requested — session=%s", session_id)

    return {"session_id": session_id, "status": "stopping"}
