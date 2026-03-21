<div align="center">
  <img src="assets/Octant_Logo.png" alt="Octant AI Logo" width="200"/>
  <h1>Octant AI</h1>
  <p><strong>Autonomous Quantitative Research Workbench</strong></p>
</div>

Octant AI is a strict, end-to-end framework translating natural language academic theses into rigorous statistical models. It acts as a five-stage orchestrator, leveraging WebRTC Voice transcription (Reson8), Large Language Models (Gemini Pro), and mathematical execution grids to synthesize institutional-grade LaTeX PDF reports over custom asset universes.

---

## 🏗 System Architecture

```text
               +-------------------------------------------------+
               |             React 18 / Tailwind CSS             |
               | (LeftPanel Config, Center Dashboard, Right PDF) |
               +-----------------------+-------------------------+
                                       | WebSocket (PULSE Events)
+--------------------------------------v---------------------------------------+
|                       OCTANT ORCHESTRATOR (Python 3.11)                      |
|                                                                              |
|  [Agent 1: Hypothesis] ---> NLP to Strict Mathematical Execution Bounds      |
|                                                                              |
|  [Agent 2: Literature] ---> Fork 1: Semantic Search & Citation Validation    |
|             |                                                                |
|  [Agent 3: Universe]   ---> Fork 2: Asset Pre-filter, WSB Trends, Scrapers   |
|                                                                              |
|  [Agent 4: Engine]     ---> Math: Marchenko-Pastur PCA, GARCH(1,1),          |
|                             Nearest-PD Higham, Bayes-Adjusted Sharpe         |
|                                                                              |
|  [Agent 5: Architect]  ---> Generative IMRaD LaTeX Compilation to PDF        |
+------------------------------------------------------------------------------+
```

## 📋 Prerequisites

- **Python**: `3.11+`
- **Node.js**: `18+` (Alpine target available)
- **pdflatex**: `texlive-full` distribution for PDF compilation.
- **Docker**: For sandboxed execution (Optional but Recommended).

### API Keys
Provide standard HTTP keys within a root directory `.env` file:
```env
GEMINI_API_KEY="sk-xxx"   # For Google AI Studio access
RESON8_API_KEY="r8-xxx"   # For binary Audio WebRTC transcription bounds
FAL_API_KEY="fal-xxx"     # For Sparkline generation endpoints
```

## 🚀 Installation

### 1. Standard Bare-Metal
```bash
# Clone Repository
git clone https://github.com/AtillaErsezen/Octant-AI.git
cd Octant-AI

# Setup Python Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run FastAPI OS Worker
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Setup React Frontend (Separate Terminal)
cd frontend
npm install
npm run dev
```

### 2. Docker Compose Isolation
Octant AI scales implicitly with concurrent Dust implementations leveraging native Docker images:
```bash
docker-compose up --build
```
> The React Dashboard triggers on `http://localhost:3000` while `FastAPI` scales background threads over `:8000`.

### 3. Dust Orchestration Setup
To execute the backend application exclusively as a Dust.tt autonomous agent workflow:
1. Initialize a new Dust App inside your Dust.tt workspace.
2. Import the included `dust_workflow.json` blueprint into the Actions visual graph.
3. Ensure the `A1` trigger webhook targets your active `POST /api/pipeline/start` FastAPI endpoint bounds.

## 🎤 Demo Thesis Example

> _"Given extreme monetary tightening phases, heavily shorted components in the consumer discretionary sector exhibit excessive drawdown resilience yielding mathematically exploitable structural alpha relative to baseline Fama-French bounds."_

1. Click the **Voice Input (Reson8)** interface.
2. Dictate the exact prompt above.
3. Observe **Agent 1** automatically decouple the thesis into mathematical directions (e.g. `H0: Alpha Z-score > 1.96`).
4. Upon pressing **Deploy Analytics**, monitor the Pipeline View for real-time statistical tests.

## 📊 Navigating the LaTeX Reports

When the pipeline finalises execution, the **Right Panel** exposes a `.pdf` package.
Reports strictly enforce the **IMRaD format** (Introduction, Methodology, Results, Discussion). 

* **Results Section**: Verify your structural Edge by evaluating the injected `Bayesian Sharpe` metric, specifically adjusted against sample variance noise.
* **Appendix**: Fama-French 5-Factor loads and structural Principal Component limits mapped dynamically over your specific `[start, end]` timeframe.

## ⚠️ Known Limitations

* **Survivorship Bias**: Yahoo Finance (`yfinance`) data endpoints do not reflect strictly delisted tickers inside historical constraints.
* **Rate Limits**: Excessive queries (>50 parallel) through `Agent 3` into the underlying scraper infrastructure may face exponential backoff limits from `Google Scholar` or `Reddit WSB`.
* **Hardware Thresholds**: Generating `pdflatex` distributions dynamically requires significant RAM buffers for nested Matplotlib SVG scaling.

## 🤝 Contribution

Internal tooling logic should follow strict PEP8 parameters. Extend quant methodologies within `backend/math_engine/` and write equivalent bounding verifications inside `backend/tests/test_math_engine.py` tracking convergence edge cases.

## 📄 License
MIT License. Commercial implementations operating the Octant AI Framework assume sole liability for capital executions mapped over generated statistical outputs. Use solely as a research workbench.