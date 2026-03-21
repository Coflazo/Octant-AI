"""
Octant AI — Data Fetcher: Fama-French 5-Factor Data.

Pulls daily Kenneth French data library factors for use with the cross-sectional
pricing engines (Agent 4 and Math Engine).
"""

import asyncio
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class FamaFrenchFetcher:
    """Downloads Fama-French data from the Kenneth French Data Library."""

    async def fetch_daily_factors(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch the daily 5-Factor metrics.

        Data is pulled via pandas_datareader from Ken French's site.
        Includes: Mkt-RF, SMB, HML, RMW, CMA, and RF (Risk-Free rate).

        Args:
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            A pandas DataFrame with DatetimeIndex and factor columns.
            Values are divided by 100 since the source is in percentages.
        """
        logger.info("Fetching Fama-French 5-Factor daily data (%s to %s)", start_date, end_date)

        def _fetch_sync():
            try:
                import pandas_datareader.data as web
            except ImportError:
                logger.warning("pandas_datareader not installed. Cannot fetch FF5 data.")
                return pd.DataFrame()

            # pandas_datareader API typically returns a dictionary of datasets
            # 'F-F_Research_Data_5_Factors_2x3_daily' is the standard identifier
            df_dict = web.DataReader(
                "F-F_Research_Data_5_Factors_2x3_daily",
                "famafrench",
                start=start_date,
                end=end_date,
            )
            # The first dataframe [0] contains the factors
            factors = df_dict[0]
            # Convert percentage returns to decimals
            factors = factors / 100.0
            return factors

        try:
            factors_df = await asyncio.to_thread(_fetch_sync)
            if factors_df.empty:
                logger.warning("Fama-French fetch returned empty DataFrame.")
            else:
                logger.info("Fetched %d days of Fama-French factors", len(factors_df))
            return factors_df
        except Exception as exc:
            logger.error(
                "Failed to fetch Fama-French data from Ken French library: %s",
                str(exc),
                exc_info=True,
            )
            # Return an empty DataFrame so downstream methods can fallback
            return pd.DataFrame()
