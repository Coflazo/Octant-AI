"""
Octant AI — Report Architect: PDF Compiler

Asynchronously calls pdflatex on the system shell twice to process 
cross-references and bibliographies, parsing stdout for compile flaws.
"""

import asyncio
import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)

class LatexCompilationError(Exception):
    """Raised when PDFLaTeX exits with a non-zero exit code due to LaTeX syntax faults."""
    pass

class PDFCompiler:
    """Manages the lifecycle of standard LaTeX PDF generation."""

    def __init__(self):
        # Locate exact pdflatex path if necessary, but assume it's in global PATH for now
        self.compiler_bin = "pdflatex"
        self.biber_bin = "biber"

    async def compile(self, tex_content: str, output_dir: str, job_name: str, bibtex_content: str) -> str:
        """Writes .tex and .bib to disk and compiles twice.
        
        Args:
            tex_content: The raw LaTeX string block.
            output_dir: Folder to dump artifacts.
            job_name: Basename of the generated files.
            bibtex_content: The raw .bib string block from bibtex_builder.
            
        Returns:
            Absolute filepath to the generated PDF.
        """
        os.makedirs(output_dir, exist_ok=True)
        tex_path = os.path.join(output_dir, f"{job_name}.tex")
        bib_path = os.path.join(output_dir, "references.bib")
        pdf_path = os.path.join(output_dir, f"{job_name}.pdf")

        # 1. & 2. Write artifact source files
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
            
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(bibtex_content)

        # 3. Compilations
        # First Pass
        await self._run_latex(output_dir, job_name)
        
        # Biber Pass (bibliography linking)
        await self._run_biber(output_dir, job_name)
        
        # Second Pass (embed cross-refs)
        await self._run_latex(output_dir, job_name)
        
        if not os.path.exists(pdf_path):
            raise LatexCompilationError(f"Compilation finished but {pdf_path} not found.")

        return pdf_path

    async def _run_latex(self, output_dir: str, job_name: str) -> None:
        cmd = [
            self.compiler_bin,
            "-interaction=nonstopmode",
            f"-output-directory={output_dir}",
            f"{job_name}.tex"
        ]
        await self._execute(cmd, output_dir)
        
    async def _run_biber(self, output_dir: str, job_name: str) -> None:
        cmd = [self.biber_bin, job_name]
        try:
            # Biber failing doesn't necessarily crash latex in warning state
            await self._execute(cmd, output_dir)
        except LatexCompilationError as e:
            logger.warning("Biber compilation threw warnings/errors, LaTeX may still build: %s", e)

    async def _execute(self, cmd: list, cwd: str) -> None:
        logger.debug("Executing shell: %s", " ".join(cmd))
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stdout_str = stdout.decode(errors="ignore")
                # Attempt to extract LaTeX error
                err_lines = [line for line in stdout_str.split('\n') if line.startswith('!') or "Error" in line]
                extracted = "\n".join(err_lines[:5]) if err_lines else stdout_str[-500:]
                
                raise LatexCompilationError(f"Command {' '.join(cmd)} failed (code {process.returncode}). Output: {extracted}")
        except FileNotFoundError:
            raise LatexCompilationError(f"Command '{cmd[0]}' not found. Is TeXLive/pdflatex installed?")
