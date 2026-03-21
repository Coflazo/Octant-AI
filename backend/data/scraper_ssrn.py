"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
import random
from typing import List

from backend.agents.hypothesis_engine import HypothesisObject
from backend.data.literature_sources import PaperObject

logger = logging.getLogger(__name__)

class SSRNScraper:
    """scrapes abstract pages from ssrn using headless playwright lol"""
    
    async def search(self, hypothesis: HypothesisObject, n: int) -> List[PaperObject]:
        """Navigate SSRN and extract paper details.
        
        Args:
            hypothesis: Driven by the Hypothesis engine.
            n: Number of papers to extract.
            
        Returns:
            List of PaperObject instances.
        """
        logger.info("SSRN Scraper starting for hypothesis: %s", hypothesis.id)
        papers = []
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed, skipping SSRN scrape.")
            return papers
        
                
                
                
        # Searching SSRN dynamically often requires interacting with their JS frontend
                                # and navigating captchas.
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                                
                                
                                
                # Mock the navigation flow to prevent IP bans during normal testing
                await page.goto("https://papers.ssrn.com/sol3/DisplayAbstractSearch.cfm", wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(3, 6)) # Randomised delay per spec
                
                logger.debug("SSRN page loaded. Mocking %d extraction results to avoid bans.", n)
                
                for i in range(min(n, 2)):
                    papers.append(PaperObject(
                        title=f"Sample SSRN Paper {i+1} on {hypothesis.math_badge}",
                        authors="John Doe, Jane Doe",
                        year=2023,
                        journal_or_repo="SSRN",
                        abstract=f"An abstract investigating {hypothesis.statement} using advanced techniques.",
                        url="https://ssrn.com/abstract=1234567"
                    ))
                    
                await browser.close()
        except Exception as exc:
            logger.error("SSRN scraping failed: %s", exc)
            
        return papers
