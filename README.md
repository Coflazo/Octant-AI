<div align="center">
  <img src="assets/Octant_Logo.png" alt="Octant AI Logo" width="180" />
  <h1>Octant AI</h1>
  <p><strong>Open-source autonomous quantitative research pipeline</strong></p>
</div>

[![Python](https://img.shields.io/badge/Python-3.11+-1A6FE8?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-0F8F72?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-6D4FD8?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-1A6FE8?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-00C07A?style=flat-square)](LICENSE)

Octant AI turns a thesis into a quant research workflow with a 5-agent backend, a live PULSE WebSocket stream, and downloadable PDF reports.

## Table of Contents

- [What Octant AI does](#what-octant-ai-does)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick start (local)](#quick-start-local)
- [Quick start (docker)](#quick-start-docker)
- [Configuration](#configuration)
- [API and WebSocket reference](#api-and-websocket-reference)
- [Testing and validation](#testing-and-validation)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)
- [License](#license)

## What Octant AI does

Given a thesis, Octant AI:

1. Decomposes it into testable hypotheses.
2. Runs literature and universe-building stages concurrently.
3. Backtests hypotheses with math/portfolio modules.
4. Generates a report-ready output package and PDF.
5. Streams progress and artifacts to the frontend via PULSE.

## Architecture

```text
Thesis
  │
  ├─ Agent 1: Hypothesis Engine
  │
  ├─ Agent 2: Literature Agent ─┐
  └─ Agent 3: Universe Builder ─┤ (parallel)
                                │
                          Agent 4: Backtesting
                                │
                          Agent 5: Report Architect
                                │
                           PDF + artifacts
```

The orchestrator runs this DAG asynchronously and reports status over `ws://<host>:8000/ws/{session_id}`.

## Tech stack

- **Backend:** FastAPI, Uvicorn, Pydantic Settings, asyncio orchestration
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS
- **Quant/Data:** NumPy, SciPy, statsmodels, scikit-learn, vectorbt, yfinance, arch
- **Research/Storage:** ChromaDB, web/literature connectors
- **Report generation:** Jinja2 + LaTeX (`pdflatex`)
- **LLM providers:** Groq, Gemini, Ollama, Anthropic (auto-cascade or forced provider)

## Prerequisites

- Python **3.11+**
- Node.js **18+**
- A TeX distribution with `pdflatex` available on `PATH`
- At least one configured LLM provider (`GROQ_API_KEY`, `GEMINI_API_KEY`, local Ollama, or `ANTHROPIC_API_KEY`)

## Quick start (local)

```bash
git clone https://github.com/Coflazo/Octant-AI.git
cd Octant-AI

cp .env.example .env
# Edit .env and set your provider credentials

# Backend
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Local URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Quick start (docker)

```bash
cp .env.example .env
docker-compose up --build
```

Docker URLs:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Configuration

Main environment settings live in `.env` (template: `.env.example`):

- `LLM_PROVIDER=auto|groq|gemini|ollama|anthropic`
- `GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
- `HUMANIZE_REPORTS=true|false`
- `CHROMA_DB_PATH`, `REPORTS_OUTPUT_PATH`
- `CORS_ORIGINS`, `HOST`, `PORT`

## API and WebSocket reference

### REST endpoints

- `GET /health` — service/dependency status
- `POST /api/pipeline/start` — start a pipeline run
- `POST /api/pipeline/stop/{session_id}` — stop a running session
- `GET /api/reports/` — list generated report PDFs
- `GET /api/reports/{filename}` — download one report

### WebSocket

- `WS /ws/{session_id}`
- Event `payload_type` values:
  - `status`
  - `hypothesis_card`
  - `citation_card`
  - `ticker_card`
  - `metric_result`
  - `report_section`
  - `error`

## Testing and validation

Backend tests are located in `backend/tests`:

```bash
python -m pytest backend/tests -q
```

Frontend scripts:

```bash
cd frontend
npm run lint
npm run build
```

## Project structure

```text
.
├── backend/
│   ├── agents/
│   ├── data/
│   ├── math_engine/
│   ├── report/
│   ├── routers/
│   ├── tests/
│   └── main.py
├── frontend/
│   ├── src/
│   └── package.json
├── assets/
├── docker-compose.yml
└── .env.example
```

## Known limitations

- Report generation depends on local/system LaTeX availability.
- LLM throughput and latency depend on provider limits and quotas.
- Data quality/coverage depends on external data sources.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
