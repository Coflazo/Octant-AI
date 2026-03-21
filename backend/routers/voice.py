"""
Octant AI — Voice API Router.

Provides the WebSocket endpoint for streaming speech-to-text.
Clients connect to /api/voice/transcribe/{session_id}, stream binary
audio chunks, and receive PULSE events with payload_type="transcription".
Once a 2-second continuous silence is detected, the transcription is locked.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.pulse import PulseEmitter
from backend.routers.pipeline import _get_manager
from backend.voice.reson8_client import Reson8Client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/transcribe/{session_id}")
async def voice_transcription_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for microphone audio streaming and transcription.

    The frontend (VoiceInput component) streams binary 250ms chunks.
    This endpoint pipes them into the Reson8Client, routing the returned text
    back to the client as PULSE "transcription" events. It detects 2s of
    silence to automatically finalise the transaction.

    Args:
        websocket: The connected WebSocket.
        session_id: Pipeline session identifier.
    """
    await websocket.accept()
    logger.info("Voice transcription socket opened — session=%s", session_id)

    manager = _get_manager()
    pulse = PulseEmitter(session_id, manager)
    client = Reson8Client()

    # Communication queues for the duplex stream
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    finalise_event = asyncio.Event()

    # Track silence duration via chunk counts (e.g., eight 250ms chunks = 2.0s)
    consecutive_silent_chunks = 0
    SILENCE_CHUNK_LIMIT = 8

    async def _audio_producer() -> None:
        """Read from websocket and enqueue for transmission."""
        nonlocal consecutive_silent_chunks
        try:
            while not finalise_event.is_set():
                message = await websocket.receive()
                if "bytes" in message:
                    chunk = message["bytes"]
                    await audio_queue.put(chunk)

                    # Check for end-of-speech
                    if client.detect_silence(chunk):
                        consecutive_silent_chunks += 1
                        if consecutive_silent_chunks >= SILENCE_CHUNK_LIMIT:
                            logger.info("2-second silence detected, finalising dictation — session=%s", session_id)
                            finalise_event.set()
                            # Close the upstream generator queue
                            await audio_queue.put(b"")
                    else:
                        consecutive_silent_chunks = 0

                elif "text" in message:
                    # Client can explicitly send "stop" to end dictation
                    if message["text"] == "stop":
                        finalise_event.set()
                        await audio_queue.put(b"")

        except WebSocketDisconnect:
            finalise_event.set()
            await audio_queue.put(b"")
        except Exception as exc:
            logger.error("Audio receive error: %s", exc)
            finalise_event.set()
            await audio_queue.put(b"")

    async def _audio_iterator():
        """Yield chunks from the queue for the streaming HTTP request."""
        while True:
            chunk = await audio_queue.get()
            if not chunk:
                break
            yield chunk

    async def _transcription_consumer() -> None:
        """Call Reson8 stream and push generated text back as PULSE events."""
        try:
            cumulative_text = []

            async for text_fragment in client.transcribe_stream(_audio_iterator()):
                if text_fragment:
                    cumulative_text.append(text_fragment)
                    # Emit partial words back on the main PULSE socket
                    await pulse.emit_transcription(
                        text=" ".join(cumulative_text),
                        is_final=False
                    )

            # When stream ends natively or via silence cutoff, emit final output
            final_transcript = " ".join(cumulative_text).strip()
            if final_transcript:
                await pulse.emit_transcription(
                    text=final_transcript,
                    is_final=True
                )

        except Exception as exc:
            logger.error("Transcription stream error — session=%s: %s", session_id, exc)
            await pulse.emit_error(
                agent="hypothesis_engine",
                error_message=f"Voice dictation failed: {str(exc)}",
                traceback_str="",
                recovery_action="Try typing the thesis instead."
            )

    try:
        # Run producer and consumer concurrently
        await asyncio.gather(
            _audio_producer(),
            _transcription_consumer()
        )
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("Voice transcription socket closed — session=%s", session_id)
