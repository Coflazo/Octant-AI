"""
Octant AI — Data Fetcher: Market Prices

Provides the PriceFetcher class for universe construction, OHLCV data fetching,
liquidity screening, and log return computation using yfinance.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class PriceFetcher:
    """Historical price fetcher and screener using the yfinance library."""

    async def fetch_universe_tickers(
        self, exchanges: List[str], sector: Optional[str], max_tickers: int
    ) -> List[str]:
        """Fetch a list of candidate tickers for the given exchanges and sector.

        Args:
            exchanges: Target exchange codes.
            sector: Optional sector filter.
            max_tickers: Maximum number of candidate tickers to return.

        Returns:
            A list of ticker symbols.
        """
        logger.info(
            "Fetching universe tickers for exchanges=%s, sector=%s, max=%d",
            exchanges, sector, max_tickers
        )
        # Note: yfinance has no native multi-exchange stock screener. 
        # In production this would query a proper screener API.
        # We provide a hardcoded starter universe mimicking the top S&P/Nasdaq equivalents.
        base_universe = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "TSLA", "UNH", "JNJ", "XOM", "JPM", "V"]
        
        # Sector mock filtering if requested
        if sector and sector.lower() == "energy":
            base_universe = ["XOM", "CVX", "COP", "SLB", "EOG", "OXY"]
        elif sector and "tech" in sector.lower():
            base_universe = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"]
            
        return base_universe[:max_tickers]

    async def fetch_ohlcv(
        self, tickers: List[str], start_date: str, end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data with handling for splits and dividends.

        Downloads with auto_adjust=True. Handles missing data by forward-filling
        then dropping remaining leading NaNs.

        Args:
            tickers: List of symbol strings.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            Dict mapping ticker symbol to its OHLCV DataFrame.
        """
        logger.info("Fetching OHLCV for %d tickers from %s to %s", len(tickers), start_date, end_date)
        if not tickers:
            return {}

        def _fetch_sync():
            df = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )
            return df

        try:
            raw_data = await asyncio.to_thread(_fetch_sync)
        except Exception as exc:
            logger.error("yfinance download failed: %s", exc)
            return {}

        result_dict = {}
        if len(tickers) == 1:
            # Single ticker returns standard 2D Frame (Columns: Open, High, etc)
            ticker = tickers[0]
            clean_df = raw_data.ffill().dropna()
            result_dict[ticker] = clean_df
        else:
            # Multi-ticker returns MultiIndex columns (Ticker -> Open, High, etc)
            for ticker in tickers:
                if ticker in raw_data.columns.levels[0]:
                    ticker_df = raw_data[ticker].copy()
                    ticker_df = ticker_df.ffill().dropna()
                    result_dict[ticker] = ticker_df

        return result_dict

    def apply_liquidity_screen(
        self, price_data: Dict[str, pd.DataFrame], min_avg_volume: int = 500000, min_price: float = 1.0
    ) -> Dict[str, pd.DataFrame]:
        """Removes tickers failing minimum volume and price criteria.

        Args:
            price_data: Dict of ticker -> OHLCV DataFrame.
            min_avg_volume: Minimum average daily volume required.
            min_price: Minimum closing price required across the period.

        Returns:
            Filtered dict of price_data.
        """
        logger.info("Applying liquidity screen (Vol > %d, Price > %.2f)", min_avg_volume, min_price)
        filtered = {}
        for ticker, df in price_data.items():
            if df.empty or "Volume" not in df.columns or "Close" not in df.columns:
                continue
                
            avg_vol = df["Volume"].mean()
            min_px = df["Close"].min()
            
            if avg_vol >= min_avg_volume and min_px >= min_price:
                filtered[ticker] = df
            else:
                logger.debug("Ticker %s failed screen: Vol=%d, MinPx=%.2f", ticker, avg_vol, min_px)
                
        logger.info("Liquidity screen passed %d/%d tickers", len(filtered), len(price_data))
        return filtered

    def compute_log_returns(self, price_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """Compute logarithmic returns from closing prices.

        R_t = ln(P_t / P_{t-1})

        Args:
            price_data: Dict of ticker -> OHLCV DataFrame.

        Returns:
            Dict mapping ticker to its log returns Series.
        """
        returns_dict = {}
        for ticker, df in price_data.items():
            if "Close" in df.columns:
                close = df["Close"]
                # ln(P_t / P_{t-1})
                log_ret = np.log(close / close.shift(1))
                returns_dict[ticker] = log_ret.dropna()
        return returns_dict
