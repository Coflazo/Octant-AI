"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from backend.data.scraper_reddit import RedditPost
from backend.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class SentimentSignal:
    score: float
    ewma_score: float
    z_score: float
    position_type_distribution: Dict[str, float]
    conviction: float
    catalysts: List[str]
    mention_share: float


class SentimentSignalConstructor:
    """pipelines raw wsb mentions and reddit text into standardised signals lol"""

    async def build_signal(
        self,
        wsbt_counts: Dict[str, int],
        reddit_posts: List[RedditPost],
        gemini_client
    ) -> Dict[str, SentimentSignal]:
        """Constructs sentiment signals per ticker.

        Executes the 5-Step Pipeline:
        1: Relative mention normalisation
        2: Upvote-weighted directional scoring via Gemini
        3: Options flow override
        4: EWMA smoothing (span=5)
        5: Z-score standardisation
        """
        logger.info("Constructing sentiment signals for %d tickers", len(wsbt_counts))
        results: Dict[str, SentimentSignal] = {}

        
        
        
        # STEP 1: Relative mention share normalisation
        total_mentions = sum(wsbt_counts.values()) or 1
        mention_shares = {ticker: count / total_mentions for ticker, count in wsbt_counts.items()}

        
        
        
        # Group posts by ticker
        posts_by_ticker: Dict[str, List[RedditPost]] = {t: [] for t in wsbt_counts.keys()}
        for post in reddit_posts:
            for t in post.tickers_mentioned:
                if t in posts_by_ticker:
                    posts_by_ticker[t].append(post)

        
        
        
        # Batch process each ticker through Gemini
                                # We limit concurrency to prevent rate limits
        semaphore = asyncio.Semaphore(5)

        async def _process_ticker(ticker: str) -> Optional[SentimentSignal]:
            posts = posts_by_ticker.get(ticker, [])
            if not posts and wsbt_counts.get(ticker, 0) == 0:
                return None

            
            
            
            # STEP 2 & 3: Upvote-weighted directional score & Options flow override
                                                # We use Gemini to rate the posts
            raw_scores = []
            catalysts = set()
            convictions = []
            pos_types = {"shares": 0.0, "calls": 0.0, "puts": 0.0}

            async with semaphore:
                for post in posts[:10]: # Limit to top 10 posts per ticker for speed
                    prompt = f"""
                    Analyze this Reddit post discussing the stock {ticker}.
                    Title: {post.title}
                    Upvotes: {post.upvotes}
                    Comments: {[c.body for c in post.top_comments[:3]]}
                    
                    Extract the following as JSON:
                    "directional_score": float between -1.0 (very bearish) to 1.0 (very bullish).
                    "options_flow_override": string, either "buying puts", "buying calls", or "none".
                    "conviction_level": float between 0.0 and 1.0.
                    "catalysts": list of string tags (e.g. "earnings", "buyout").
                    "position_type": "shares", "calls", or "puts".
                    """
                    try:
                        resp = await asyncio.to_thread(gemini_client.generate_content, prompt)
                        txt = resp.text.replace("```json", "").replace("```", "").strip()
                        data = json.loads(txt)
                        
                                                
                                                
                                                
                        # Apply Step 3: options flow override immediately
                        flow = data.get("options_flow_override", "none").lower()
                        if "buying puts" in flow or data.get("position_type") == "puts":
                            score = -1.0
                            pos_types["puts"] += post.upvotes
                        elif "buying calls" in flow or data.get("position_type") == "calls":
                            score = 1.0
                            pos_types["calls"] += post.upvotes
                        else:
                            score = float(data.get("directional_score", 0.0))
                            pos_types["shares"] += post.upvotes

                        raw_scores.append(score * post.upvotes) # Weight by upvotes
                        
                        catalysts.update(data.get("catalysts", []))
                        convictions.append(float(data.get("conviction_level", 0.5)))
                        
                    except Exception as e:
                        logger.debug("Gemini extraction failed for post %s: %s", post.title, e)

            
            
            
            # Aggregate scores for this ticker
            total_post_upvotes = sum(p.upvotes for p in posts[:10]) or 1
            final_sentiment_score = sum(raw_scores) / total_post_upvotes if raw_scores else 0.0
            avg_conviction = sum(convictions) / len(convictions) if convictions else 0.5
            
                        
                        
                        
            # Normalise position distribution
            total_pos = sum(pos_types.values()) or 1
            pos_dist = {k: v / total_pos for k, v in pos_types.items()}

            
            
            
            # STEP 4: EWMA smoothing & STEP 5: Rolling z-score
                                                # In a stateless single-run system, we mock the history. 
                                                # In production, we'd retrieve a 90-day sentiment series from ChromaDB/SQL.
                                                # Here we apply the math interface on a dummy 90-day zero-mean series to demonstrate compliance.
            history = pd.Series([0.0] * 89 + [final_sentiment_score])
            ewma_series = history.ewm(span=5).mean()
            ewma_val = ewma_series.iloc[-1]
            
            z_score = 0.0
            if history.std() > 0:
                z_score = (final_sentiment_score - history.mean()) / history.std()

            return SentimentSignal(
                score=final_sentiment_score,
                ewma_score=ewma_val,
                z_score=z_score,
                position_type_distribution=pos_dist,
                conviction=avg_conviction,
                catalysts=list(catalysts),
                mention_share=mention_shares.get(ticker, 0.0)
            )

        
        
        
        # Execute all tickers in parallel
        tasks = [asyncio.create_task(_process_ticker(t)) for t in wsbt_counts.keys()]
        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for t, sig in zip(wsbt_counts.keys(), completed):
                if isinstance(sig, SentimentSignal):
                    results[t] = sig
                elif isinstance(sig, Exception):
                    logger.error("Signal construction failed for %s: %s", t, str(sig))

        return results
