# FinSense AI — Live Fintech AI Demo (Pathway + FastAPI)

FinSense AI is a multi-feature prototype showing how AI + Pathway can react to live data. It ships with mock live streams so you can demo everything offline, and offers simple hooks to plug real data sources later.
Features included:
- Trading Buddy: Ask why a stock is moving; it correlates price jumps with recent news.
- Payment Guard: Sanctions match checks and fraud/anomaly alerts on incoming payments.
- Portfolio Risk Dashboard: Upload a tiny portfolio; news triggers risk notices per holding.
- Customer Behavior Watchdog: Flags unusual spend vs a rolling baseline.

Tech stack:
- Backend: Python 3.11+, FastAPI, WebSockets, Pathway for streaming pipelines
- Optional LLM: OpenAI or Azure OpenAI via env vars (falls back to rule-based explainer)
- Frontend: Minimal HTML + Tailwind CDN + HTMX + Alpine.js for real-time updates (we only use vanilla JS here)

## Quickstart (Windows PowerShell)

```powershell
# 1) Create and activate a virtual env
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) (Optional) Set LLM keys
# $env:OPENAI_API_KEY = "sk-..."   # or use AZURE_OPENAI_* vars as in .env.example

# 4) Run the app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in a browser.

## What to expect
- Mock price + news streams start automatically (Tesla/Apple by default).
- Web UI shows:
  - Trading Buddy chat (ask “Why did Tesla jump 5% just now?”)
  - Live Market + News feed
  - Payment Guard alerts (sanctions/fraud)
  - Portfolio upload and risk updates
  - Watchdog anomaly alerts

## Environment variables
Copy `.env.example` to `.env` and edit as needed, or set in your shell.
- OPENAI_API_KEY: for OpenAI
- AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / AZURE_OPENAI_DEPLOYMENT
- SANCTIONS_REFRESH_SECONDS: refresh interval for sanctions list (mock)
- SYMBOLS: comma-separated tickers to stream (default: TSLA,AAPL)

## Real feeds (optional)
This project runs offline by default. To use real data, extend `app/services/mock_sources.py` or add new readers in `app/services/pathway_pipelines.py` using Pathway connectors (e.g. Kafka, HTTP, files). Keep the same output schemas and queues so the UI continues to work.

## Tests
Run a tiny unit test for anomaly logic:
```powershell
pytest -q
```

## Notes
- Pathway is used conceptually to model live pipelines. If Pathway isn’t available in your env, the app falls back to pure asyncio producers so the demo still runs. Install `pathway` to enable pipelines.
- Keep this as a learning/demo build. For production, add persistence, auth, secrets management, metrics, and robust risk models.

---

MIT License
