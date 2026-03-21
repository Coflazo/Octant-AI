# 🧭 Octant AI

**Autonomous Quantitative Research Workbench**

Octant AI is a privacy-first, autonomous quantitative research platform. Input a natural-language investment thesis — typed or spoken via Reson8 voice API — and the system will:

1. **Decompose** it into 4–8 testable sub-hypotheses (Gemini 2.5 Pro)
2. **Research** academic literature from 6 sources (arXiv, Semantic Scholar, OpenAlex, SSRN, CORE, Modern Finance)
3. **Build** a qualifying equity universe across 10 global exchanges with live data (yfinance + OpenBB)
4. **Backtest** with dual engines (VectorBT + custom explainable) and 18 mathematical models
5. **Compile** a publication-quality IMRaD-format PDF report typeset in LaTeX

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React 18 + TypeScript + Tailwind            │
│  ┌──────────┐  ┌───────────────────────────┐  ┌──────────────┐ │
│  │ Left     │  │ Center Panel              │  │ Right Panel  │ │
│  │ Panel    │  │ Pipeline · Hypotheses ·   │  │ Report ·     │ │
│  │ Voice ·  │  │ Citations · Tickers ·     │  │ Metrics ·    │ │
│  │ Thesis · │  │ Results Matrix · Log      │  │ Download PDF │ │
│  │ Controls │  │                           │  │              │ │
│  └──────────┘  └───────────────────────────┘  └──────────────┘ │
│                         │ PULSE WebSocket                      │
├─────────────────────────┼──────────────────────────────────────┤
│                    FastAPI Backend                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Math Engine    │ │
│  │ Hypothe- │  │ Litera-  │  │ Universe │  │ ARIMA · GARCH  │ │
│  │ sis      │→ │ ture     │→ │ Builder  │→ │ HMM · BS · OU  │ │
│  │ Engine   │  │ Agent    │  │          │  │ MVO · PCA · MC │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘ │
│       │              │            │               │            │
│       │   ┌──────────┴────────┐   │    ┌──────────┴─────────┐ │
│       │   │ Agent 4: Backtest │←──┘    │ Agent 5: Report    │ │
│       │   │ VectorBT + Custom │───────→│ LaTeX → PDF        │ │
│       │   └───────────────────┘        └────────────────────┘ │
└───────┼───────────────────────────────────────────────────────┘
        │
   Dust.tt Orchestrator
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn, asyncio |
| Orchestration | Dust.tt |
| Frontend | React 18, TypeScript, Tailwind CSS |
| Voice Input | Reson8 (console.reson8.dev) |
| LLM | Google Gemini 2.5 Pro + Gemini Flash |
| Price Data | yfinance |
| Fundamentals | OpenBB SDK |
| Chart Images | fal.ai |
| Backtesting | VectorBT + custom Python engine |
| Sentiment | WSBTrends (Go) + Playwright scraper |
| Math | NumPy, SciPy, statsmodels, arch, scikit-learn |
| Report | LaTeX (pdflatex) + matplotlib |
| Real-time | WebSocket (PULSE protocol) |
| Vector DB | ChromaDB |

## Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **pdflatex** (TeX Live or MacTeX) for report compilation
- API keys: Google Gemini, Reson8, fal.ai, Dust.tt, OpenBB

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/AtillaErsezen/Octant-AI.git
cd Octant-AI
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cd ..
```

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run

```bash
# Terminal 1 — Backend
cd backend && uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` in your browser.

### Docker alternative

```bash
docker-compose up --build
```

## Demo Thesis Examples

- "Test momentum reversal in small-cap energy stocks when VIX spikes above 30"
- "Evaluate mean reversion in pairs of European bank stocks using cointegration"
- "Analyse whether Reddit sentiment predicts abnormal returns in meme stocks"

## Project Structure

```
octant-ai/
├── backend/
│   ├── main.py                    # FastAPI app + WebSocket
│   ├── config.py                  # Central configuration
│   ├── pulse.py                   # PULSE WebSocket emitter
│   ├── agents/                    # 5 pipeline agents
│   ├── math_engine/               # 18 mathematical models
│   ├── data/                      # Data fetchers + scrapers
│   ├── sentiment/                 # Signal construction
│   ├── report/                    # LaTeX + matplotlib + PDF
│   ├── voice/                     # Reson8 integration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/            # Left/Center/Right panels
│   │   ├── hooks/                 # WebSocket + voice hooks
│   │   ├── types/pulse.ts         # PULSE protocol types
│   │   └── utils/formatters.ts
│   ├── package.json
│   └── vite.config.ts
├── reports/                       # Generated PDF output
├── data/                          # ChromaDB + cached data
├── latex_templates/               # LaTeX .tex templates
├── docker-compose.yml
└── .env.example
```

## License

Proprietary — all rights reserved.
