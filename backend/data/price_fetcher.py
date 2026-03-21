"""
Octant AI — Data Fetcher: Market Prices

Provides the YFinanceFetcher class for pulling adjusted close prices
from Yahoo Finance. Handles missing data via forward-fill and back-fill
to ensure continuous time series for the quantitative models.
"""

import asyncio
import logging
from typing import List

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class YFinanceFetcher:
    """Historical price fetcher using the yfinance library.
    
    Pulls daily adjusted close prices, standardises the resulting DataFrame,
    and handles missing/NaN market data so that downstream matrix operations
    and vectorised backtesting engines do not fail.
    """

    async def fetch_prices(
        self, tickers: List[str], start_date: str, end_date: str, frequency: str = "1d"
    ) -> pd.DataFrame:
        """Fetch cleaned adjusted close prices for a list of tickers.

        Downloads the market data window, extracts the 'Adj Close' column
        (falling back to 'Close' if unavailable), and applies standard data
        imputation (ffill then bfill).

        Args:
            tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).
            frequency: Data frequency string (e.g., "1d", "1wk").

        Returns:
            A pandas DataFrame aligned by trading day (index), where each
            column represents a ticker's adjusted close price over time.
        """
        if not tickers:
            return pd.DataFrame()

        logger.info(
            "Fetching %s prices for %d tickers from %s to %s",
            frequency,
            len(tickers),
            start_date,
            end_date,
        )

        try:
            # yfinance network calls are synchronous, so we run them in a thread
            # to avoid blocking the main FastAPI event loop. threads=True uses
            # concurrent extraction inside yf itself.
            df = await asyncio.to_thread(
                yf.download,
                tickers=tickers,
                start=start_date,
                end=end_date,
                interval=frequency,
                group_by="column",
                auto_adjust=False,
                threads=True,
                progress=False,
            )

            if df.empty:
                logger.warning("yfinance returned an empty DataFrame.")
                return pd.DataFrame()

            # Multi-ticker downloads return a MultiIndex (Price->Ticker),
            # Single-ticker returns simple columns.
            is_multi = isinstance(df.columns, pd.MultiIndex)
            price_col = None

            if is_multi:
                if "Adj Close" in df.columns.levels[0]:
                    price_col = "Adj Close"
                elif "Close" in df.columns.levels[0]:
                    price_col = "Close"
            else:
                if "Adj Close" in df.columns:
                    price_col = "Adj Close"
                elif "Close" in df.columns:
                    price_col = "Close"

            if not price_col:
                logger.error("No valid price columns found in yfinance response.")
                return pd.DataFrame()
            
            if price_col == "Close":
                logger.warning("Adj Close not found, falling back to unadjusted Close.")

            # Extract just the targeted price data
            prices = df[price_col]

            # If only 1 ticker was requested, 'prices' is a pd.Series.
            # We promote it to a DataFrame to maintain the contract.
            if isinstance(prices, pd.Series):
                prices = prices.to_frame(name=tickers[0])

            # ── Data Imputation ───────────────────────────────────────
            # Forward-fill carries the last valid observation forward (e.g., holidays).
            # Backward-fill catches leading NaNs at the start of the required period.
            cleaned_prices = prices.ffill().bfill()

            logger.info("Fetched and cleaned prices for %d assets.", cleaned_prices.shape[1])
            return cleaned_prices

        except Exception as exc:
            logger.error(
                "Failed to fetch prices from yfinance: %s", str(exc), exc_info=True
            )
            # Re-raise so the orchestrator can catch and emit an error PULSE
            raise
