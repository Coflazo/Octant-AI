"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

class OctantBaseError(Exception):
    """root application exception conveying recovery context lol"""
    def __init__(self, message: str, recovery_action: str = "Contact support or restart the pipeline."):
        super().__init__(message)
        self.recovery_action = recovery_action


class HypothesisDecompositionError(OctantBaseError):
    def __init__(self, message="Gemini failed to translate NLP into distinct hypotheses."):
        super().__init__(message, recovery_action="Try simplifying your trading thesis to fewer, distinct logical predicates.")


class LiteratureSearchError(OctantBaseError):
    def __init__(self, message="Literature vector retrieval stalled or returned critical nulls."):
        super().__init__(message, recovery_action="Verify network connection to Scholar APIs or decrease hypothesis complexity.")


class UniverseTooSmallError(OctantBaseError):
    def __init__(self, message="Asset pre-filtering yielded an insufficient matrix pool."):
        super().__init__(message, recovery_action="Lower market cap restrictions or expand chosen target exchanges.")


class GARCHConvergenceError(OctantBaseError):
    def __init__(self, message="Maximum Likelihood gradients failed to converge during heteroskedastic fitting."):
        super().__init__(message, recovery_action="Check specific asset logs. Asset distribution may be excessively leptokurtic.")


class LatexCompilationError(OctantBaseError):
    def __init__(self, message="The pdflatex binary threw non-zero exit codes formatting strings."):
        super().__init__(message, recovery_action="Ensure texlive-full is installed or check system memory limits.")


class PipelineStoppedError(OctantBaseError):
    def __init__(self, message="The underlying orchestrator task was deliberately cancelled."):
        super().__init__(message, recovery_action="None required. Wait for the engine to spin down completely.")


class Reson8TranscriptionError(OctantBaseError):
    def __init__(self, message="Binary voice chunks could not be reconciled by Reson8."):
        super().__init__(message, recovery_action="Check local microphone settings and ensure chunks are valid raw formats.")


class FalAPIError(OctantBaseError):
    def __init__(self, message="The fal.ai sparkline generative endpoint timed out."):
        super().__init__(message, recovery_action="Degraded state active. Sparklines will not be rendered on universe cards.")
