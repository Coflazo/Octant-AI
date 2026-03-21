"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import json
import logging
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




# Regex that matches standalone uppercase word (potential ticker)
TICKER_RE = re.compile(r'\b([A-Z]{1,5})\b')


class RedditScraper:
    """scrapes financial subreddits for sentiment signal construction lol"""

    def __init__(self, target_subreddits: Optional[List[str]] = None):
        self.subreddits = target_subreddits or [
            "wallstreetbets", "stocks", "investing", 
            "ValueInvesting", "StockMarket", "Superstonk"
        ]
        
        self.known_tickers: Set[str] = set()
        self._load_tickers()

    def _load_tickers(self) -> None:
        """loads a local json file of 3000+ us ticker symbols for regex matching lol"""
        db_path = Path("backend/data/tickers.json")
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    self.known_tickers = set(json.load(f))
            except Exception as e:
                logger.warning("Failed to load tickers.json: %s", e)
        else:
            logger.warning("backend/data/tickers.json not found, loading user's known subset.")
            self.known_tickers = {
                "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "AMD",
                "INTC", "NFLX", "BABA", "DIS", "BA", "GE", "F", "GM", "PFE", "MRNA",
                "QQQ", "SPY", "IWM", "GME", "AMC", "BB", "PLTR", "SOFI", "UBER"
            }

    def _extract_tickers(self, text: str) -> List[str]:
        """find strictly uppercase words (1-5 letters) matching known tickers lol"""
        found = []
        for match in TICKER_RE.finditer(text):
            ticker = match.group(1)
            if ticker in self.known_tickers:
                found.append(ticker)
        return list(set(found))

    async def _random_delay(self) -> None:
        """between page navigations: await asynciosleep(randomnormalvariate(5, 15)) clamped to [3, 8] seconds lol"""
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
        
                
        # Override known tickers entirely if specifically searching for a dynamic subset
        if ticker_list:
            self.known_tickers.update(ticker_list)

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
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                    viewport={"width": random.randint(1200, 1600), "height": random.randint(800, 1080)}
                )
                
                page = await context.new_page()

                for sub in self.subreddits:
                    sub_url = f"https://www.reddit.com/r/{sub}/hot/"
                    logger.info("Scraping %s", sub_url)
                    
                    try:
                        await page.goto(sub_url, timeout=60000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)
                        
                        scroll_rounds = 4
                        for i in range(scroll_rounds):
                            await page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
                            await page.wait_for_timeout(2000)
                        
                                                
                        # Extract top post titles, upvotes, times, URLs using fallback evaluation
                        page_posts = await page.evaluate('''() => {
                            let results = [];
                            document.querySelectorAll('shreddit-post').forEach(el => {
                                const title = el.getAttribute('post-title') || el.getAttribute('aria-label') || '';
                                if (title) {
                                    results.push({
                                        title: title,
                                        url: el.getAttribute('content-href') || el.getAttribute('permalink') || '',
                                        upvotes: parseInt(el.getAttribute('score') || '0', 10),
                                        post_time: el.getAttribute('created-timestamp') || ''
                                    });
                                }
                            });
                            // Fallbacks
                            if (results.length === 0) {
                                document.querySelectorAll('.Post').forEach(el => {
                                    const h3 = el.querySelector('h3');
                                    if(h3) {
                                        results.push({
                                            title: h3.innerText,
                                            url: '',
                                            upvotes: 0,
                                            post_time: ''
                                        });
                                    }
                                });
                            }
                            return results.slice(0, 30);
                        }''')
                        
                                                
                        # Filter for relevance to our universe
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
                                    tickers_in_title = [t for t in tickers_in_title if t in ticker_list]

                                
                                # Filter logic (top quintile or contains relevant ticker)
                                if upvotes >= quintile_threshold or (len(tickers_in_title) > 0):
                                    post_obj = RedditPost(
                                        title=title,
                                        url=url if url.startswith("http") else f"https://www.reddit.com{url}",
                                        upvotes=upvotes,
                                        post_time=post_data["post_time"],
                                        tickers_mentioned=tickers_in_title
                                    )
                                    
                                                                        
                                    # Optional: Comment scraping can be added here as in Section 7
                                    all_posts.append(post_obj)

                    except Exception as e:
                        logger.error("Failed to scrape subreddit r/%s: %s", sub, e)
                        
                    await self._random_delay()
                    
                await browser.close()
                
        except Exception as exc:
            logger.error("Playwright session failed: %s", exc)

        logger.info("Scraped %d highly relevant Reddit posts across networks.", len(all_posts))
        return all_posts
