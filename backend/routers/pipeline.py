"""Pipeline API routes — start, stop, and status endpoints."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.session_manager import session_manager
from backend.pulse import PulseEmitter
from backend.ws_manager import get_manager
from backend.orchestrator import OctantOrchestrator, PipelineRequest

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = OctantOrchestrator()


class PipelineStartPayload(BaseModel):
    session_id: str
    thesis: str
    exchanges: List[str]
    time_range: List[str]
    sector: Optional[str] = None


async def _run_pipeline_async(request: PipelineRequest, pulse: PulseEmitter):
    """Execute the pipeline on the current event loop (same loop as WebSockets)."""
    try:
        await orchestrator.run_pipeline(request, pulse)
    except Exception as e:
        logger.error("Pipeline failed for %s: %s", request.session_id, e)


@router.post("/start")
async def start_pipeline(payload: PipelineStartPayload):
    """Validate parameters and launch the pipeline as an async task."""
    session_id = payload.session_id
    if not payload.thesis or not payload.time_range or len(payload.time_range) != 2:
        raise HTTPException(status_code=400, detail="Invalid time range or missing thesis.")

    await session_manager.create(session_id)

    pulse = PulseEmitter(session_id=session_id, manager=get_manager())

    request = PipelineRequest(
        session_id=session_id,
        thesis=payload.thesis,
        exchanges=payload.exchanges,
        time_range=tuple(payload.time_range),
        sector=payload.sector,
    )

    asyncio.create_task(_run_pipeline_async(request, pulse))

    return {"message": "Pipeline initialized.", "session_id": session_id}


@router.post("/stop/{session_id}")
async def stop_pipeline(session_id: str):
    """Set the stop flag on a running pipeline."""
    state = await session_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    state.stop_flag.set()
    logger.info("Stop signal dispatched for session %s", session_id)

    return {"message": f"Stop signal dispatched for session {session_id}"}
