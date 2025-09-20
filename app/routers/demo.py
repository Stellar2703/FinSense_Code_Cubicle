from fastapi import APIRouter
from ..services.state import AppState
from ..services.utils import classify_sentiment
from ..services.state import NewsItem

router = APIRouter()

# simple endpoint to inject fake news for demo
@router.post("/demo/fake_news")
async def fake_news():
    # Access the app singletons
    from ..main import state as st, alerts
    item = NewsItem(ts=st.now_ts(), symbol="AAPL", headline="Apple delays iPhone launch", sentiment="negative")
    st.news.append(item)
    await st.emit_market({
        "type": "news",
        "symbol": item.symbol,
        "headline": item.headline,
        "sentiment": item.sentiment,
        "ts": item.ts,
    })
    await alerts.publish({
        "channel": "portfolio",
        "kind": "news-impact",
        "symbol": item.symbol,
        "impact_pct": -2.0,
        "headline": item.headline,
        "ts": item.ts,
        "message": f"{item.symbol}: {item.headline} — estimated impact -2.0%",
    })
    return {"ok": True}
