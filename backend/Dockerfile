FROM python:3.11-slim

# ── Install system dependencies (LaTeX for PDF compilation) ────
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-full \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user ──────────────────────────────────────
RUN groupadd -r octant && useradd -r -g octant -m octant

WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# ── Install Playwright browsers ───────────────────────────────
RUN playwright install --with-deps chromium

# ── Copy application code ─────────────────────────────────────
COPY backend/ /app/backend/
COPY latex_templates/ /app/latex_templates/

# ── Create required directories ───────────────────────────────
RUN mkdir -p /app/reports /app/data/chromadb /app/data/ff5_cache && \
    chown -R octant:octant /app

USER octant

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
