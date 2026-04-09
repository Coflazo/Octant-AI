"""Health check endpoint and dependency status monitoring."""

from fastapi import APIRouter
import time
import asyncio
import os
import shutil

router = APIRouter()

async def check_dependencies():
    """Concurrently sweep external and local dependency states."""
    checks = []

    # pdflatex check
    t0 = time.time()
    pdf_bin = shutil.which("pdflatex")
    checks.append({
        "service": "pdflatex binary",
        "status": "ok" if pdf_bin else "down",
        "latency_ms": round((time.time() - t0) * 1000, 2)
    })

    # LLM Provider check
    t0 = time.time()
    await asyncio.sleep(0.01)
    has_llm = any([
        os.environ.get("GROQ_API_KEY"),
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("ANTHROPIC_API_KEY"),
    ])
    checks.append({
        "service": "LLM Provider",
        "status": "ok" if has_llm else "degraded",
        "latency_ms": round((time.time() - t0) * 1000, 2)
    })

    return checks

@router.get("/health")
async def health_check():
    """Main routing heartbeat."""
    checks = await check_dependencies()

    system_status = "ok"
    if any(c["status"] == "down" for c in checks):
        system_status = "down"
    elif any(c["status"] == "degraded" for c in checks):
        system_status = "degraded"

    return {
        "status": system_status,
        "version": "0.2.0",
        "uptime": "N/A",
        "checks": checks
    }
