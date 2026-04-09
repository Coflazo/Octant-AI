"""Pipeline orchestrator — coordinates the 5-agent directed acyclic graph."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from backend.config import get_settings
from backend.exceptions import PipelineStoppedError
from backend.llm_provider import get_llm_provider, get_embedding_provider
from backend.pulse import PulseEmitter
from backend.session_manager import session_manager
from backend.agents.hypothesis_engine import HypothesisEngine
from backend.agents.literature_agent import LiteratureAgent
from backend.agents.universe_builder import UniverseBuilder
from backend.agents.backtesting_agent import BacktestingAgent
from backend.agents.report_architect import ReportArchitect
from backend.math_engine.performance import PerformanceReport

logger = logging.getLogger(__name__)

llm_provider = get_llm_provider()
embedding_provider = get_embedding_provider()


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
    hypotheses: list
    citations_db: dict
    results_manifest: dict
    universe_result: object


class OctantOrchestrator:
    """Master pipeline coordinator enforcing the 5-agent DAG."""

    def __init__(self):
        self.hypothesis_engine = HypothesisEngine(llm_provider)
        self.literature_agent = LiteratureAgent(llm_provider, embedding_provider)
        self.universe_builder = UniverseBuilder(llm_provider)
        self.backtesting_agent = BacktestingAgent()
        self.report_architect = ReportArchitect(llm_provider)

    async def _check_stop(self, session_id: str):
        """Raise PipelineStoppedError if the frontend cancelled this session."""
        state = await session_manager.get(session_id)
        if state and state.stop_flag.is_set():
            logger.warning("Pipeline halt intercepted for session %s.", session_id)
            raise PipelineStoppedError("Orchestration interrupted by user.")

    async def run_pipeline(
        self, request: PipelineRequest, pulse: PulseEmitter
    ) -> PipelineResult:
        """Execute the full 5-agent quantitative pipeline."""
        session_id = request.session_id

        try:
            # 1. Start
            await self._check_stop(session_id)
            await pulse.emit_status(
                "orchestrator", "active", 1, 5,
                "Initializing", "Starting 5-node pipeline...",
            )

            # 2. Agent 1 — Hypothesis Engine
            await self._check_stop(session_id)
            hypotheses = await self.hypothesis_engine.decompose(
                thesis_str=request.thesis,
                exchanges=request.exchanges,
                sector_filter=request.sector,
                pulse=pulse,
            )
            await session_manager.update(session_id, hypotheses=hypotheses)

            # 3. Agents 2 & 3 — Concurrent Literature + Universe
            await self._check_stop(session_id)
            await pulse.emit_status(
                "orchestrator", "active", 2, 5,
                "Concurrent Research",
                "Agent 2 (Literature) & Agent 3 (Universe) running in parallel",
            )

            literature_task = asyncio.create_task(
                self.literature_agent.research(hypotheses, pulse)
            )
            universe_task = asyncio.create_task(
                self.universe_builder.build(
                    hypotheses, request.exchanges,
                    request.sector, request.time_range, pulse,
                )
            )

            citations_db, universe_result = await asyncio.gather(
                literature_task, universe_task
            )

            # 4. Agent 4 — Backtesting
            await self._check_stop(session_id)
            results_manifest = await self.backtesting_agent.run(
                universe_result, hypotheses, citations_db, pulse
            )
            await session_manager.update(session_id, results_manifest=results_manifest)

            # 5. Agent 5 — Report Architect
            await self._check_stop(session_id)
            pdf_path = await self.report_architect.generate(
                hypotheses, citations_db, results_manifest, pulse
            )
            await session_manager.update(
                session_id, pdf_path=pdf_path, status="complete"
            )

            # Final success
            await pulse.emit_status(
                "orchestrator", "complete", 5, 5,
                "Success", "Pipeline finished.",
            )

            return PipelineResult(
                pdf_path=pdf_path,
                hypotheses=hypotheses,
                citations_db=citations_db,
                results_manifest=results_manifest,
                universe_result=universe_result,
            )

        except PipelineStoppedError as e:
            logger.info("Pipeline %s stopped: %s", session_id, e)
            await pulse.emit_status(
                "orchestrator", "error", 0, 0, "Aborted", "Pipeline stopped by user."
            )
            await session_manager.update(session_id, status="stopped")
            raise

        except Exception as e:
            logger.error(
                "Pipeline error for %s: %s", session_id, e, exc_info=True
            )
            await pulse.emit_status(
                "orchestrator", "error", 0, 0,
                "Pipeline Error", f"Uncaught exception: {str(e)}",
            )
            await session_manager.update(session_id, status="error")
            raise
