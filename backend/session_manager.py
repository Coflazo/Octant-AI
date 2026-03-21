"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from backend.agents.hypothesis_engine import HypothesisObject

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    status: str  # "idle", "running", "complete", "error", "stopped"
    start_time: datetime = field(default_factory=datetime.utcnow)
    hypotheses: List[HypothesisObject] = field(default_factory=list)
    results_manifest: Dict = field(default_factory=dict)
    pdf_path: Optional[str] = None
    stop_flag: asyncio.Event = field(default_factory=asyncio.Event)


class SessionManager:
    """singleton memory pool managing all active quant jobs lol"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._sessions: Dict[str, SessionState] = {}

    async def create(self, session_id: str) -> None:
        """initialises a tracking struct for a new pipeline iteration lol"""
        async with self._lock:
            if session_id in self._sessions:
                logger.warning("Session %s already exists, overwriting.", session_id)
            self._sessions[session_id] = SessionState(status="running")
            logger.info("Session %s created.", session_id)

    async def get(self, session_id: str) -> Optional[SessionState]:
        """retrieves current session state struct lol"""
        async with self._lock:
            return self._sessions.get(session_id)

    async def update(self, session_id: str, **kwargs) -> None:
        """dynamically patches fields on the session tracker lol"""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state:
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

    async def delete(self, session_id: str) -> None:
        """hard removes the session from memory lol"""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    async def list_active(self) -> List[str]:
        """returns array of active running session ids lol"""
        async with self._lock:
            return [sid for sid, state in self._sessions.items() if state.status == "running"]


# Global Singleton
session_manager = SessionManager()
