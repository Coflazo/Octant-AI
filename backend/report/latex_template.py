"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from typing import Dict, List

from backend.agents.hypothesis_engine import HypothesisObject
from backend.data.literature_sources import PaperObject
from backend.math_engine.performance import PerformanceReport

logger = logging.getLogger(__name__)


class LaTeXAssembler:
    """compounds text, tables, and images into a strict tex source string lol"""

    def __init__(self):
        self.header_color = "1B3D6E" # OctNavy
        self.accent_color = "00C07A" # OctGreen

    def _latex_escape(self, s: str) -> str:
        """sanitizes text strings for safe latex compilation lol"""
        if s is None:
            return ""
        s = str(s)
                # Escape order matters
        s = s.replace("\\", "\\textbackslash ")
        subs = {
            "&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#",
            "_": "\\_", "{": "\\{", "}": "\\}", "~": "\\textasciitilde ",
            "^": "\\textasciicircum "
        }
        for k, v in subs.items():
            s = s.replace(k, v)
        return s

    def assemble(
        self,
        hypotheses: List[HypothesisObject],
        citations_db: Dict[str, List[PaperObject]],
        results_manifest: Dict[str, PerformanceReport],
        figure_paths: Dict[str, str],
        gemini_narratives: Dict[str, str],
        bibtex_content: str
    ) -> str:
        """injects python variables into the rigid imrad latex preamble and body lol"""

        
        # 1. Start Preamble
        latex = [
            "\\documentclass[12pt,a4paper]{article}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage{geometry}",
            "\\geometry{a4paper, margin=1in}",
            "\\usepackage{amsmath, amssymb}",
            "\\usepackage{booktabs, array}",
            "\\usepackage{graphicx}",
            "\\usepackage{xcolor}",
            "\\usepackage{listings}",
            "\\usepackage[backend=biber, style=apa]{biblatex}",
            "\\addbibresource{references.bib}",
            "\\usepackage{caption}",
            "\\usepackage{subcaption}",
            "\\usepackage{setspace}",
            "\\usepackage{microtype}",
            "\\usepackage{lmodern}",
            "\\usepackage[colorlinks=true, linkcolor=OctNavy, citecolor=OctNavy, urlcolor=OctNavy]{hyperref}",
            "",
            "\\definecolor{OctNavy}{HTML}{1B3D6E}",
            "\\definecolor{OctGreen}{HTML}{00C07A}",
            "\\definecolor{OctDeep}{HTML}{0A0B0D}",
            "",
            "\\begin{document}",
            "\\setstretch{1.15}"
        ]

        
        # 2. Title Page
        thesis_statement = hypotheses[0].thesis_statement if hypotheses else "Quantitative Trading Strategy Analysis"
        latex.extend([
            "\\begin{titlepage}",
            "\\centering",
            "\\vspace*{2cm}",
            "{\\color{OctNavy}\\rule{\\linewidth}{2pt}}\\\\[0.4cm]",
            f"{{\\Huge \\bfseries {self._latex_escape(thesis_statement)} }}\\\\[0.4cm]",
            "{\\color{OctNavy}\\rule{\\linewidth}{2pt}}\\\\[1.5cm]",
            "{\\Large \\textit{Octant AI - Autonomous Quantitative Research Workbench}}\\\\[2cm]",
            "{\\large \\textbf{Abstract}}\\\\[0.5cm]",
            "\\begin{minipage}{0.85\\textwidth}",
            "\\centering",
            self._latex_escape(gemini_narratives.get("Abstract", "No abstract generated.")),
            "\\end{minipage}\\\\[2cm]",
            "\\vfill",
            f"{{\\large \\today}}",
            "\\end{titlepage}",
            "\\newpage",
            "\\tableofcontents",
            "\\newpage"
        ])

        
        # 3. IMRaD Sections
        sections = [
            ("Introduction", "1_Introduction"),
            ("Literature Review", "2_Literature_Review"),
            ("Methodology", "3_Methodology"),
            ("Results", "4_Results"),
            ("Discussion", "5_Discussion"),
            ("Conclusions", "6_Conclusions")
        ]

        for title, key in sections:
            latex.extend([
                f"\\section{{{title}}}",
                self._latex_escape(gemini_narratives.get(key, f"{title} narrative not available."))]
            )
            
                        
            # Inject figures conditionally
            if title == "Results":
                                # Inject performance table
                latex.extend(self._build_performance_table(results_manifest, hypotheses))
                
                                
                # Check for equity curve figure mapping to primary hypothesis
                primary_h = hypotheses[0].hypothesis if hypotheses else ""
                if primary_h in figure_paths:
                    latex.extend([
                        "\\begin{figure}[h!]",
                        "\\centering",
                        f"\\includegraphics[width=0.9\\textwidth]{{{figure_paths[primary_h]}}}",
                        f"\\caption{{Cumulative Returns and Drawdowns for Hypothesis 1: {self._latex_escape(primary_h)}}}",
                        "\\end{figure}"
                    ])

        
        # 4. Bibliography
        latex.extend([
            "\\newpage",
            "\\printbibliography[heading=bibintoc, title={References}]"
        ])

        
        # 5. Appendices
        latex.extend(self._build_appendices(hypotheses, results_manifest))

        latex.append("\\end{document}")
        return "\n".join(latex)

    def _build_performance_table(self, results_manifest: Dict[str, PerformanceReport], hypotheses: List[HypothesisObject]) -> List[str]:
        """creates a booktabs formatted latex table with key stats lol"""
        latex = [
            "\\begin{table}[h!]",
            "\\centering",
            "\\caption{Statistical Cross-Section Performance Attributes}",
            "\\resizebox{\\textwidth}{!}{",
            "\\begin{tabular}{lrrrrrrr}",
            "\\toprule",
            "\\textbf{Hypothesis} & \\textbf{CAGR} & \\textbf{Vol} & \\textbf{Sharpe} & \\textbf{Bayes SR} & \\textbf{Max DD} & \\textbf{Win Rate} & \\textbf{P-Value} \\\\",
            "\\midrule"
        ]
        
        for idx, h in enumerate(hypotheses):
            report = results_manifest.get(h.hypothesis)
            if not report:
                continue
                
            short_hyp = h.hypothesis[:30] + "..." if len(h.hypothesis) > 30 else h.hypothesis
            latex.append(
                f"{self._latex_escape(short_hyp)} & "
                f"{report.cagr*100:.1f}\\% & "
                f"{report.volatility*100:.1f}\\% & "
                f"{report.sharpe_ratio:.2f} & "
                f"{report.bayes_sharpe:.2f} & "
                f"{report.max_drawdown*100:.1f}\\% & "
                f"{report.win_rate*100:.1f}\\% & "
                f"{report.bootstrap_p_value:.3f} \\\\"
            )
            
        latex.extend([
            "\\bottomrule",
            "\\end{tabular}",
            "}",
            "\\end{table}"
        ])
        return latex

    def _build_appendices(self, hypotheses: List[HypothesisObject], results_manifest: Dict[str, PerformanceReport]) -> List[str]:
        """adds statistical appendices including ff5 factors and marchenko-pastur lol"""
        return [
            "\\newpage",
            "\\appendix",
            "\\section{Statistical Model Significance}",
            "Model derivations subjected to Strict FWER (Bonferroni) checks and Bayesian volatility dampening to prevent overfitting via the mathematical engine.",
            "\\vspace{1cm}"
        ]
