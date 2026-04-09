"""Matplotlib sparkline generator — replaces fal.ai hosted chart images."""

import asyncio
import logging
import os
import uuid
from typing import List

logger = logging.getLogger(__name__)


class SparklineGenerator:
    """Generate minimal sparkline PNGs from price data using matplotlib."""

    def __init__(self, output_dir: str = "/tmp/octant_reports/sparklines"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_sparkline(
        self,
        symbol: str,
        price_series: List[float],
        width: int = 120,
        height: int = 40,
    ) -> str:
        """Generate a sparkline PNG for a ticker.

        Args:
            symbol: Ticker symbol (e.g., "AAPL").
            price_series: List of recent price floats.
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            Relative URL path to the generated PNG, or empty string on failure.
        """
        if not price_series or len(price_series) < 2:
            return ""

        try:
            path = await asyncio.to_thread(
                self._render, symbol, price_series, width, height
            )
            return path
        except Exception as exc:
            logger.error("Sparkline generation failed for %s: %s", symbol, exc)
            return ""

    def _render(
        self,
        symbol: str,
        prices: List[float],
        width: int,
        height: int,
    ) -> str:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        dpi = 100
        fig_w = width / dpi
        fig_h = height / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
        fig.patch.set_facecolor("#0A0B0D")
        ax.set_facecolor("#0A0B0D")

        color = "#00C07A" if prices[-1] >= prices[0] else "#EF4444"
        ax.plot(prices, color=color, linewidth=1.5, alpha=0.9)
        ax.fill_between(
            range(len(prices)), prices, min(prices),
            color=color, alpha=0.15,
        )

        ax.axis("off")
        ax.margins(0)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        filename = f"{symbol}_{uuid.uuid4().hex[:6]}.png"
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=dpi, bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        return f"/static/sparklines/{filename}"
