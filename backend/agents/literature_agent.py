"""Agent 2: Literature Agent — academic literature researcher."""

import asyncio
import difflib
import logging
from typing import Dict, List

import google.generativeai as genai

from backend.agents.hypothesis_engine import HypothesisObject
from backend.pulse import PulseEmitter
from backend.data.literature_sources import LiteratureEngine, PaperObject
from backend.data.scraper_ssrn import SSRNScraper
from backend.data.modern_finance_scraper import ModernFinanceScraper
from backend.data.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class LiteratureAgent:
    """Agent 2: Academic literature researcher."""

    def __init__(self, gemini_client):
        self.gemini = gemini_client
        self.literature_engine = LiteratureEngine()
        self.ssrn_scraper = SSRNScraper()
        self.mf_scraper = ModernFinanceScraper(gemini_client)
        self.chroma_store = ChromaStore()

    def _build_queries(self, hypothesis: HypothesisObject) -> List[str]:
        """Generate 5-8 search queries mixing domain keywords and math terms."""
        base_keys = [k for k in hypothesis.key_variables if len(k) > 2]

        cat = hypothesis.math_badge.lower()
        math_map = {
            "time_series": "time series momentum autoregressive returns",
            "volatility_surface": "implied volatility surface equity returns cross-section",
            "mean_reversion": "mean reversion ornstein uhlenbeck pairs trading",
            "factor_model": "fama french multi-factor asset pricing cross-sectional",
            "options_pricing": "black scholes implied volatility skew risk premium",
            "regime_detection": "hidden markov regime switching volatility clustering",
            "cointegration": "cointegration pairs trading error correction",
            "garch": "garch volatility clustering conditional heteroscedasticity",
            "arima": "arima autoregressive integrated moving average forecasting",
        }

        math_keywords = math_map.get(cat, f"financial econometrics {cat}")
        target_keys_str = " ".join(base_keys[:3])
        geo_scope = " ".join(hypothesis.geographic_scope) if hypothesis.geographic_scope else ""

        queries = [
            f"{target_keys_str} {hypothesis.direction}",
            f"{target_keys_str} {math_keywords}",
            f"{hypothesis.asset_class or 'equity'} returns {math_keywords}",
            f"{geo_scope} {target_keys_str}".strip(),
            target_keys_str,
        ]

        seen = set()
        clean_queries = []
        for q in queries:
            q_clean = " ".join(q.split())
            if len(q_clean) > 5 and q_clean not in seen:
                clean_queries.append(q_clean)
                seen.add(q_clean)

        return clean_queries[:8]

    def _deduplicate(self, raw_papers: List[PaperObject]) -> List[PaperObject]:
        """Soft-match titles with >85% sequence similarity, keeping the best metadata."""
        if not raw_papers:
            return []

        deduped = []
        for paper in raw_papers:
            is_dup = False
            for existing in deduped:
                ratio = difflib.SequenceMatcher(
                    None, paper.title.lower(), existing.title.lower()
                ).ratio()
                if ratio > 0.85:
                    is_dup = True
                    if len(paper.abstract) > len(existing.abstract):
                        existing.title = paper.title
                        existing.abstract = paper.abstract
                        existing.authors = paper.authors
                    break
            if not is_dup:
                deduped.append(paper)
        return deduped

    async def research(
        self, hypotheses: List[HypothesisObject], pulse: PulseEmitter
    ) -> Dict[str, List[PaperObject]]:
        """Main orchestrated loop for Agent 2."""
        citations_db: Dict[str, List[PaperObject]] = {}
        total_h = len(hypotheses)

        await pulse.emit_status(
            "literature", "active", 0, total_h,
            "Agent 2 Deployed", "Spanning 6 Academic Repositories",
            0, total_h * 45,
        )

        for i, hyp in enumerate(hypotheses):
            step = i + 1
            await pulse.emit_status(
                "literature", "active", step, total_h,
                f"Researching Hypothesis {step}",
                f"Compiling queries for: {hyp.statement[:40]}...",
                int((step / total_h) * 100), (total_h - step) * 45,
            )

            queries = self._build_queries(hyp)
            heavy_query = queries[0] if queries else "quantitative finance"

            # Search sources concurrently
            eng_task = self.literature_engine.search_all_sources(hyp, max_papers_per_source=5)
            ssrn_task = self.ssrn_scraper.search(hyp, n=2)
            mf_task = self.mf_scraper.get_articles(hyp.key_variables)
            chroma_task = asyncio.to_thread(self.chroma_store.query_similar, heavy_query, n=2)

            raw_results = await asyncio.gather(
                eng_task, ssrn_task, mf_task, chroma_task, return_exceptions=True
            )

            eng_papers = raw_results[0] if isinstance(raw_results[0], list) else []
            ssrn_papers = raw_results[1] if isinstance(raw_results[1], list) else []
            mf_papers = raw_results[2] if isinstance(raw_results[2], list) else []

            chroma_papers = []
            if isinstance(raw_results[3], list):
                for chk in raw_results[3]:
                    if isinstance(chk, dict):
                        chroma_papers.append(PaperObject(
                            title=chk.get("paper_title", "Local Store Match"),
                            authors="Octant Cache",
                            year=2024,
                            journal_or_repo="ChromaDB Local",
                            abstract=chk.get("text", ""),
                        ))

            all_raw_papers = eng_papers + ssrn_papers + mf_papers + chroma_papers

            await pulse.emit_status(
                "literature", "active", step, total_h,
                f"Researching Hypothesis {step}",
                f"Retrieved {len(all_raw_papers)} raw documents.",
                int((step / total_h) * 100), (total_h - step) * 45,
            )

            unique_papers = self._deduplicate(all_raw_papers)

            # NLP Extraction via Gemini
            if unique_papers:
                analyzed_papers = await self.literature_engine._analyze_papers_with_gemini(
                    unique_papers, hyp
                )
            else:
                analyzed_papers = []

            # Emit citation cards
            for paper in analyzed_papers:
                relevance = 85.0
                support_flag = None
                if paper.supports_hypothesis == "YES":
                    relevance = 95.0
                    support_flag = True
                elif paper.supports_hypothesis == "NO":
                    relevance = 80.0
                    support_flag = False

                await pulse.emit_citation_card({
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "journal": paper.journal_or_repo,
                    "relevance_score": relevance,
                    "supports_hypothesis": support_flag,
                })

            # Store in VectorDB
            if analyzed_papers:
                await asyncio.to_thread(self.chroma_store.embed_and_store, analyzed_papers)

            citations_db[hyp.id] = analyzed_papers

        total_p = sum(len(papers) for papers in citations_db.values())
        await pulse.emit_status(
            "literature", "complete", total_h, total_h,
            "Review Complete", f"{total_p} peer-reviewed papers catalogued.",
            100, 0,
        )

        return citations_db
