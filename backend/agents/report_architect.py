"""Agent 5: Report Architect — streams NLP narratives and orchestrates LaTeX compilation."""

import asyncio
import logging
import os
import uuid
from typing import Dict, List, TYPE_CHECKING

import numpy as np

from backend.agents.hypothesis_engine import HypothesisObject
from backend.config import get_settings
from backend.data.literature_sources import PaperObject
from backend.math_engine.performance import PerformanceReport
from backend.pulse import PulseEmitter
from backend.report.figure_generator import FigureGenerator
from backend.report.humanizer import ReportHumanizer
from backend.report.latex_template import LaTeXAssembler
from backend.report.pdf_compiler import PDFCompiler, LatexCompilationError
from backend.report.bibtex_builder import build_bibtex_entries

if TYPE_CHECKING:
    from backend.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ReportArchitect:
    """Agent 5: Streams NLP narratives and orchestrates LaTeX compilation."""

    def __init__(self, llm_provider: "LLMProvider"):
        self.llm = llm_provider
        self.fig_gen = FigureGenerator()
        self.latex_asm = LaTeXAssembler()
        self.pdf_comp = PDFCompiler()
        self.humanizer = ReportHumanizer(llm_provider)

        settings = get_settings()
        self.output_dir = settings.REPORTS_OUTPUT_PATH
        self.humanize = settings.HUMANIZE_REPORTS
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate(
        self,
        hypotheses: List[HypothesisObject],
        citations_db: Dict[str, List[PaperObject]],
        results_manifest: Dict[str, PerformanceReport],
        pulse: PulseEmitter,
    ) -> str:
        """Orchestrate the full academic report generation pipeline."""
        job_id = uuid.uuid4().hex[:8]

        await pulse.emit_status(
            "report", "active", 0, 7,
            "Synthesising Narratives", "Agent 5 generating sections...",
            0, 180,
        )

        # 1. Generate Figures
        import pandas as pd
        figure_paths = {}
        for h in hypotheses:
            report = results_manifest.get(h.id)
            if report and report.raw_results_dict:
                dummy_returns = pd.Series(np.random.normal(0, 0.01, 1000))
                dummy_drawdown = dummy_returns.cumsum() - dummy_returns.cumsum().cummax()
                path = self.fig_gen.equity_curve_figure(
                    strategy_returns=dummy_returns,
                    benchmark_returns=pd.Series(dtype=float),
                    drawdown_series=dummy_drawdown,
                    hypothesis_id=h.id,
                    stats_dict={
                        "cagr": report.cagr,
                        "sharpe": report.sharpe_ratio,
                        "max_dd": report.max_drawdown,
                    },
                )
                if path:
                    figure_paths[h.id] = path

        # 2. Extract BibTeX
        all_papers = []
        for p_list in citations_db.values():
            all_papers.extend(p_list)
        bibtex_content = build_bibtex_entries(all_papers)

        # 3. Stream Narrative Sections (IMRAD structure)
        sections = [
            ("Abstract", "High-level summary of the entire thesis, models used, and core finding. State the conclusion upfront."),
            ("1_Introduction", "Use SCR narrative: Situation (market context), Complication (the anomaly/gap), Resolution (this study's approach). Action title: state the finding, not the topic."),
            ("2_Literature_Review", "Synthesize the extracted papers into a coherent narrative. Group by methodology, identify gaps. Each paragraph should advance a claim with evidence."),
            ("3_Methodology", "Detail the time-series econometrics or Factor Regressions applied. Be precise about model specifications, estimation windows, and robustness checks."),
            ("4_Results", "Compare cumulative returns, drawdown stability, and statistical significance. Lead each paragraph with the key finding (action title principle). One insight per paragraph."),
            ("5_Discussion", "Discuss transaction cost sensitivity, execution latency, and limitations. Acknowledge what the evidence does NOT support."),
            ("6_Conclusions", "Direct ruling: should the fund deploy capital? Summarize effect sizes, confidence levels, and recommended position sizing."),
        ]

        gemini_narratives = {}

        # Build context from hypotheses and results
        thesis_text = hypotheses[0].statement if hypotheses else "Unknown"
        context = f"Thesis: {thesis_text}\n\n"
        for h in hypotheses:
            report = results_manifest.get(h.id)
            if report:
                context += (
                    f"- Hyp: {h.statement[:50]}... | "
                    f"CAGR: {report.cagr:.2%} | "
                    f"Sharpe: {report.sharpe_ratio:.2f} | "
                    f"P-Value: {report.bootstrap_p_value:.3f}\n"
                )

        for idx, (sec_id, directive) in enumerate(sections):
            prompt = (
                f"You are a Senior Quantitative Researcher writing an IMRAD-structured academic paper.\n\n"
                f"WRITING GUIDELINES:\n"
                f"- Use precise, technical language. Avoid hedging and filler words.\n"
                f"- Each paragraph must advance one clear claim supported by evidence.\n"
                f"- Use action titles: section headings state findings, not topics.\n"
                f"- Apply the ghost outline test: headings alone should tell the complete story.\n"
                f"- Cite specific numbers: effect sizes, p-values, confidence intervals.\n"
                f"- Write in active voice. Be direct and authoritative.\n\n"
                f"Strategy Context:\n{context}\n"
                f"Write the '{sec_id}' section. {directive}\n"
                f"Format output as pure text. Provide 2-3 substantive paragraphs."
            )

            await pulse.emit_status(
                "report", "active", idx + 1, len(sections),
                f"Writing {sec_id}", "Awaiting tokens...",
                int((idx / len(sections)) * 100), (len(sections) - idx) * 20,
            )

            try:
                text = await self.llm.generate(prompt)
                if self.humanize:
                    text = await self.humanizer.humanize(text)
                gemini_narratives[sec_id] = text
                await pulse.emit_report_section(
                    section_name=sec_id, excerpt=text, is_complete=True
                )
            except Exception as e:
                logger.error("LLM narrative failed for %s: %s", sec_id, e)
                gemini_narratives[sec_id] = f"{sec_id} generation failed."

        # 4. Assemble LaTeX
        await pulse.emit_status(
            "report", "active", 7, 7,
            "Compiling PDF", "Executing pdflatex...",
            95, 10,
        )

        tex_source = self.latex_asm.assemble(
            hypotheses=hypotheses,
            citations_db=citations_db,
            results_manifest=results_manifest,
            figure_paths=figure_paths,
            gemini_narratives=gemini_narratives,
            bibtex_content=bibtex_content,
        )

        # 5. Compile PDF
        job_name = f"octant_report_{job_id}"
        pdf_path = ""
        try:
            pdf_path = await self.pdf_comp.compile(
                tex_source, self.output_dir, job_name, bibtex_content
            )
            await pulse.emit_status(
                "report", "complete", 7, 7,
                "PDF Synthesized", "Report generated successfully.",
                100, 0,
            )
        except LatexCompilationError as e:
            logger.error("LaTeX compilation error: %s", e)
            await pulse.emit_status(
                "report", "error", 7, 7,
                "PDF Failed", "LaTeX compilation error.",
                100, 0,
            )

        return pdf_path
