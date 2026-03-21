"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import json
import logging
from typing import Dict, List

from backend.config import get_settings

logger = logging.getLogger(__name__)


class WSBTrendsClient:
    """interfaces with the external wsbtrends go binary lol"""

    def __init__(self) -> None:
        settings = get_settings()
        self.binary_path = getattr(settings, "WSBT_BINARY_PATH", "./bin/wsbtrends")

    async def get_mention_counts(self, window_days: int = 7) -> Dict[str, int]:
        """Fetch raw ticker mention counts for a specific trailing window.

        Args:
            window_days: Lookback period in days.

        Returns:
            A dictionary mapping ticker symbol to absolute mention count.
        """
        import os
        if not os.path.exists(self.binary_path):
            logger.warning("WSBTrends binary not found at %s. Returning empty mentions.", self.binary_path)
            return {}

        logger.info("Executing WSBTrends Go subprocess (window=%d)", window_days)
        try:
            cmd = [self.binary_path, "--window", str(window_days), "--format", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("WSBTrends exited with code %d. Stderr: %s", process.returncode, stderr.decode())
                return {}

            output_str = stdout.decode().strip()
            if not output_str:
                return {}

            data = json.loads(output_str)
                                                # Ensure it fits dict[str, int]
            return {str(k): int(v) for k, v in data.items()}

        except Exception as exc:
            logger.error("Failed to execute WSBTrends subprocess: %s", exc)
            return {}

    async def get_multi_window(self, windows: List[int]) -> Dict[str, Dict[int, int]]:
        """Return counts for multiple time windows simultaneously.

        Args:
            windows: A list of integer window lengths (e.g., [1, 7, 30]).

        Returns:
            Dict mapping ticker -> {window: count}.
        """
        logger.info("Fetching multi-window mention counts for windows: %s", windows)
        tasks = [self.get_mention_counts(w) for w in windows]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined = {}
        for w, res in zip(windows, results):
            if isinstance(res, dict):
                for ticker, count in res.items():
                    if ticker not in combined:
                        combined[ticker] = {}
                    combined[ticker][w] = count
            else:
                logger.error("Error fetching window %d: %s", w, res)

        return combined
