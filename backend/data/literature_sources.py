"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional

import httpx
import google.generativeai as genai

from backend.agents.hypothesis_engine import HypothesisObject
from backend.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class PaperObject:
    title: str
    authors: str
    year: int
    journal_or_repo: str
    abstract: str
    full_text: Optional[str] = None
    url: str = ""
    doi: str = ""
    arxiv_id: Optional[str] = None
    influence_score: Optional[float] = None
    
        
    # Gemini extracted fields
    key_finding: str = ""
    signal_tested: str = ""
    market_studied: str = ""
    time_period: str = ""
    performance_metric: str = ""
    statistical_methodology: str = ""
    effect_size: Optional[float] = None
    supports_hypothesis: Optional[bool] = None
    novelty_score: int = 0


class LiteratureEngine:
    """queries academic sources and analyses abstracts with gemini flash lol"""

    def __init__(self) -> None:
        settings = get_settings()
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("models/gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY unconfigured.")

    async def search_all_sources(self, hypothesis: HypothesisObject, max_papers_per_source: int = 20) -> List[PaperObject]:
        """orchestrate parallel queries to all academic sources lol"""
        logger.info("Starting literature search for Hypothesis %s", hypothesis.id)

        
        # Fire off all API searches in parallel
        results = await asyncio.gather(
            self._search_arxiv(hypothesis, max_papers_per_source),
            self._search_semantic_scholar(hypothesis, max_papers_per_source),
            self._search_openalex(hypothesis, max_papers_per_source),
            self._search_core(hypothesis, max_papers_per_source),
            return_exceptions=True
        )

        all_papers = []
        for res in results:
            if isinstance(res, list):
                all_papers.extend(res)
            elif isinstance(res, Exception):
                logger.error("A literature source failed: %s", res)

        
        # Deduplicate
        seen = set()
        unique_papers = []
        for p in all_papers:
            key = p.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_papers.append(p)

        logger.info("Found %d unique API papers for %s", len(unique_papers), hypothesis.id)
        
                
        # Analyze papers with Gemini Flash in batches
        if unique_papers and self.model:
            unique_papers = await self._analyze_papers_with_gemini(unique_papers, hypothesis)

        return unique_papers

    async def _search_arxiv(self, hypothesis: HypothesisObject, n: int) -> List[PaperObject]:
        """query arxiv api for quantitative finance categories lol"""
        kw = hypothesis.math_badge.lower().replace(" ", "+")
        query = f"all:{kw}+AND+(cat:q-fin.ST+OR+cat:q-fin.PM+OR+cat:q-fin.TR+OR+cat:q-fin.MF+OR+cat:q-fin.RM)"
        url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={n}&sortBy=relevance"
        
        papers = []
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=10)
                try:
                    import feedparser
                except ImportError:
                    logger.warning("feedparser missing. Skipping arXiv parsing.")
                    return papers
                    
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    papers.append(PaperObject(
                        title=entry.title.replace('\\n', ' '),
                        authors=", ".join(a.name for a in entry.authors),
                        year=int(entry.published[:4]),
                        journal_or_repo="arXiv",
                        abstract=entry.summary.replace('\\n', ' '),
                        url=entry.link,
                        arxiv_id=entry.id.split('/abs/')[-1]
                    ))
            except Exception as exc:
                logger.error("arXiv search failed: %s", exc)
        return papers

    async def _search_semantic_scholar(self, hypothesis: HypothesisObject, n: int) -> List[PaperObject]:
        """query semantic scholar api lol"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        query = f"{hypothesis.asset_class} {hypothesis.math_badge}"
        params = {
            "query": query,
            "limit": min(n, 100),
            "fields": "paperId,title,abstract,authors,year,citationCount,influenceScore,tldr,externalIds"
        }
        papers = []
        async with httpx.AsyncClient() as client:
            try:
                for attempt in range(3):
                    resp = await client.get(url, params=params, timeout=10)
                    if resp.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if resp.status_code == 200:
                        data = resp.json().get("data", [])
                        for item in data:
                            abstract = item.get("abstract") or (item.get("tldr") or {}).get("text", "")
                            if not abstract: continue
                            authors = ", ".join(a.get("name", "") for a in item.get("authors", []))
                            papers.append(PaperObject(
                                title=item.get("title", ""),
                                authors=authors,
                                year=item.get("year", 2020) or 2020,
                                journal_or_repo="Semantic Scholar",
                                abstract=abstract,
                                url=f"https://api.semanticscholar.org/{item.get('paperId')}",
                                influence_score=item.get("influenceScore", 0.0)
                            ))
                    break
            except Exception as exc:
                logger.error("Semantic Scholar search failed: %s", exc)
        return papers

    async def _search_openalex(self, hypothesis: HypothesisObject, n: int) -> List[PaperObject]:
        """query openalex works api lol"""
        search_query = urllib.parse.quote(hypothesis.math_badge)
        url = f"https://api.openalex.org/works?search={search_query}&sort=cited_by_count:desc&per-page={n}"
        papers = []
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("results", [])
                    for item in data:
                        abstract_inv = item.get("abstract_inverted_index", {})
                        abstract = "Abstract not available via inverted index parsing in this minimal stub"
                        if abstract_inv:
                            words = max([max(v) for v in abstract_inv.values()]) + 1
                            text_arr = [""] * words
                            for word, positions in abstract_inv.items():
                                for pos in positions:
                                    text_arr[pos] = word
                            abstract = " ".join(text_arr)
                        
                        authors = ", ".join(auth.get('author',{}).get('display_name','') for auth in item.get('authorships', []))
                        papers.append(PaperObject(
                            title=item.get("title", ""),
                            authors=authors,
                            year=item.get("publication_year", 2020) or 2020,
                            journal_or_repo="OpenAlex",
                            abstract=abstract,
                            doi=item.get("doi", "")
                        ))
            except Exception as exc:
                logger.error("OpenAlex search failed: %s", exc)
        return papers

    async def _search_core(self, hypothesis: HypothesisObject, n: int) -> List[PaperObject]:
        """query core api lol"""
        url = "https://api.core.ac.uk/v3/search/works"
        params = {"q": hypothesis.math_badge, "limit": n}
        settings = get_settings()
        headers = {"Authorization": f"Bearer {settings.CORE_API_KEY}"} if getattr(settings, "CORE_API_KEY", None) else {}
        papers = []
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("results", [])
                    for item in data:
                        abstract = item.get("abstract", "")
                        if not abstract: continue
                        authors = ", ".join(a.get("name","") for a in item.get("authors", []))
                        papers.append(PaperObject(
                            title=item.get("title", ""),
                            authors=authors,
                            year=item.get("yearPublished", 2020) or 2020,
                            journal_or_repo="CORE",
                            abstract=abstract,
                            url=item.get("downloadUrl", ""),
                            full_text=item.get("fullText", None)
                        ))
            except Exception as exc:
                logger.error("CORE API search failed: %s", exc)
        return papers

    async def _analyze_papers_with_gemini(self, papers: List[PaperObject], hypothesis: HypothesisObject) -> List[PaperObject]:
        """batch papers and extract metrics via gemini flash lol"""
        logger.info("Analysing %d papers with Gemini Flash for H-%s", len(papers), hypothesis.id)
        
        batch_size = 10
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            
            prompt = f"""
            Analyze these {len(batch)} paper abstracts against this HYPOTHESIS: "{hypothesis.statement}".
            
            Extract structured data. Return exactly a JSON array of objects (one per input paper, preserving order). Each object must have:
            "key_finding" (str), "signal_tested" (str), "market_studied" (str), "time_period" (str),
            "performance_metric" (str), "statistical_methodology" (str), "effect_size" (float or null),
            "supports_hypothesis" (boolean or null), "novelty_score" (int 0-100)
            
            PAPERS:
            """
            for j, p in enumerate(batch):
                prompt += f"\\nPAPER {j}: Title: {p.title}\\nAbstract: {p.abstract[:800]}\\n"
                
            try:
                response = await asyncio.to_thread(self.model.generate_content, prompt)
                txt = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(txt)
                
                if len(data) == len(batch):
                    for j, metrics in enumerate(data):
                        batch[j].key_finding = metrics.get("key_finding", "")
                        batch[j].signal_tested = metrics.get("signal_tested", "")
                        batch[j].market_studied = metrics.get("market_studied", "")
                        batch[j].time_period = metrics.get("time_period", "")
                        batch[j].performance_metric = metrics.get("performance_metric", "")
                        batch[j].statistical_methodology = metrics.get("statistical_methodology", "")
                        batch[j].effect_size = metrics.get("effect_size", None)
                        batch[j].supports_hypothesis = metrics.get("supports_hypothesis", None)
                        batch[j].novelty_score = metrics.get("novelty_score", 0)
            except Exception as exc:
                logger.error("Gemini batch extraction failed: %s", exc)
                
        return papers
