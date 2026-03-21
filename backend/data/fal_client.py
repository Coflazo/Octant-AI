"""
Octant AI — Data Layer: fal.ai client

Async wrapper for the fal.ai image generation API. Used by Agent 5
to generate custom chart layouts and design components for the PDF report
using the fal-ai/flux-pro model.
"""

import asyncio
import logging
import os

from backend.config import get_settings

logger = logging.getLogger(__name__)


class FalAIClient:
    """Interfaces with fal.ai to generate high-fidelity technical images.
    """

    def __init__(self) -> None:
        """Initialise Fal AI credentials."""
        settings = get_settings()
        self.api_key = settings.FAL_KEY
        if self.api_key:
            os.environ["FAL_KEY"] = self.api_key
        else:
            logger.warning("FAL_KEY is not configured. Image generation will return mock URLs.")

    async def generate_chart_image(self, prompt: str) -> str:
        """Call fal-ai/flux-pro to generate a chart or component.

        Args:
            prompt: Text prompt describing the desired image.

        Returns:
            The URL of the generated image hosted by fal.ai.
        """
        if not self.api_key:
            return "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80"

        logger.info("Requesting fal.ai image generation (flux-pro) for prompt: %s...", prompt[:50])
        try:
            import fal_client

            # fal_client.subscribe is synchronous by default.
            # We use an asyncio thread to wrap the blocking call natively.
            result = await asyncio.to_thread(
                fal_client.subscribe,
                "fal-ai/flux-pro",
                arguments={
                    "prompt": prompt,
                    "image_size": "landscape_4_3",
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
                with_logs=False,
            )

            # Extract the URL from the response payload
            images = result.get("images", [])
            if not images or not isinstance(images, list):
                logger.error("fal.ai response did not contain an images array.")
                return ""

            image_url = images[0].get("url", "")
            logger.info("Generated image successfully: %s", image_url)
            return image_url

        except ImportError:
            logger.error("fal-client library is not installed.")
            return "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80"
        except Exception as exc:
            logger.error("Failed to generate image via fal.ai: %s", str(exc), exc_info=True)
            # Returning a fallback URL so the PDF report never crashes completely
            return "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80"
