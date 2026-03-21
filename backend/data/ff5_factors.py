"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)








# Standard Ken French data library URL for 5-Factor daily
FF5_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"


async def fetch_ff5_factors(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch the daily 5-Factor metrics with local caching.

    Downloads from Ken French's data library CSV URL, caches locally
    in data/ff5_cache/, parses with pandas, and returns daily returns
    aligned to the specified date range.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        A pandas DataFrame with DatetimeIndex and factor columns.
    """
    logger.info("Fetching Fama-French 5-Factor daily data (%s to %s)", start_date, end_date)

    cache_dir = Path("data/ff5_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "F-F_Research_Data_5_Factors_2x3_daily.csv"

    def _sync_fetch_and_parse() -> pd.DataFrame:
        if not cache_file.exists():
            import urllib.request
            import zipfile
            import io
            
            logger.info("Downloading Fama-French factors from Ken French library...")
            try:
                response = urllib.request.urlopen(FF5_URL)
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                                                                                # Assumes there is only 1 CSV in the zip
                    csv_name = z.namelist()[0]
                    with z.open(csv_name) as f:
                        content = f.read()
                        
                                                
                                                
                                                
                        # Cache raw CSV content locally
                        with open(cache_file, "wb") as out:
                            out.write(content)
            except Exception as e:
                logger.error("Failed downloading FF5 zip: %s", e)
                return pd.DataFrame()

        
        
        
        # Parse the CSV. Ken French CSVs have a multi-line header, 
                                # usually the data starts after row 3, and ends before copyright info.
        try:
                                                # We skip the first 3 rows since the header is on row 3 usually
            df = pd.read_csv(cache_file, skiprows=3, index_col=0)
            
                        
                        
                        
            # The last few rows might be copyright strings instead of dates, so we clean it up
            df.index = pd.to_datetime(df.index, format="%Y%m%d", errors="coerce")
            df = df.dropna(subset=[df.columns[0]]) # drop metadata rows at the bottom
            
                        
                        
                        
            # Convert percentage returns to decimals
            df = df.astype(float) / 100.0
            
                        
                        
                        
            # Filter by requested date range
            mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
            df = df.loc[mask]
            
            return df
        except Exception as e:
            logger.error("Failed parsing FF5 CSV: %s", e)
            return pd.DataFrame()

    try:
        factors_df = await asyncio.to_thread(_sync_fetch_and_parse)
        logger.info("Fetched %d days of Fama-French factors.", len(factors_df))
        return factors_df
    except Exception as exc:
        logger.error("Failed to fetch Fama-French data: %s", str(exc), exc_info=True)
        return pd.DataFrame()
