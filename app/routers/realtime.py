from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os

from ..services.state import AppState
from ..services.alerts import AlertBroker
from ..services.realtime_sources import ingest_price_data, ingest_news_data
from statistics import mean, pstdev

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
    
    # Enhanced anomaly detection: ratio + z-score + rolling statistics
    from ..services.utils import anomaly_ratio
    baseline = state.customer_baseline.get(data.customer_id, {"avg": 5000.0, "count": 1})
    ratio_flag, ratio = anomaly_ratio(data.amount, baseline["avg"])

    # Maintain rolling history (cap length to 100 for memory)
    history = state.customer_history.setdefault(data.customer_id, [])
    history.append(data.amount)
    if len(history) > 100:
        history.pop(0)

    # Compute z-score if we have at least 5 points and non-zero stdev
    zscore = None
    if len(history) >= 5:
        m = mean(history)
        sd = pstdev(history) or 0.0
        if sd > 0:
            zscore = (data.amount - m) / sd

    # Determine severity tiers
    severity = "normal"
    is_anom = False
    if ratio_flag or (zscore is not None and zscore >= 4):
        is_anom = True
        if ratio >= 20 or (zscore and zscore >= 8):
            severity = "critical"
        elif ratio >= 15 or (zscore and zscore >= 6):
            severity = "high"
        else:
            severity = "medium"

    ts = data.timestamp or state.now_ts()

    # Record payment event
    state.payments.append({
        "customer_id": data.customer_id,
        "amount": data.amount,
        "recipient": data.recipient,
        "ts": ts,
        "ratio": ratio,
        "zscore": zscore,
        "is_anomaly": is_anom,
        "severity": severity,
    })
    if len(state.payments) > 500:
        state.payments.pop(0)

    if is_anom:
        await alerts.publish({
            "channel": "fraud",
            "kind": "payment_anomaly",
            "customer": data.customer_id,
            "amount": data.amount,
            "ratio": round(ratio, 2),
            "zscore": round(zscore, 2) if zscore is not None else None,
            "severity": severity,
            "ts": ts,
            "message": f"{data.customer_id}: {severity} anomaly {data.amount:,.0f} (x{ratio:.1f}{' z=' + str(round(zscore,2)) if zscore is not None else ''})",
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
            "severity": "critical",
        })

    # Update baseline only if not anomalous (keeps baseline stable)
    if not is_anom:
        if data.customer_id not in state.customer_baseline:
            state.customer_baseline[data.customer_id] = {"avg": data.amount, "count": 1}
        else:
            stat = state.customer_baseline[data.customer_id]
            stat["avg"] = (stat["avg"] * stat["count"] + data.amount) / (stat["count"] + 1)
            stat["count"] += 1

    return {"status": "ok", "message": f"Payment processed", "anomaly": is_anom, "severity": severity, "ratio": ratio, "zscore": zscore}

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

@router.get("/payments/recent")
async def recent_payments(limit: int = 50):
    """Return recent payment events (for Payment Guard UI)."""
    from ..main import state
    return list(reversed(state.payments[-limit:]))

@router.get("/payments/metrics/{customer_id}")
async def customer_payment_metrics(customer_id: str):
    """Return rolling metrics and baseline for a customer (Behavior Watchdog)."""
    from ..main import state
    history = state.customer_history.get(customer_id, [])
    baseline = state.customer_baseline.get(customer_id, {"avg": None, "count": 0})
    response = {
        "customer_id": customer_id,
        "baseline_avg": baseline["avg"],
        "baseline_count": baseline["count"],
        "history_len": len(history),
        "last_amount": history[-1] if history else None,
    }
    if len(history) >= 2:
        response["min"] = min(history)
        response["max"] = max(history)
        response["mean"] = sum(history) / len(history)
    return response
