"""
Octant AI — Agent 3: Universe Builder

Orchestrates the data acquisition phase across market prices, fundamental ratios,
and social sentiment to build the master dataset used by the dual backtesting engines.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.agents.hypothesis_engine import HypothesisObject
from backend.pulse import PulseEmitter
from backend.data.price_fetcher import PriceFetcher
from backend.data.fundamentals import FundamentalsEngine
from backend.data.fal_client import FalChartClient
from backend.data.wsb_trends import WSBTrendsClient
from backend.data.scraper_reddit import RedditScraper
from backend.sentiment.signal_constructor import SentimentSignalConstructor, SentimentSignal
from backend.data.ff5_factors import fetch_ff5_factors

logger = logging.getLogger(__name__)


class UniverseTooSmallError(Exception):
    """Raised when liquidity screens reduce the equity universe below the statistical threshold."""
    pass


@dataclass
class UniverseBuildResult:
    universe_df: pd.DataFrame
    price_matrix: Dict[str, pd.DataFrame]
    log_returns: Dict[str, pd.Series]
    sentiment_signals: Dict[str, SentimentSignal]
    ff5_factors: pd.DataFrame
    macro_indicators: Dict[str, float]


class UniverseBuilder:
    """Agent 3: Universe Builder."""

    def __init__(self, gemini_client):
        self.gemini = gemini_client
        self.price_fetcher = PriceFetcher()
        self.fundamentals = FundamentalsEngine()
        self.fal_client = FalChartClient()
        self.wsbt_client = WSBTrendsClient()
        self.reddit_scraper = RedditScraper()
        self.sentiment_constructor = SentimentSignalConstructor()

    async def build(
        self,
        hypothesis_list: List[HypothesisObject],
        exchanges: List[str],
        sector_filter: Optional[str],
        time_range: Tuple[str, str],
        pulse: PulseEmitter
    ) -> UniverseBuildResult:
        """Executes the full overarching universe construction flow.

        Args:
            hypothesis_list: Output from Agent 1.
            exchanges: Target exchange codes.
            sector_filter: String filter or None.
            time_range: Tuple of (start_date, end_date) in YYYY-MM-DD.
            pulse: PulseEmitter for real-time WebSockets integration.

        Returns:
            A UniverseBuildResult dataclass covering the entire market state.
        """
        start_date, end_date = time_range
        
        # 1. Emit PULSE Status Active
        await pulse.emit_status(
            agent="universe",
            status="active",
            step=1,
            total=10,
            message_title="Building the Equity Universe",
            message_subtitle=f"Screener spanning {len(exchanges)} exchanges...",
            percent=10,
            estimated_remaining_sec=120
        )

        # 2. Extract inference constraints from hypotheses
        # A simple consensus check over the hypotheses for dynamic sector hints
        dynamic_sectors = set(h.asset_class for h in hypothesis_list if h.asset_class)
        logger.info("Hypothesis implicit asset classes: %s", dynamic_sectors)

        # 3. Fetch candidate tickers
        candidate_tickers = await self.price_fetcher.fetch_universe_tickers(
            exchanges=exchanges,
            sector=sector_filter,
            max_tickers=50  # Capped for safety during beta
        )

        # 4. Emit PULSE Progress
        await pulse.emit_status("universe", "active", 2, 10, "Fetching Market Data", f"Checking {len(candidate_tickers)} candidates", 20, 100)

        # 5. Download OHLCV Data
        raw_prices = await self.price_fetcher.fetch_ohlcv(
            tickers=candidate_tickers,
            start_date=start_date,
            end_date=end_date
        )

        # 6. Apply Liquidity Screen
        await pulse.emit_status("universe", "active", 3, 10, "Applying Liquidity Screens", "Min $1.00 & 500k Adv/Vol", 30, 90)
        clean_prices = self.price_fetcher.apply_liquidity_screen(
            price_data=raw_prices,
            min_avg_volume=500000,
            min_price=1.0
        )

        surviving_tickers = list(clean_prices.keys())
        if len(surviving_tickers) < 5:
            err_msg = f"Universe screen reduced candidates to {len(surviving_tickers)}, failing statistical threshold of 5."
            await pulse.emit_error("universe", err_msg, "Expand your exchange selection or alter sector filters.")
            raise UniverseTooSmallError(err_msg)

        # 7. Fetch Fundamentals
        await pulse.emit_status("universe", "active", 5, 10, "Pulling Fundamentals", "Retrieving metrics via OpenBB", 50, 70)
        
        fundamentals_tasks = asyncio.gather(
            self.fundamentals.get_short_interest(surviving_tickers),
            self.fundamentals.get_sector_classification(surviving_tickers),
            self.fundamentals.get_market_caps(surviving_tickers),
            # self.fundamentals.get_earnings_dates(surviving_tickers),
            self.fundamentals.get_macro_indicators(),
            return_exceptions=True
        )
        fin_results = await fundamentals_tasks
        
        short_interest = fin_results[0] if isinstance(fin_results[0], dict) else {}
        sectors = fin_results[1] if isinstance(fin_results[1], dict) else {}
        mkt_caps = fin_results[2] if isinstance(fin_results[2], dict) else {}
        macro_indicators = fin_results[3] if isinstance(fin_results[3], dict) else {}

        # 8. Emit ticker_card PULSE events (with fal.ai fallback) -> Concurrency!
        await pulse.emit_status("universe", "active", 6, 10, "Rendering Ticker Cards", "Calling fal.ai flux-pro", 60, 50)
        
        async def _emit_ticker(ticker: str):
            df = clean_prices[ticker]
            close_prices = df["Close"].dropna().tail(30).tolist() if "Close" in df.columns else []
            
            spark_url = ""
            if close_prices:
                spark_url = await self.fal_client.generate_sparkline(ticker, close_prices)
                
            await pulse.emit_ticker_card({
                "symbol": ticker,
                "name": f"{ticker} Corporation",
                "exchange": exchanges[0] if exchanges else "UNK",
                "sector": sectors.get(ticker, "Unknown"),
                "sparkline_url": spark_url,
                "mktcap": mkt_caps.get(ticker, 0.0),
                "short_interest": short_interest.get(ticker, 0.0)
            })
            
        emit_tasks = [asyncio.create_task(_emit_ticker(t)) for t in surviving_tickers]
        await asyncio.gather(*emit_tasks, return_exceptions=True)

        # 9. Concurrently run Sentiment Scrapers
        await pulse.emit_status("universe", "active", 7, 10, "Scraping Social Sentiment", "Reddit Playwright + WSBTrends", 70, 40)
        sentiment_fetch_tasks = await asyncio.gather(
            self.wsbt_client.get_mention_counts(window_days=7),
            self.reddit_scraper.scrape(ticker_list=surviving_tickers),
            return_exceptions=True
        )
        wsbt_counts = sentiment_fetch_tasks[0] if isinstance(sentiment_fetch_tasks[0], dict) else {}
        reddit_posts = sentiment_fetch_tasks[1] if isinstance(sentiment_fetch_tasks[1], list) else []

        # 10. Build sentiment signals
        await pulse.emit_status("universe", "active", 8, 10, "Constructing Sentiment Signals", "Gemini 2.5 NLP Extraction", 80, 20)
        sentiment_signals = await self.sentiment_constructor.build_signal(
            wsbt_counts=wsbt_counts,
            reddit_posts=reddit_posts,
            gemini_client=self.gemini
        )

        # 11. Fetch FF5 factors
        await pulse.emit_status("universe", "active", 9, 10, "Pulling Fama-French", "Downloading FF5 2x3 Daily", 90, 10)
        ff5_factors = await fetch_ff5_factors(start_date, end_date)

        # 12. Compute log returns
        log_returns = self.price_fetcher.compute_log_returns(clean_prices)

        # 13. Assemble the Universe DataFrame
        universe_data = []
        for t in surviving_tickers:
            z_score = 0.0
            if t in sentiment_signals:
                z_score = sentiment_signals[t].z_score
                
            universe_data.append({
                "ticker": t,
                "exchange": exchanges[0] if exchanges else "UNK",
                "sector": sectors.get(t, "Unknown"),
                "mktcap": mkt_caps.get(t, 0.0),
                "short_interest": short_interest.get(t, 0.0),
                "sentiment_z_score": z_score
            })
        universe_df = pd.DataFrame(universe_data).set_index("ticker")

        # 14. Complete
        await pulse.emit_status("universe", "complete", 10, 10, "Universe Generated", f"{len(surviving_tickers)} distinct assets processed.", 100, 0)
        logger.info("Agent 3 Universe Builder complete. Survived: %d", len(surviving_tickers))

        return UniverseBuildResult(
            universe_df=universe_df,
            price_matrix=clean_prices,
            log_returns=log_returns,
            sentiment_signals=sentiment_signals,
            ff5_factors=ff5_factors,
            macro_indicators=macro_indicators
        )
