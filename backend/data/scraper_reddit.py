"""
Octant AI — Sentiment Data: Playwright Reddit Scraper

Headless React SPA scraper targeting r/wallstreetbets and similar subreddits.
Extracts post and comment text for downstream NLP sentiment pipeline.
"""

import asyncio
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RedditComment:
    author: str
    body: str
    upvotes: int
    tickers_mentioned: List[str] = field(default_factory=list)


@dataclass
class RedditPost:
    title: str
    url: str
    upvotes: int
    post_time: str
    tickers_mentioned: List[str] = field(default_factory=list)
    top_comments: List[RedditComment] = field(default_factory=list)


class RedditScraper:
    """Scrapes financial subreddits for sentiment signal construction."""

    def __init__(self, target_subreddits: Optional[List[str]] = None):
        self.subreddits = target_subreddits or [
            "wallstreetbets", "stocks", "investing", 
            "ValueInvesting", "StockMarket", "Superstonk"
        ]
        
        # Load local tickers database if available, else fallback to standard subset
        self.known_tickers: Set[str] = set()
        self._load_tickers()

    def _load_tickers(self) -> None:
        """Loads a local JSON file of 3000+ US ticker symbols for regex matching."""
        db_path = Path("backend/data/tickers.json")
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    self.known_tickers = set(json.load(f))
            except Exception as e:
                logger.warning("Failed to load tickers.json: %s", e)
        else:
            logger.warning("backend/data/tickers.json not found, loading fallback ticker subset.")
            self.known_tickers = {"AAPL", "MSFT", "TSLA", "GME", "AMC", "NVDA", "SPY", "QQQ"}

    def _extract_tickers(self, text: str) -> List[str]:
        """Find strictly uppercase words (2-5 letters) matching known tickers."""
        words = re.findall(r"\b[A-Z]{2,5}\b", text)
        return list(set(w for w in words if w in self.known_tickers))

    async def _random_delay(self) -> None:
        """Between page navigations: await asyncio.sleep(random.normalvariate(5, 1.5)) clamped to [3, 8] seconds."""
        delay = max(3.0, min(8.0, random.normalvariate(5.0, 1.5)))
        await asyncio.sleep(delay)

    async def scrape(self, ticker_list: Optional[List[str]] = None) -> List[RedditPost]:
        """Scrape configured subreddits for Hot posts.

        Args:
            ticker_list: Optional subset of tickers to look for.

        Returns:
            A list of RedditPost objects containing the title, score, and comments.
        """
        logger.info("Starting Playwright Reddit scraper on %d subreddits", len(self.subreddits))
        all_posts: List[RedditPost] = []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Skipping Reddit scraper.")
            return all_posts

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                
                # Setup realistic anti-bot context
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                    viewport={"width": random.randint(1200, 1600), "height": random.randint(800, 1080)}
                )
                
                page = await context.new_page()

                for sub in self.subreddits:
                    sub_url = f"https://www.reddit.com/r/{sub}/hot/"
                    logger.info("Scraping %s", sub_url)
                    
                    try:
                        await page.goto(sub_url, wait_until="networkidle")
                        await page.wait_for_selector('shreddit-feed', timeout=15000)
                        
                        # Extract top post titles, upvotes, times, URLs using evaluate
                        # Reddit redesign uses JS web components (<shreddit-post>)
                        page_posts = await page.evaluate('''() => {
                            const posts = Array.from(document.querySelectorAll('shreddit-post')).slice(0, 20);
                            return posts.map(p => ({
                                title: p.getAttribute('post-title') || '',
                                url: p.getAttribute('content-href') || p.getAttribute('permalink') || '',
                                upvotes: parseInt(p.getAttribute('score') || '0', 10),
                                post_time: p.getAttribute('created-timestamp') || ''
                            }));
                        }''')
                        
                        # Find the top quintile threshold (top 20% of the 20 posts)
                        if page_posts:
                            page_posts.sort(key=lambda x: x["upvotes"], reverse=True)
                            threshold_idx = max(0, int(len(page_posts) * 0.2) - 1)
                            quintile_threshold = page_posts[threshold_idx]["upvotes"]
                            
                            for post_data in page_posts:
                                title = post_data["title"]
                                url = post_data["url"]
                                upvotes = post_data["upvotes"]
                                
                                tickers_in_title = self._extract_tickers(title)
                                if ticker_list:
                                    # Cross-filter
                                    tickers_in_title = [t for t in tickers_in_title if t in ticker_list]

                                # Filter: upvotes in top quintile OR contains ticker
                                if upvotes >= quintile_threshold or (len(tickers_in_title) > 0):
                                    post_obj = RedditPost(
                                        title=title,
                                        url=url if url.startswith("http") else f"https://www.reddit.com{url}",
                                        upvotes=upvotes,
                                        post_time=post_data["post_time"],
                                        tickers_mentioned=tickers_in_title
                                    )
                                    
                                    # Detailed comment extraction phase
                                    await self._random_delay()
                                    await page.goto(post_obj.url, wait_until="networkidle")
                                    # Wait for comments tree to render
                                    try:
                                        await page.wait_for_selector('shreddit-comment-tree', timeout=15000)
                                        # Extract top 50 comments
                                        comments_data = await page.evaluate('''() => {
                                            const comments = Array.from(document.querySelectorAll('shreddit-comment')).slice(0, 50);
                                            return comments.map(c => ({
                                                author: c.getAttribute('author') || 'Unknown',
                                                body: c.querySelector('div[id*="-post-rtjson-content"]')?.textContent?.trim() || '',
                                                upvotes: parseInt(c.getAttribute('score') || '0', 10)
                                            }));
                                        }''')
                                        
                                        for c in comments_data:
                                            body = c["body"]
                                            if body:
                                                c_tickers = self._extract_tickers(body)
                                                if ticker_list:
                                                    c_tickers = [t for t in c_tickers if t in ticker_list]
                                                
                                                post_obj.top_comments.append(RedditComment(
                                                    author=c["author"],
                                                    body=body,
                                                    upvotes=c["upvotes"],
                                                    tickers_mentioned=c_tickers
                                                ))
                                    except Exception as e:
                                        logger.debug("Comments failed to load for %s: %s", post_obj.url, e)
                                        
                                    all_posts.append(post_obj)

                    except Exception as e:
                        logger.error("Failed to scrape subreddit r/%s: %s", sub, e)
                        
                    await self._random_delay()
                    
                await browser.close()
                
        except Exception as exc:
            logger.error("Playwright session failed: %s", exc)

        logger.info("Scraped %d highly relevant Reddit posts across networks.", len(all_posts))
        return all_posts
