FROM python:3.11-slim

# Install system dependencies including heavy pdflatex (TeXLive)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    biber \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r octantuser && useradd -m -r -g octantuser octantuser

WORKDIR /app

# Upgrade pip and install standard
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend context
COPY . /app/backend
RUN chown -R octantuser:octantuser /app

# Volumes defined in docker-compose, but we ensure output dirs exist
RUN mkdir -p /tmp/octant_reports && chown -R octantuser:octantuser /tmp/octant_reports

USER octantuser

EXPOSE 8000

ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
