"""Application configuration and environment variable management."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables.

    Attributes:
        LLM_PROVIDER: Provider selection (auto/groq/gemini/ollama/anthropic).
        GROQ_API_KEY: Groq API key for free-tier LLM access.
        GEMINI_API_KEY: Google Gemini API key for free-tier LLM access.
        ANTHROPIC_API_KEY: Anthropic API key for paid Claude access.
        OLLAMA_BASE_URL: Base URL for local Ollama instance.
        OLLAMA_MODEL: Ollama model name for LLM inference.
        CORE_API_KEY: CORE API key for academic full-text search (optional).
        EMBEDDING_PROVIDER: Embedding provider (auto/sentence-transformers/ollama).
        EMBEDDING_MODEL: Model name override for embeddings.
        HUMANIZE_REPORTS: Enable AI-pattern detection and rewrite on reports.
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
        HOST: Uvicorn host binding address.
        PORT: Uvicorn port number.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────
    LLM_PROVIDER: str = "auto"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # ── Embedding Provider ────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "auto"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ── API Keys (optional) ──────────────────────────────────────────────
    CORE_API_KEY: Optional[str] = None

    # ── Report Settings ──────────────────────────────────────────────────
    HUMANIZE_REPORTS: bool = True

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
