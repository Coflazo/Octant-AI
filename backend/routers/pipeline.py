"""
Octant AI — Pipeline Router

Maps standard HTTPS `POST /api/pipeline/start`, `POST /api/pipeline/stop/{session_id}`
REST abstractions down to the Background Orchestrator thread and 
interacts directly with the state dicts tracked by the `SessionManager`.
"""

import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from backend.session_manager import session_manager
from backend.pulse import PulseEmitter
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


def background_pipeline_runner(request: PipelineRequest, pulse: PulseEmitter):
    """Executes the master pipeline synchronously on the FastAPI background execution threads."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(orchestrator.run_pipeline(request, pulse))
    except Exception as e:
        logger.error("Background task pipeline loop explicitly failed for %s: %s", request.session_id, e)
    finally:
        loop.close()


@router.post("/start")
async def start_pipeline(payload: PipelineStartPayload, background_tasks: BackgroundTasks):
    """Validates parameters, generates state structs, and issues unblocking OS worker."""
    session_id = payload.session_id
    if not payload.thesis or not payload.time_range or len(payload.time_range) != 2:
        raise HTTPException(status_code=400, detail="Invalid target time series or missing thesis params.")
        
    await session_manager.create(session_id)
    
    pulse = PulseEmitter(session_id=session_id)
    
    request = PipelineRequest(
        session_id=session_id,
        thesis=payload.thesis,
        exchanges=payload.exchanges,
        time_range=tuple(payload.time_range),
        sector=payload.sector
    )
    
    # Hand off standard execution mapping back to the Async loop worker pool
    background_tasks.add_task(background_pipeline_runner, request, pulse)
    
    return {"message": "Pipeline initialized.", "session_id": session_id}


@router.post("/stop/{session_id}")
async def stop_pipeline(session_id: str):
    """Interferes with the execution thread by emitting the explicit Event loop boolean."""
    state = await session_manager.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline target not identifiable.")
    
    state.stop_flag.set()
    logger.info("Termination sequence flagged on pipeline root for %s", session_id)
    
    return {"message": f"Termination signal dispatched for session {session_id}"}


@router.get("/reports/{filename}")
async def fetch_pdf(filename: str):
    """Safely serves the resulting generative report to HTTP targets via streaming FileResponses."""
    import os
    target_path = os.path.join("/tmp/octant_reports", filename)
    
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Compiled artifact not existing in system memory.")
        
    return FileResponse(
        target_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
