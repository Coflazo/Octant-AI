"""Global WebSocket ConnectionManager singleton.

Extracted to its own module to break circular imports between
main.py (which registers routers) and pipeline.py / voice.py
(which need the manager to create PulseEmitter instances).
"""

from backend.pulse import ConnectionManager

manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    """Return the application-wide ConnectionManager instance."""
    return manager
