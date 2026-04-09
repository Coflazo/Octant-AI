"""Octant AI — Session state management for active pipeline runs."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.agents.hypothesis_engine import HypothesisObject

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    status: str  # "idle", "running", "complete", "error", "stopped"
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hypotheses: List[HypothesisObject] = field(default_factory=list)
    results_manifest: Dict = field(default_factory=dict)
    pdf_path: Optional[str] = None
    stop_flag: asyncio.Event = field(default_factory=asyncio.Event)


class SessionManager:
    """Singleton memory pool managing all active quant jobs."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._sessions: Dict[str, SessionState] = {}

    async def create(self, session_id: str) -> None:
        """Initialise a tracking struct for a new pipeline iteration."""
        async with self._lock:
            if session_id in self._sessions:
                logger.warning("Session %s already exists, overwriting.", session_id)
            self._sessions[session_id] = SessionState(status="running")
            logger.info("Session %s created.", session_id)

    async def get(self, session_id: str) -> Optional[SessionState]:
        """Retrieve current session state."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def update(self, session_id: str, **kwargs) -> None:
        """Dynamically patch fields on the session tracker."""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state:
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

    async def delete(self, session_id: str) -> None:
        """Remove the session from memory."""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    async def list_active(self) -> List[str]:
        """Return list of active running session IDs."""
        async with self._lock:
            return [sid for sid, state in self._sessions.items() if state.status == "running"]




# Global Singleton
session_manager = SessionManager()
