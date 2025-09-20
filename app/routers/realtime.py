from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os

from ..services.state import AppState
from ..services.alerts import AlertBroker
from ..services.realtime_sources import ingest_price_data, ingest_news_data

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

# Pydantic models for request validation
class PriceData(BaseModel):
    symbol: str
    price: float
    timestamp: Optional[float] = None

class NewsData(BaseModel):
    symbol: str
    headline: str
    timestamp: Optional[float] = None

class PaymentData(BaseModel):
    customer_id: str
    amount: float
    recipient: str
    timestamp: Optional[float] = None

# Webhook token validation
def verify_webhook_token(token: str = None):
    expected_token = os.getenv("REALTIME_WEBHOOK_TOKEN")
    if expected_token and token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    return True

@router.post("/price")
async def ingest_price(data: PriceData, token: str = None):
    """Ingest real-time price data via HTTP POST"""
    verify_webhook_token(token)
    
    # Import here to avoid circular import issues
    from ..main import state
    await ingest_price_data(state, data.symbol, data.price, data.timestamp)
    return {"status": "ok", "message": f"Price data ingested for {data.symbol}"}

@router.post("/news")
async def ingest_news(data: NewsData, token: str = None):
    """Ingest real-time news data via HTTP POST"""
    verify_webhook_token(token)
    
    from ..main import state, alerts
    await ingest_news_data(state, alerts, data.symbol, data.headline, data.timestamp)
    return {"status": "ok", "message": f"News data ingested for {data.symbol}"}

@router.post("/payment")
async def ingest_payment(data: PaymentData, token: str = None):
    """Ingest real-time payment data via HTTP POST"""
    verify_webhook_token(token)
    
    from ..main import state, alerts
    
    # Basic fraud detection
    from ..services.utils import anomaly_ratio
    baseline = state.customer_baseline.get(data.customer_id, {"avg": 5000.0, "count": 1})
    is_anom, ratio = anomaly_ratio(data.amount, baseline["avg"])
    
    ts = data.timestamp or state.now_ts()
    
    if is_anom:
        await alerts.publish({
            "channel": "fraud",
            "kind": "anomaly",
            "customer": data.customer_id,
            "amount": data.amount,
            "ratio": round(ratio, 1),
            "ts": ts,
            "message": f"{data.customer_id}: amount {data.amount:,.0f} is {ratio:.0f}× baseline — suspicious",
        })
    
    # Sanctions check
    hit_ts = state.sanctions.get(data.recipient)
    if hit_ts:
        ago = int(ts - hit_ts)
        await alerts.publish({
            "channel": "sanctions",
            "kind": "match",
            "customer": data.customer_id,
            "recipient": data.recipient,
            "amount": data.amount,
            "ts": ts,
            "message": f"Transfer flagged. Recipient '{data.recipient}' was added {ago} seconds ago.",
        })
    
    # Update baseline
    if not is_anom:
        if data.customer_id not in state.customer_baseline:
            state.customer_baseline[data.customer_id] = {"avg": data.amount, "count": 1}
        else:
            stat = state.customer_baseline[data.customer_id]
            stat["avg"] = (stat["avg"] * stat["count"] + data.amount) / (stat["count"] + 1)
            stat["count"] += 1
    
    return {"status": "ok", "message": f"Payment data processed for {data.customer_id}"}

@router.get("/status")
async def realtime_status():
    """Check real-time feed status"""
    from ..services.realtime_sources import realtime_available
    
    config = {
        "realtime_enabled": realtime_available(),
        "available_feeds": [],
        "webhook_token_set": bool(os.getenv("REALTIME_WEBHOOK_TOKEN"))
    }
    
    # Check which API keys are configured
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        config["available_feeds"].append("alpha_vantage")
    if os.getenv("FINNHUB_API_KEY"):
        config["available_feeds"].append("finnhub")
    if os.getenv("POLYGON_API_KEY"):
        config["available_feeds"].append("polygon")
    if os.getenv("NEWS_API_KEY"):
        config["available_feeds"].append("news_api")
    
    return config
