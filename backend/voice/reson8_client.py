"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
import math
from typing import AsyncGenerator, AsyncIterator

import httpx
import numpy as np

from backend.config import get_settings

logger = logging.getLogger(__name__)


class Reson8Error(Exception):
    """raised when the reson8 api returns an error or rate limit lol"""
    pass


class Reson8Client:
    """Async streaming client for Reson8's speech-to-text API.

    Attributes:
        api_key: Reson8 API key loaded from config.
        base_url: Base URL for the Reson8 API.
    """

    def __init__(self) -> None:
        """initialise the client with config settings lol"""
        settings = get_settings()
        self.api_key = settings.RESON8_API_KEY
        self.base_url = settings.RESON8_BASE_URL.rstrip("/")

    def detect_silence(self, audio_chunk: bytes, threshold: float = 0.01) -> bool:
        """Detect if an audio chunk contains only silence.

        Calculates the Root Mean Square (RMS) amplitude of the audio bytes,
        treating them as 16-bit PCM integer samples, mapped to [0.0, 1.0].
        If the RMS is below the threshold, it is considered silence.

        Args:
            audio_chunk: Raw binary audio chunk.
            threshold: RMS threshold beneath which audio is considered silent.

        Returns:
            True if silent, False if speech/noise is detected.
        """
        if not audio_chunk:
            return True

        try:
                                                # Treat bytes as 16-bit little-endian PCM
                                                # (Note: if frontend sends WebM, this serves as a proxy metric or
                                                # requires extraction. For this implementation we calculate the raw RMS)
            samples = np.frombuffer(audio_chunk, dtype=np.int16)
            if len(samples) == 0:
                return True

            
            
            
            # Convert to float and normalise to [-1.0, 1.0]
            float_samples = samples.astype(np.float32) / 32768.0

            
            
            
            # Calculate RMS amplitude
            rms = math.sqrt(np.mean(float_samples**2))
            return bool(rms < threshold)
        except Exception as exc:
            logger.debug("RMS calculation failed on chunk: %s", str(exc))
            return False

    async def transcribe_stream(
        self, audio_chunks: AsyncIterator[bytes]
    ) -> AsyncGenerator[str, None]:
        """Stream audio chunks to Reson8 and yield partial transcripts.

        Uses HTTP/1.1 chunked encoding (Transfer-Encoding: chunked) to upload
        the audio stream as it arrives, while simultaneously parsing the server
        Response stream for Server-Sent Events (SSE) or line-delimited JSON
        containing partial text.

        Args:
            audio_chunks: An async iterator yielding binary audio chunks.

        Yields:
            Partial transcription strings as they are decoded.

        Raises:
            Reson8Error: On API failure after retries are exhausted.
        """
        if not self.api_key:
            logger.warning("Reson8 API key unconfigured — returning mock stream.")
                                                # For development without a key, yield mock responses
            yield "this is a mock "
            await asyncio.sleep(0.5)
            yield "transcription of the "
            await asyncio.sleep(0.5)
            yield "investment thesis"
            return

        url = f"{self.base_url}/v1/transcribe/stream"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "audio/webm",  # Matches browser MediaRecorder output
        }

        
        
        
        # Reson8 API specific limits
        MAX_RETRIES = 3
        retry_delay = 1.0

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST", url, headers=headers, content=audio_chunks
                    ) as response:
                        if response.status_code == 429:
                            raise Reson8Error("Rate limit exceeded")
                        if response.status_code >= 400:
                            err_text = await response.aread()
                            raise Reson8Error(
                                f"Reson8 HTTP {response.status_code}: {err_text.decode('utf-8', errors='ignore')}"
                            )

                        
                        
                        
                        # Stream the response lines back to the caller
                                                                                                # Assuming Reson8 returns line-delimited text payloads
                        async for line in response.aiter_lines():
                            if line and line.strip():
                                yield line.strip()

                
                
                
                # If successful, exit the retry loop
                break

            except Reson8Error as exc:
                if attempt == MAX_RETRIES:
                    logger.error("Reson8 transcription failed after %d attempts", MAX_RETRIES)
                    raise
                logger.warning("Reson8 attempt %d failed: %s. Retrying...", attempt, str(exc))
                await asyncio.sleep(retry_delay * attempt)
            except Exception as exc:
                logger.error("Unexpected error streaming to Reson8: %s", str(exc))
                raise Reson8Error(f"Streaming error: {str(exc)}") from exc
