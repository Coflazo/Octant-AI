"""
Octant AI — Voice API Router.

Placeholder router for the Reson8 voice transcription endpoints.
The full implementation with streaming WebSocket audio handling
is built in Section 3. This stub ensures main.py can import it
without errors during Section 2 validation.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def voice_health() -> dict:
    """Health check for the voice transcription subsystem.

    Returns:
        Status dict indicating whether Reson8 is configured.
    """
    from backend.config import get_settings
    settings = get_settings()
    has_key = bool(settings.RESON8_API_KEY)

    return {
        "service": "voice",
        "reson8_configured": has_key,
        "status": "ready" if has_key else "unconfigured",
    }
