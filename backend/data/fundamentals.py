"""
Octant AI — Data Fetcher: Fundamentals

Provides the OpenBBFetcher class for retrieving foundational financial
ratios (PE, PB, Market Cap) for equities using the OpenBB SDK.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)


class OpenBBFetcher:
    """Retrieves fundamental equity metrics using OpenBB SDK.

    Falls back gracefully if the API rate limits or the SDK is unconfigured,
    ensuring pipeline continuity during the Universe Construction phase.
    """

    def __init__(self) -> None:
        """Initialise OpenBB environment variables if defined."""
        # Because OpenBB v4 is heavy to import, we import locally or lazily.
        # It also expects PAT/API keys via system environment.
        pass

    async def get_fundamentals(self, tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
        """Fetch core financial ratios for a list of tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            A dictionary mapping each ticker to a dictionary of metrics, e.g.:
            {"AAPL": {"PE": 28.5, "PB": 40.1, "MarketCap": 2.5e12}}
        """
        logger.info("Fetching fundamentals for %d tickers via OpenBB", len(tickers))
        results = {}

        try:
            # We run the heavy OpenBB SDK calls in a separate thread.
            metrics = await asyncio.to_thread(self._sync_fetch_openbb, tickers)
            results = metrics
        except Exception as exc:
            logger.warning("OpenBB fundamental fetch failed: %s", str(exc))
            # Fallback / construct empty records if the SDK fails so the
            # UniverseBuilder can still proceed using other criteria.
            for t in tickers:
                results[t] = {"PE": None, "PB": None, "MarketCap": None}

        return results

    def _sync_fetch_openbb(self, tickers: List[str]) -> dict:
        """Synchronous worker that calls the OpenBB SDK.

        Args:
            tickers: List of symbol strings.

        Returns:
            Dictionary mapping ticker to its metrics.
        """
        try:
            from openbb import obb
        except ImportError:
            logger.warning("openbb SDK not installed. Returning null fundamentals.")
            raise

        settings = get_settings()
        if settings.OPENBB_PAT:
            # PATs dictate OpenBB Hub configuration
            import os
            os.environ["OPENBB_PAT"] = settings.OPENBB_PAT

        metrics_map = {}
        
        # In openbb v4, fetching multiple tickers effectively generally requires
        # calling `obb.equity.fundamental.metrics(symbol="AAPL,MSFT", provider="yfinance")`
        symbol_str = ",".join(tickers)

        try:
            resp = obb.equity.fundamental.metrics(symbol=symbol_str, provider="yfinance")
            # resp.results is a list of Pydantic models (one per ticker/period)
            if resp and resp.results:
                for record in resp.results:
                    # record may have symbol, pe_ratio, pb_ratio, market_cap depending on provider
                    sym = getattr(record, "symbol", None)
                    if sym:
                        metrics_map[sym] = {
                            "PE": getattr(record, "pe_ratio", None),
                            "PB": getattr(record, "pb_ratio", None),
                            "MarketCap": getattr(record, "market_cap", None),
                        }
        except Exception as exc:
            logger.error("OpenBB call error: %s", str(exc))
            raise

        # Ensure all requested tickers have entries, even if missing in response
        for t in tickers:
            if t not in metrics_map:
                metrics_map[t] = {"PE": None, "PB": None, "MarketCap": None}

        return metrics_map
