from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
from dotenv import load_dotenv

from .services.state import AppState
from .services.trading_buddy import handle_trading_question
from .services.mock_sources import start_mock_feeds
from .services.realtime_sources import start_realtime_feeds, realtime_available
from .services.pathway_integration import integrate_pathway_with_realtime
from .services.alerts import AlertBroker
from .routers import demo as demo_router
from .routers import realtime as realtime_router
from .routers import trading as trading_router

load_dotenv()

app = FastAPI(title="FinSense AI", version="0.1.0")

# Static and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
STATIC_DIR = os.path.join(WEB_DIR, "static")
TEMPLATES = Jinja2Templates(directory=WEB_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

state = AppState()
alerts = AlertBroker()

@app.on_event("startup")
async def on_startup():
    # Decide between mock and real-time feeds
    use_real = os.getenv("REALTIME", "0") in {"1", "true", "True"}
    
    # Start data feeds
    if use_real and realtime_available():
        asyncio.create_task(start_realtime_feeds(state, alerts))
    else:
        asyncio.create_task(start_mock_feeds(state, alerts))
    
    # Integrate Pathway for real-time data processing if available
    asyncio.create_task(integrate_pathway_with_realtime(state, alerts))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return TEMPLATES.TemplateResponse("index-new.html", {"request": request})

@app.get("/new", response_class=HTMLResponse)
async def new_ui(request: Request):
    return TEMPLATES.TemplateResponse("index-new.html", {"request": request})

@app.websocket("/ws/market")
async def ws_market(ws: WebSocket):
    await ws.accept()
    try:
        q = state.market_ws_queue
        while True:
            msg = await q.get()
            await ws.send_json(msg)
    except WebSocketDisconnect:
        return

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await ws.accept()
    try:
        q = alerts.ws_queue
        while True:
            msg = await q.get()
            await ws.send_json(msg)
    except WebSocketDisconnect:
        return

@app.post("/ask", response_class=PlainTextResponse)
async def ask(question: str = Form(...)):
    """Return plain text so newlines aren't JSON-escaped (prevents literal \n in UI)."""
    answer = await handle_trading_question(question, state)
    # Ensure we return a PlainTextResponse explicitly (FastAPI would otherwise JSON-encode)
    return PlainTextResponse(answer)

@app.post("/trigger-fake-news")
async def trigger_fake_news():
    """Trigger a demo news alert for testing"""
    import random
    from .services.utils import classify_sentiment
    
    sample_news = [
        ("AAPL", "Apple announces breakthrough in battery technology"),
        ("TSLA", "Tesla reports record quarterly deliveries"),
        ("GOOGL", "Google unveils new AI capabilities in search"),
        ("MSFT", "Microsoft Azure shows strong growth in cloud services"),
        ("NVDA", "NVIDIA announces next-generation AI chips")
    ]
    
    symbol, headline = random.choice(sample_news)
    sentiment = classify_sentiment(headline)
    ts = state.now_ts()
    
    # Add to news data
    from .services.state import NewsItem
    news_item = NewsItem(ts=ts, symbol=symbol, headline=headline, sentiment=sentiment)
    state.news.append(news_item)
    
    # Emit to WebSocket
    await state.emit_market({
        "type": "news",
        "symbol": symbol,
        "headline": headline,
        "sentiment": sentiment,
        "source": "Demo",
        "ts": ts
    })
    
    # Trigger portfolio alert if applicable
    if state.portfolio and symbol in state.portfolio.holdings:
        from .services.utils import estimate_news_impact
        impact = estimate_news_impact(sentiment)
        await alerts.publish({
            "channel": "portfolio",
            "kind": "news-impact",
            "symbol": symbol,
            "impact_pct": impact,
            "headline": headline,
            "ts": ts,
            "message": f"{symbol}: {headline} — estimated impact {impact:+.1f}%",
        })
    
    return {"status": "success", "symbol": symbol, "headline": headline}

@app.post("/upload-portfolio")
async def upload_portfolio(
    file: UploadFile = File(None),
    portfolio: UploadFile = File(None)
):
    # Accept either field name for flexibility
    selected = file or portfolio
    if not selected:
        return PlainTextResponse("No file uploaded (expected form field 'file' or 'portfolio').", status_code=400)
    try:
        content = await selected.read()
        await state.load_portfolio_json(content)
        from .routers.trading import _compute_portfolio_analysis
        analysis = _compute_portfolio_analysis(state)
        return {"ok": True, "analysis": analysis}
    except Exception as e:
        return PlainTextResponse(f"Failed to load portfolio: {e}", status_code=400)

app.include_router(demo_router.router)
app.include_router(realtime_router.router)
app.include_router(trading_router.router)

# Set global references for trading router
trading_router.state = state
trading_router.alerts = alerts
