"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

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
    """agent 2: academic literature researcher lol"""

    def __init__(self, gemini_client):
        self.gemini = gemini_client
        self.literature_engine = LiteratureEngine(gemini_client)
        self.ssrn_scraper = SSRNScraper(gemini_client)
        self.mf_scraper = ModernFinanceScraper(gemini_client)
        self.chroma_store = ChromaStore(gemini_client)

    def _build_queries(self, hypothesis: HypothesisObject) -> List[str]:
        """generates 5-8 search queries mixing domain keywords and mathematical bounds lol"""
        base_keys = [k for k in hypothesis.key_variables if len(k) > 2]
        
                
                
                
        # Taxonomy mapping from math engine bounds
        cat = hypothesis.math_method_category.lower()
        math_map = {
            "time_series": "time series momentum autoregressive returns",
            "volatility_surface": "implied volatility surface equity returns cross-section",
            "mean_reversion": "mean reversion ornstein uhlenbeck pairs trading",
            "factor_model": "fama french multi-factor asset pricing cross-sectional",
            "options_pricing": "black scholes implied volatility skew risk premium",
            "regime_detection": "hidden markov regime switching volatility clustering"
        }
        
        math_keywords = math_map.get(cat, f"financial econometrics {cat}")
        target_keys_str = " ".join(base_keys[:3])
        
        queries = [
            f"{target_keys_str} {hypothesis.direction}",
            f"{target_keys_str} {math_keywords}",
            f"{hypothesis.asset_class or 'equity'} returns {math_keywords}",
            f"{hypothesis.scope or ''} {target_keys_str}",
            target_keys_str
        ]
        
                
                
                
        # Deduplicate and trim
        seen = set()
        clean_queries = []
        for q in queries:
            q_clean = " ".join(q.split())
            if len(q_clean) > 5 and q_clean not in seen:
                clean_queries.append(q_clean)
                seen.add(q_clean)
                
        return clean_queries[:8]

    def _deduplicate(self, raw_papers: List[PaperObject]) -> List[PaperObject]:
        """soft-match titles > 085 sequence similarity, keeping the highest influence score lol"""
        if not raw_papers:
            return []
            
        deduped = []
        for paper in raw_papers:
            is_dup = False
            for existing in deduped:
                ratio = difflib.SequenceMatcher(None, paper.title.lower(), existing.title.lower()).ratio()
                if ratio > 0.85:
                    is_dup = True
                                                                                # Keep the one with better metadata or relevance proxy
                                                                                # Since influence_score isn't strictly scalar across all models,
                                                                                # we use abstract length as a proxy for detail if both exist.
                    if len(paper.abstract) > len(existing.abstract):
                        existing.title = paper.title
                        existing.abstract = paper.abstract
                        existing.authors = paper.authors
                    break
            if not is_dup:
                deduped.append(paper)
        return deduped

    async def research(self, hypotheses: List[HypothesisObject], pulse: PulseEmitter) -> Dict[str, List[PaperObject]]:
        """main orchestrated loop for agent 2 lol"""
        citations_db: Dict[str, List[PaperObject]] = {}
        total_h = len(hypotheses)
        
                
                
                
        # 1. Emit Active Status
        await pulse.emit_status("literature", "active", 0, total_h, "Agent 2 Deployed", "Spanning 6 Academic Repositories", 0, total_h * 45)

        for i, hyp in enumerate(hypotheses):
            step = i + 1
            await pulse.emit_status("literature", "active", step, total_h, f"Researching Hypothesis {step}", f"Compiling queries for: {hyp.hypothesis[:40]}...", int((step/total_h)*100), (total_h-step)*45)

            
            
            
            # 2. Build queries
            queries = self._build_queries(hyp)
            
                        
                        
                        
            # 3. Concurrently search sources
                                                # To avoid rate limits, we use the first 2 queries for heavy APIs
            heavy_query = queries[0] if queries else "quantitative finance"
            broad_keys = [k for k in hyp.key_variables]

            
            
            
            # Trigger standard LiteratureEngine (arXiv, SemanticScholar, OpenAlex, CORE)
            eng_task = self.literature_engine.query_all_sources(heavy_query, max_results=5)
            
                        
                        
                        
            # Trigger Playwright SSRN Scraper
            ssrn_task = self.ssrn_scraper.scrape(heavy_query, limit=2)
            
                        
                        
                        
            # Trigger Modern Finance Scraper
            mf_task = self.mf_scraper.get_articles(broad_keys)
            
                        
                        
                        
            # Trigger Vector Retrieval from prior runs
            chroma_task = asyncio.to_thread(self.chroma_store.query_similar, heavy_query, top_k=2)

            
            
            
            # Gather raw papers
            raw_results = await asyncio.gather(eng_task, ssrn_task, mf_task, chroma_task, return_exceptions=True)
            
                        
                        
                        
            # Process results safely
            eng_papers = raw_results[0] if isinstance(raw_results[0], list) else []
            ssrn_papers = raw_results[1] if isinstance(raw_results[1], list) else []
            mf_papers = raw_results[2] if isinstance(raw_results[2], list) else []
            
                        
                        
                        
            # Chroma returns chunks, map them to simple PaperObjects if they are dictionaries
            chroma_papers = []
            if isinstance(raw_results[3], list):
                for chk in raw_results[3]:
                    if isinstance(chk, dict):
                        chroma_papers.append(PaperObject(
                            title=chk.get("paper_title", "Local Store Match"),
                            authors="Octant Cache",
                            year=2024,
                            journal_or_repo="ChromaDB Local",
                            abstract=chk.get("text", "")
                        ))

            all_raw_papers = eng_papers + ssrn_papers + mf_papers + chroma_papers
            
                        
                        
                        
            # 5. Emit progress
            await pulse.emit_status("literature", "active", step, total_h, f"Researching Hypothesis {step}", f"Retrieved {len(all_raw_papers)} raw documents.", int((step/total_h)*100), (total_h-step)*45)
            
                        
                        
                        
            # 4. Deduplicate
            unique_papers = self._deduplicate(all_raw_papers)
            
                        
                        
                        
            # 6. NLP Extraction: Gemini determines hypothesis support
                                                # We already have abstracts, but the master spec requests a batch structural pass
                                                # We'll re-run them through the Engine's Gemini method to inject the hypothesis context
            if unique_papers:
                analyzed_papers = await self.literature_engine._analyze_papers_with_gemini(unique_papers, hyp.hypothesis)
            else:
                analyzed_papers = []

            
            
            
            # 7. PULSE citation cards
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
                    "supports_hypothesis": support_flag
                })
                
                            
                            
                            
            # 8. Store in VectorDB
            if analyzed_papers:
                await asyncio.to_thread(self.chroma_store.embed_and_store, analyzed_papers)
                
                            
                            
                            
            # 9. Compute prior_art_summary
            supporting = sum(1 for p in analyzed_papers if p.supports_hypothesis == "YES")
            contradicting = sum(1 for p in analyzed_papers if p.supports_hypothesis == "NO")
            
            if len(analyzed_papers) < 3:
                novelty = "novel territory"
            elif supporting > 5:
                novelty = "well-documented signal"
            elif contradicting > supporting:
                novelty = "contrarian thesis"
            else:
                novelty = "mixed precedent"
                
            hyp.prior_art_summary = f"Found {len(analyzed_papers)} distinct papers. {supporting} support, {contradicting} contradict. Classification: {novelty}."
            hyp.literature_papers = analyzed_papers
            citations_db[getattr(hyp, "id", f"H{step}")] = analyzed_papers

        
        
        
        # 10. Emit Complete
        total_p = sum(len(papers) for papers in citations_db.values())
        await pulse.emit_status("literature", "complete", total_h, total_h, "Review Complete", f"{total_p} peer-reviewed papers catalogued globally.", 100, 0)
        
        return citations_db
