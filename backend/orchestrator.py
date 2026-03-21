"""
Octant AI — Backend Orchestrator

The topmost coordinator class that translates frontend inputs or
Dust.tt API triggers into physical Agent invocations. Implements strict
`asyncio.gather` boundaries to enforce concurrent Literature and Universe queries,
while respecting atomic pipeline cancellation flags.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai

from backend.config import GEMINI_API_KEY
from backend.pulse import PulseEmitter
from backend.session_manager import session_manager
from backend.agents.hypothesis_engine import HypothesisEngine
from backend.agents.literature_agent import LiteratureAgent
from backend.agents.universe_builder import UniverseBuilder
from backend.agents.backtesting_agent import BacktestingAgent
from backend.agents.report_architect import ReportArchitect
from backend.math_engine.performance import PerformanceReport

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
gemini_client = genai


class PipelineStoppedError(Exception):
    """Raised natively when a frontend cancellation kills the session pipeline."""
    pass


@dataclass
class PipelineRequest:
    session_id: str
    thesis: str
    exchanges: List[str]
    time_range: Tuple[str, str]
    sector: Optional[str] = None


@dataclass
class PipelineResult:
    pdf_path: str
    hypotheses: List[any]
    citations_db: Dict[str, List[any]]
    results_manifest: Dict[str, PerformanceReport]
    universe_result: any


class OctantOrchestrator:
    """Master Pipeline Coordinator enforcing the 5-Agent Directed Acyclic Graph."""

    def __init__(self):
        # Initialise agents passing down the global injected Gemini resource
        self.hypothesis_engine = HypothesisEngine(gemini_client)
        self.literature_agent = LiteratureAgent(gemini_client)
        self.universe_builder = UniverseBuilder()
        self.backtesting_agent = BacktestingAgent()
        self.report_architect = ReportArchitect(gemini_client)

    async def _check_stop(self, session_id: str):
        """Raises a hard kill signal if the frontend interrupted the process."""
        state = await session_manager.get(session_id)
        if state and state.stop_flag.is_set():
            logger.warning("Pipeline halt intercepted for session %s.", session_id)
            raise PipelineStoppedError("Orchestration interrupted by user.")

    async def run_pipeline(self, request: PipelineRequest, pulse: PulseEmitter) -> PipelineResult:
        """The core quantitative pipeline routing logic."""
        session_id = request.session_id
        
        try:
            # 1. Start Phase
            await self._check_stop(session_id)
            await pulse.emit_status("orchestrator", "active", 1, 5, "Initializing", "Kicking off 5-node pipeline...")

            # 2. Agent 1 -> Hypothesis Engine
            await self._check_stop(session_id)
            hypotheses = await self.hypothesis_engine.generate(request.thesis, pulse)
            await session_manager.update(session_id, hypotheses=hypotheses)

            # 3. Agents 2 & 3 -> Concurrent Literature and Universe Builder
            await self._check_stop(session_id)
            await pulse.emit_status("orchestrator", "active", 2, 5, "Concurrent Research", "Spinning up Agent 2 (Literature) & Agent 3 (Universe)")
            
            # Using asyncio.gather for parallel fork-join semantics per spec
            literature_task = asyncio.create_task(
                self.literature_agent.research(hypotheses, pulse)
            )
            universe_task = asyncio.create_task(
                self.universe_builder.build(hypotheses, request.exchanges, request.sector, request.time_range, pulse)
            )
            
            citations_db, universe_result = await asyncio.gather(literature_task, universe_task)
            
            # 4. Agent 4 -> Backtesting Engine
            await self._check_stop(session_id)
            results_manifest = await self.backtesting_agent.run(universe_result, hypotheses, citations_db, pulse)
            await session_manager.update(session_id, results_manifest=results_manifest)

            # 5. Agent 5 -> Report Architect
            await self._check_stop(session_id)
            pdf_path = await self.report_architect.generate(hypotheses, citations_db, results_manifest, pulse)
            await session_manager.update(session_id, pdf_path=pdf_path, status="complete")
            
            # Final Success pulse
            await pulse.emit_status("orchestrator", "complete", 5, 5, "Success", "Pipeline finished execution.")

            return PipelineResult(
                pdf_path=pdf_path,
                hypotheses=hypotheses,
                citations_db=citations_db,
                results_manifest=results_manifest,
                universe_result=universe_result
            )

        except PipelineStoppedError as e:
            logger.info("Pipeline %s exited early: %s", session_id, str(e))
            await pulse.emit_status("orchestrator", "error", 0, 0, "Aborted", "User killed the test string.")
            await session_manager.update(session_id, status="stopped")
            raise
            
        except Exception as e:
            logger.error("Terminal exception in Orchestrator for %s: %s", session_id, e, exc_info=True)
            await pulse.emit_status("orchestrator", "error", 0, 0, "Catastrophic Failure", f"Uncaught exception: {str(e)}")
            await session_manager.update(session_id, status="error")
            raise e
