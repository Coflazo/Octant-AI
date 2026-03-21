"""
Octant AI — Data Layer: fal.ai Sparklines

Async wrapper for the fal.ai image generation API. Used by Agent 3
to generate clean, dark-theme sparkline charts for ticker cards.
"""

import asyncio
import logging
import os
from typing import List

from backend.config import get_settings

logger = logging.getLogger(__name__)


class FalChartClient:
    """Interfaces with fal.ai to generate high-fidelity sparkline images."""

    def __init__(self) -> None:
        """Initialise Fal AI credentials."""
        settings = get_settings()
        self.api_key = settings.FAL_KEY
        if self.api_key:
            os.environ["FAL_KEY"] = self.api_key
        else:
            logger.warning("FAL_KEY is not configured. Sparklines will not render.")

    async def generate_sparkline(
        self, symbol: str, price_series: List[float], width: int = 120, height: int = 40
    ) -> str:
        """Generate a sparkline image for a ticker using fal.ai.

        Args:
            symbol: Ticker symbol (e.g., "AAPL").
            price_series: List of recent price floats.
            width: Required image width.
            height: Required image height.

        Returns:
            The URL of the generated image hosted by fal.ai, or empty string on failure.
        """
        if not self.api_key or not price_series:
            return ""

        direction = "up" if price_series[-1] >= price_series[0] else "down"
        color = "#00C07A" if direction == "up" else "#EF4444"
        
        prompt = (
            f"A sleek, ultra-minimalist dark theme financial sparkline chart for {symbol}. "
            f"The line is {color} and glowing slightly. No axes, no text, no background. "
            f"Background is solid #0A0B0D. Dimensions {width}x{height}."
        )

        logger.debug("Requesting fal.ai sparkline for %s", symbol)
        
        try:
            import fal_client

            # fal_client.subscribe is synchronous by default.
            result = await asyncio.to_thread(
                fal_client.subscribe,
                "fal-ai/flux-pro",
                arguments={
                    "prompt": prompt,
                    "image_size": "landscape_16_9", # Will be cropped by frontend
                    "num_inference_steps": 25,
                    "guidance_scale": 3.0,
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
                with_logs=False,
            )

            images = result.get("images", [])
            if not images or not isinstance(images, list):
                logger.error("fal.ai response missing images array for %s", symbol)
                return ""

            image_url = images[0].get("url", "")
            return image_url

        except Exception as exc:
            logger.error("Failed to generate sparkline for %s via fal.ai: %s", symbol, exc)
            # Sparkline is non-critical, return empty string per spec
            return ""
