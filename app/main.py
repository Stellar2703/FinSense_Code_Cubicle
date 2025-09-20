from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
from dotenv import load_dotenv

from .services.state import AppState
from .services.trading_buddy import handle_trading_question
from .services.mock_sources import start_mock_feeds
from .services.realtime_sources import start_realtime_feeds, realtime_available
from .services.alerts import AlertBroker
from .routers import demo as demo_router
from .routers import realtime as realtime_router

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
    if use_real and realtime_available():
        asyncio.create_task(start_realtime_feeds(state, alerts))
    else:
        asyncio.create_task(start_mock_feeds(state, alerts))

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

@app.post("/ask")
async def ask(question: str = Form(...)):
    answer = await handle_trading_question(question, state)
    return {"answer": answer}

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
async def upload_portfolio(file: UploadFile = File(...)):
    content = await file.read()
    await state.load_portfolio_json(content)
    return {"ok": True}

app.include_router(demo_router.router)
app.include_router(realtime_router.router)
