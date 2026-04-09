<div align="center">
  <img src="assets/Octant_Logo.png" alt="Octant AI Logo" width="200"/>
  <h1>Octant AI</h1>
  <h3>Open-Source Autonomous Quantitative Research Pipeline</h3>

<br/>

*From an investment thesis to a publication-quality quantitative research PDF — fully open-source.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-1A6FE8?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-6D4FD8?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-0F8F72?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-1A6FE8?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-0F8F72?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![LaTeX](https://img.shields.io/badge/Report-LaTeX_PDF-C4482A?style=flat-square&logo=latex&logoColor=white)](https://www.latex-project.org)
[![License](https://img.shields.io/badge/License-MIT-00C07A?style=flat-square)](LICENSE)

<br/>

<table>
<tr>
<td align="center"><b>5 Agents</b><br/><sub>Fully autonomous pipeline</sub></td>
<td align="center"><b>18 Math Models</b><br/><sub>GARCH, B-S, PCA, MVO</sub></td>
<td align="center"><b>6 Academic Sources</b><br/><sub>arXiv, Semantic Scholar, OpenAlex, SSRN, CORE, Modern Finance</sub></td>
<td align="center"><b>50,000 MC Paths</b><br/><sub>VaR, ES, ruin probability</sub></td>
<td align="center"><b>IMRaD PDF</b><br/><sub>Publication-grade LaTeX report</sub></td>
</tr>
</table>

</div>

---

## What Is Octant AI?

Octant AI is an **open-source, autonomous quantitative research workbench**. A quant researcher types an investment thesis and the system:

1. **Decomposes** it into 4-8 independently testable sub-hypotheses
2. **Retrieves and analyses** academic literature from 6 sources (arXiv, Semantic Scholar, OpenAlex, SSRN, CORE, Modern Finance)
3. **Builds a qualifying equity universe** across selectable global exchanges with liquidity screening
4. **Downloads and cleans** 20+ years of historical price data with corporate action adjustments
5. **Scrapes social sentiment** from Reddit (WallStreetBets + 5 other communities) via Playwright + WSBTrends
6. **Runs dual backtests** — VectorBT for speed, custom engine for explainability — with 18 mathematical models per hypothesis
7. **Compiles a publication-quality PDF** report typeset in LaTeX with matplotlib figures, BibTeX citations, and full statistical appendices

Every stage streams real-time status updates to the React frontend via the **PULSE** WebSocket protocol.

---

## LLM Provider Cascade

Octant AI uses a 3-tier LLM fallback system. No paid API is required.

| Tier | Provider | Model | Cost | Setup |
|------|----------|-------|------|-------|
| 1 | **Groq** | llama-3.3-70b-versatile | Free (30 req/min) | Set `GROQ_API_KEY` |
| 1 | **Gemini** | gemini-2.0-flash | Free (15 req/min) | Set `GEMINI_API_KEY` |
| 2 | **Ollama** | llama3.2 / mistral | Free (local) | Install Ollama |
| 3 | **Anthropic** | claude-sonnet | Paid | Set `ANTHROPIC_API_KEY` |

Auto-detection cascade: checks `GROQ_API_KEY` -> `GEMINI_API_KEY` -> pings Ollama -> `ANTHROPIC_API_KEY`.

Override with `LLM_PROVIDER=groq|gemini|ollama|anthropic` in your `.env`.

### Embeddings

Local embeddings via `sentence-transformers` (all-MiniLM-L6-v2, 384-dim) with Ollama fallback. No paid embedding API required.

---

## Installation

### Prerequisites

- Python 3.11+ and Node.js 18+
- `texlive-full` (for pdflatex)
- At least one LLM provider configured (Groq free tier recommended)

### Quick Start

```bash
git clone https://github.com/Coflazo/Octant-AI.git
cd Octant-AI

# Configure your LLM provider
cp .env.example .env
# Edit .env — set at least GROQ_API_KEY

# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### With Docker

```bash
git clone https://github.com/Coflazo/Octant-AI.git
cd Octant-AI
cp .env.example .env
# Edit .env with your API keys
docker-compose up --build
```

Frontend: `http://localhost:3000` | Backend API: `http://localhost:8000` | API docs: `http://localhost:8000/docs`

---

## Usage

1. Open `http://localhost:3000`
2. Type your investment thesis in the text area
3. Select target exchanges (NYSE, NASDAQ, LSE, etc.)
4. Set your backtest time range (default: 10 years)
5. Optionally set a sector filter
6. Press **Run**
7. Watch the pipeline execute live in the center panel
8. Download your PDF report from the right panel when complete

### Example Theses

```
"Test a mean-reversion strategy on NVDA that enters when RSI(14) < 30
and Z-Score(Vol) > 2. Benchmark against QQQ."

"Test whether low short-interest momentum stocks in the energy sector
outperform during rising real yield environments."

"Does implied volatility skew in the technology sector predict
subsequent equity returns over a 10-day horizon?"
```

---

## Architecture

### 5-Agent Pipeline

```
Thesis Input -> Agent 1 (Hypothesis Engine) -> [4-8 sub-hypotheses]
                                                    |
                                    +---------+-----+-------+
                                    |                       |
                              Agent 2                 Agent 3
                          (Literature)           (Universe Builder)
                                    |                       |
                                    +---------+-----+-------+
                                                    |
                                              Agent 4
                                           (Backtesting)
                                                    |
                                              Agent 5
                                         (Report Architect)
                                                    |
                                              PDF Report
```

### Technology Stack

| Layer | Components |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, WebSocket PULSE client |
| **API** | FastAPI, Uvicorn ASGI, PULSE WebSocket protocol |
| **LLM** | Groq / Gemini / Ollama / Anthropic (auto-cascade) |
| **Math** | NumPy, SciPy, statsmodels, scikit-learn, VectorBT, arch |
| **Data** | yfinance, Playwright (Reddit), WSBTrends, ChromaDB |
| **Report** | pdflatex (2-pass), matplotlib (300 DPI), BibTeX, Jinja2 |

---

## Mathematical Model Registry

| Category | Models |
|----------|--------|
| **Time-Series** | ADF stationarity, ARIMA (AIC), GARCH/GJR-GARCH/EGARCH, HMM (2-state Baum-Welch), FFT + Wavelet |
| **Cross-Sectional** | OLS (Newey-West SE), Rolling regression alpha, PCA + Marchenko-Pastur, Black-Scholes Greeks, Ornstein-Uhlenbeck |
| **Portfolio** | GBM + Merton jump-diffusion, MVO (Ledoit-Wolf shrinkage), Bayesian posterior Sharpe, Bootstrap hypothesis tests, Monte Carlo (50k paths) |
| **Risk** | Sharpe/Sortino/Omega ratios, VaR/ES (95%/99%), Max drawdown + Calmar, Factor alpha (Bonferroni p-val), Vol surface Greeks |

---

## The PULSE WebSocket Protocol

Real-time event streaming from backend agents to the React frontend.

**Event types:** `status`, `hypothesis_card`, `citation_card`, `ticker_card`, `metric_result`, `report_section`, `error`

Each event contains: `agent`, `status`, `progress` (step/total/percent), `payload_type`, `payload`, `message` (title/subtitle), `timestamp`.

Connect: `ws://localhost:8000/ws/{session_id}`

---

## Report Features

- **IMRAD structure**: Abstract, Introduction, Literature Review, Methodology, Results, Discussion, Conclusions
- **Humanizer**: AI-pattern detection + LLM rewrite for natural academic prose
- **Scientific writing skills**: SCR narrative spine, action titles, one-insight-per-section
- **LaTeX compilation**: 2-pass pdflatex with BibTeX
- **Figures**: matplotlib equity curves, vol surfaces, return distributions, correlation clustermaps, rolling Sharpe, PCA eigenvalue spectra

---

## Performance Metrics (18 Total)

CAGR, Annualised Volatility, Sharpe Ratio, Sortino Ratio, Information Ratio, Omega Ratio, Max Drawdown, Calmar Ratio, VaR (95%), Expected Shortfall (99%), Skewness, Excess Kurtosis, Bootstrap p-value, Bayesian Posterior Sharpe, Fama-French 5-Factor Alpha, Factor Significance (t-stat), Win Rate, Profit Factor.

---

## Known Limitations

| Limitation | Mitigation |
|------------|------------|
| Survivorship bias (yfinance) | Correction factor 0.5-2.0%/yr by cap tier |
| Data snooping (N hypotheses) | Bonferroni + BH corrections; t-stat threshold 3.0 |
| Options data depth | Current-date IV surface via Yahoo Finance |
| LLM rate limits | Auto-cascade to next provider on failure |
| No real-time data | Historical backtesting only |

---

## License

MIT License. See [LICENSE](LICENSE) for details.
