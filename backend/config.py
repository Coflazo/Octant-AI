"""
Octant AI — Central Configuration.

All environment variables are accessed via the Settings object defined here.
No hardcoded secrets or paths anywhere else in the codebase. Uses Pydantic
BaseSettings to load from a .env file with type validation and defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables.

    Every external API key, file path, and tuneable parameter for the entire
    Octant AI pipeline is centralised in this single class. The .env file is
    the canonical source; this class validates types and provides defaults.

    Attributes:
        GEMINI_API_KEY: Google Gemini API key for LLM calls (reasoning + throughput).
        RESON8_API_KEY: Reson8 speech-to-text API key from console.reson8.dev.
        FAL_API_KEY: fal.ai API key for chart image generation.
        DUST_API_KEY: Dust.tt API key for agent workflow orchestration.
        OPENBB_TOKEN: OpenBB SDK personal access token for fundamentals data.
        CORE_API_KEY: CORE API key for academic full-text search (optional).
        CHROMA_DB_PATH: Local filesystem path for ChromaDB persistent storage.
        REPORTS_OUTPUT_PATH: Directory where compiled PDF reports are written.
        LATEX_TEMPLATES_PATH: Directory containing LaTeX .tex template files.
        LOG_LEVEL: Python logging level string (DEBUG, INFO, WARNING, ERROR).
        CORS_ORIGINS: Comma-separated list of allowed CORS origins for FastAPI.
        REDIS_URL: Optional Redis connection URL for production session storage.
        WSBT_BINARY_PATH: Filesystem path to the compiled WSBTrends Go binary.
        MAX_UNIVERSE_SIZE: Maximum number of tickers in the equity universe.
        BACKTEST_DEFAULT_PERIOD_YEARS: Default lookback period for backtests.
        MONTE_CARLO_PATHS: Number of Monte Carlo simulation paths to generate.
        GEMINI_REASONING_MODEL: Gemini model name for reasoning tasks.
        GEMINI_FLASH_MODEL: Gemini model name for high-throughput extraction.
        GEMINI_EMBEDDING_MODEL: Gemini model name for text embeddings.
        RESON8_BASE_URL: Base URL for the Reson8 API.
        FAL_BASE_URL: Base URL for the fal.ai API.
        HOST: Uvicorn host binding address.
        PORT: Uvicorn port number.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── API Keys ───────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    RESON8_API_KEY: str = ""
    FAL_API_KEY: str = ""
    DUST_API_KEY: str = ""
    OPENBB_TOKEN: str = ""
    CORE_API_KEY: Optional[str] = None

    # ── File Paths ─────────────────────────────────────────────────────────
    CHROMA_DB_PATH: str = "./data/chromadb"
    REPORTS_OUTPUT_PATH: str = "./reports"
    LATEX_TEMPLATES_PATH: str = "./latex_templates"
    WSBT_BINARY_PATH: str = "./bin/wsbt"

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Server ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    REDIS_URL: Optional[str] = None
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Pipeline Tuneables ─────────────────────────────────────────────────
    MAX_UNIVERSE_SIZE: int = 200
    BACKTEST_DEFAULT_PERIOD_YEARS: int = 10
    MONTE_CARLO_PATHS: int = 50000

    # ── Model Names ────────────────────────────────────────────────────────
    GEMINI_REASONING_MODEL: str = "gemini-2.5-pro-preview-05-06"
    GEMINI_FLASH_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # ── External Service URLs ──────────────────────────────────────────────
    RESON8_BASE_URL: str = "https://api.reson8.dev"
    FAL_BASE_URL: str = "https://api.fal.ai"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list.

        Returns:
            List of origin URL strings for FastAPI CORSMiddleware.
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    The lru_cache ensures the .env file is read only once and the same
    Settings object is reused across the entire application lifetime.

    Returns:
        The application Settings object.
    """
    return Settings()
