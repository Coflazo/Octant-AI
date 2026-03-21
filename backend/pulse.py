"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

import orjson
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections keyed by session_id.

    Supports connect, disconnect, per-session send, and broadcast.
    Also routes incoming binary audio chunks to registered handlers
    for Reson8 voice transcription.

    Attributes:
        active_connections: Mapping of session_id to WebSocket instance.
        audio_handlers: Mapping of session_id to async audio chunk callback.
    """

    def __init__(self) -> None:
        """initialise empty connection and handler registries lol"""
        self.active_connections: Dict[str, WebSocket] = {}
        self.audio_handlers: Dict[
            str, Callable[[bytes], Coroutine[Any, Any, None]]
        ] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept an incoming WebSocket and register it for the session.

        If a connection already exists for this session_id, the old one is
        closed first to prevent leaked sockets.

        Args:
            websocket: The incoming WebSocket connection to accept.
            session_id: Unique identifier for this pipeline session.
        """
                                # Close any stale connection on the same session
        if session_id in self.active_connections:
            logger.warning(
                "Replacing existing WebSocket for session_id=%s", session_id
            )
            try:
                await self.active_connections[session_id].close()
            except Exception:
                pass

        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(
            "WebSocket registered — session_id=%s, total_active=%d",
            session_id,
            len(self.active_connections),
        )

    async def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection and clean up resources.

        Silently ignores unknown session_ids for idempotency.

        Args:
            session_id: The session whose connection should be removed.
        """
        ws = self.active_connections.pop(session_id, None)
        self.audio_handlers.pop(session_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
            logger.info(
                "WebSocket disconnected — session_id=%s, remaining=%d",
                session_id,
                len(self.active_connections),
            )

    async def send_pulse(self, session_id: str, pulse_event: dict) -> None:
        """Send a PULSE JSON event to a specific session.

        Uses orjson for fast serialisation. If the send fails due to a
        broken connection, the session is automatically cleaned up.

        Args:
            session_id: Target session to send the event to.
            pulse_event: The PULSE event dict to serialise and send.
        """
        ws = self.active_connections.get(session_id)
        if not ws:
            logger.warning(
                "Cannot send PULSE — no active WebSocket for session_id=%s",
                session_id,
            )
            return

        try:
            raw = orjson.dumps(pulse_event).decode("utf-8")
            await ws.send_text(raw)
            logger.debug(
                "PULSE sent — session=%s, agent=%s, type=%s",
                session_id,
                pulse_event.get("agent", "?"),
                pulse_event.get("payload_type", "?"),
            )
        except Exception as exc:
            logger.error(
                "PULSE send failed — session=%s, error=%s", session_id, str(exc)
            )
            await self.disconnect(session_id)

    async def broadcast_pulse(self, pulse_event: dict) -> None:
        """Broadcast a PULSE event to all active sessions.

        Useful for system-wide announcements. Failed sends trigger
        per-session disconnect cleanup.

        Args:
            pulse_event: The PULSE event dict to broadcast.
        """
        for session_id in list(self.active_connections.keys()):
            await self.send_pulse(session_id, pulse_event)

    def register_audio_handler(
        self,
        session_id: str,
        handler: Callable[[bytes], Coroutine[Any, Any, None]],
    ) -> None:
        """Register an async callback for incoming audio chunks.

        The voice transcription system uses this to receive mic audio
        streamed from the browser through the WebSocket.

        Args:
            session_id: Session to register the handler for.
            handler: Async function that processes a bytes audio chunk.
        """
        self.audio_handlers[session_id] = handler
        logger.info("Audio handler registered — session_id=%s", session_id)

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        """Route an audio chunk to the registered handler for a session.

        If no handler is registered, the chunk is silently dropped.

        Args:
            session_id: Session that sent the audio chunk.
            chunk: Raw audio bytes from the browser microphone.
        """
        handler = self.audio_handlers.get(session_id)
        if handler:
            await handler(chunk)
        else:
            logger.debug(
                "No audio handler for session_id=%s — dropping %d bytes",
                session_id,
                len(chunk),
            )


class PulseEmitter:
    """Structured PULSE event emitter for a single pipeline session.

    Each of the five agents creates a PulseEmitter instance to send
    typed events at key milestones. Every emit method constructs a
    valid PULSE payload and delegates to the ConnectionManager.

    Attributes:
        session_id: The pipeline session this emitter targets.
        manager: The global ConnectionManager for WebSocket delivery.
    """

    def __init__(self, session_id: str, manager: ConnectionManager) -> None:
        """Create a PulseEmitter bound to a specific session.

        Args:
            session_id: Unique identifier for this pipeline session.
            manager: The ConnectionManager holding the WebSocket.
        """
        self.session_id = session_id
        self.manager = manager

    def _timestamp(self) -> str:
        """Generate an ISO 8601 UTC timestamp string.

        Returns:
            Current UTC time as an ISO format string.
        """
        return datetime.now(timezone.utc).isoformat()

    def _build_event(
        self,
        agent: str,
        status: str,
        payload_type: str,
        payload: dict,
        message_title: str = "",
        message_subtitle: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        percent_complete: int = 0,
        estimated_remaining_sec: int = 0,
    ) -> dict:
        """Construct a complete PULSE event envelope.

        Args:
            agent: Agent identifier (e.g., "hypothesis_engine").
            status: Lifecycle status ("pending", "active", "complete", "error").
            payload_type: Discriminator for the payload shape.
            payload: The event-specific data dictionary.
            message_title: Human-readable title for the frontend status line.
            message_subtitle: Human-readable subtitle / detail line.
            current_step: Current step index within the agent's work.
            total_steps: Total number of steps the agent will perform.
            percent_complete: Integer percentage 0–100.
            estimated_remaining_sec: Estimated seconds until agent completes.

        Returns:
            A complete PULSE event dict ready for JSON serialisation.
        """
        return {
            "type": "PULSE",
            "agent": agent,
            "status": status,
            "progress": {
                "current_step": current_step,
                "total_steps": total_steps,
                "percent_complete": percent_complete,
                "estimated_remaining_sec": estimated_remaining_sec,
            },
            "payload_type": payload_type,
            "payload": payload,
            "message": {
                "title": message_title,
                "subtitle": message_subtitle,
            },
            "timestamp": self._timestamp(),
        }

    async def emit_status(
        self,
        agent: str,
        status: str,
        step: int = 0,
        total: int = 0,
        message_title: str = "",
        message_subtitle: str = "",
        percent: int = 0,
        estimated_remaining_sec: int = 0,
    ) -> None:
        """Emit a status update PULSE event.

        Used at agent lifecycle transitions: "pending" → "active" → "complete"
        or → "error". Also used for intermediate progress updates.

        Args:
            agent: Agent identifier string.
            status: One of "pending", "active", "complete", "error".
            step: Current step number within this agent's work.
            total: Total steps this agent will perform.
            message_title: Display title for the frontend status card.
            message_subtitle: Display subtitle / detail text.
            percent: Completion percentage 0–100.
            estimated_remaining_sec: Estimated seconds remaining.
        """
        event = self._build_event(
            agent=agent,
            status=status,
            payload_type="status",
            payload={"status": status},
            message_title=message_title,
            message_subtitle=message_subtitle,
            current_step=step,
            total_steps=total,
            percent_complete=percent,
            estimated_remaining_sec=estimated_remaining_sec,
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_hypothesis_card(
        self, hypothesis_obj: dict
    ) -> None:
        """Emit a hypothesis card PULSE event.

        Sent once per hypothesis after Agent 1 completes decomposition.

        Args:
            hypothesis_obj: Dict with keys: id, statement, null_hypothesis,
                math_badge, direction, key_variables, relevant_math_models,
                geographic_scope, asset_class.
        """
        event = self._build_event(
            agent="hypothesis_engine",
            status="active",
            payload_type="hypothesis_card",
            payload=hypothesis_obj,
            message_title="Hypothesis generated",
            message_subtitle=hypothesis_obj.get("statement", "")[:80],
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_citation_card(self, paper_obj: dict) -> None:
        """Emit a citation card PULSE event.

        Sent for each paper found and analysed by Agent 2.

        Args:
            paper_obj: Dict with keys: title, authors, year, journal,
                relevance, supports, abstract_summary, url, doi,
                key_finding, signal_tested, market_studied, time_period,
                performance_metric, statistical_methodology, effect_size,
                novelty_score.
        """
        event = self._build_event(
            agent="literature",
            status="active",
            payload_type="citation_card",
            payload=paper_obj,
            message_title="Paper analysed",
            message_subtitle=paper_obj.get("title", "")[:80],
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_ticker_card(self, ticker_obj: dict) -> None:
        """Emit a ticker card PULSE event.

        Sent for each ticker that passes the liquidity screen in Agent 3.

        Args:
            ticker_obj: Dict with keys: symbol, name, exchange, sector,
                sparkline_url, mktcap, short_interest, days_to_cover,
                pb_ratio, avg_volume, sentiment_z_score.
        """
        event = self._build_event(
            agent="universe",
            status="active",
            payload_type="ticker_card",
            payload=ticker_obj,
            message_title="Ticker qualified",
            message_subtitle=f"{ticker_obj.get('symbol', '')} — {ticker_obj.get('name', '')}",
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_metric_result(
        self, hypothesis_id: str, metrics_obj: dict
    ) -> None:
        """Emit a metric result PULSE event.

        Sent after Agent 4 completes backtesting for a single hypothesis.

        Args:
            hypothesis_id: ID of the hypothesis these metrics belong to.
            metrics_obj: Dict containing all performance metrics.
        """
        payload = {"hypothesis_id": hypothesis_id, **metrics_obj}
        event = self._build_event(
            agent="backtest",
            status="active",
            payload_type="metric_result",
            payload=payload,
            message_title="Backtest complete",
            message_subtitle=f"Hypothesis {hypothesis_id} — Sharpe: {metrics_obj.get('sharpe_ratio', 'N/A')}",
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_report_section(
        self, section_name: str, excerpt: str, is_complete: bool
    ) -> None:
        """Emit a report section PULSE event.

        Sent as Agent 5 writes each section of the LaTeX report. Called
        multiple times per section when Gemini streaming is active
        (is_complete=False for partial, True for final).

        Args:
            section_name: Name of the report section being written.
            excerpt: Text excerpt (partial or complete) of the section.
            is_complete: Whether this is the final emission for this section.
        """
        event = self._build_event(
            agent="architect",
            status="active",
            payload_type="report_section",
            payload={
                "section_name": section_name,
                "excerpt": excerpt,
                "is_complete": is_complete,
            },
            message_title=f"Writing: {section_name}",
            message_subtitle="Complete" if is_complete else "Streaming...",
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_transcription(
        self, text: str, is_final: bool
    ) -> None:
        """Emit a transcription PULSE event from Reson8 voice input.

        Sent as partial words arrive from the speech-to-text engine.
        When is_final=True, the 2-second silence was detected and
        the transcription is locked.

        Args:
            text: The partial or complete transcription text.
            is_final: Whether this is the final transcription.
        """
        payload_type = "transcription_complete" if is_final else "transcription"
        event = self._build_event(
            agent="hypothesis_engine",
            status="active",
            payload_type=payload_type,
            payload={"text": text, "is_final": is_final},
            message_title="Voice input" if not is_final else "Transcription complete",
            message_subtitle=text[:80],
        )
        await self.manager.send_pulse(self.session_id, event)

    async def emit_error(
        self, agent: str, error_message: str, traceback_str: str = "",
        recovery_action: Optional[str] = None,
    ) -> None:
        """Emit an error PULSE event.

        Sent when an agent encounters a pipeline-blocking or non-critical
        failure. The recovery_action string guides the user on next steps.

        Args:
            agent: The agent that encountered the error.
            error_message: Human-readable error description.
            traceback_str: Full Python traceback string for debugging.
            recovery_action: Optional suggestion for how to recover.
        """
        event = self._build_event(
            agent=agent,
            status="error",
            payload_type="error",
            payload={
                "agent": agent,
                "error_message": error_message,
                "traceback": traceback_str,
                "recovery_action": recovery_action,
            },
            message_title=f"Error in {agent}",
            message_subtitle=error_message[:80],
        )
        await self.manager.send_pulse(self.session_id, event)
