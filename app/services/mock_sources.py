import asyncio
import random
from typing import Dict, Any
from datetime import datetime, timezone

from .state import AppState, PricePoint, NewsItem
from .utils import classify_sentiment, estimate_news_impact, anomaly_ratio


async def start_mock_feeds(state: AppState, alerts) -> None:
    tasks = [
        asyncio.create_task(_price_feed(state)),
        asyncio.create_task(_news_feed(state, alerts)),
        asyncio.create_task(_sanctions_feed(state, alerts)),
        asyncio.create_task(_payments_feed(state, alerts)),
        asyncio.create_task(_portfolio_watcher(state, alerts)),
    ]
    for t in tasks:
        t.add_done_callback(lambda fut: fut.exception())


async def _price_feed(state: AppState) -> None:
    # initialize prices
    for s in state.symbols:
        state.prices[s] = random.uniform(50, 300)

    while True:
        for s in state.symbols:
            base = state.prices[s]
            # random walk
            delta = random.uniform(-0.5, 0.5)
            newp = max(1.0, base + delta)
            state.prices[s] = newp
            p = PricePoint(ts=state.now_ts(), price=newp)
            hist = state.price_history[s]
            hist.append(p)
            if len(hist) > 500:
                del hist[: len(hist) - 500]
            await state.emit_market({"type": "price", "symbol": s, "price": round(newp, 2), "ts": p.ts})
        await asyncio.sleep(1.0)


async def _news_feed(state: AppState, alerts) -> None:
    headlines = [
        ("TSLA", "Government announces EV subsidy boosting adoption"),
        ("AAPL", "Apple delays iPhone launch due to supply chain"),
        ("TSLA", "Tesla beats delivery record in Q3"),
        ("AAPL", "Analyst upgrades Apple on services growth"),
    ]
    while True:
        await asyncio.sleep(random.uniform(10, 20))
        sym, text = random.choice(headlines)
        sent = classify_sentiment(text)
        item = NewsItem(ts=state.now_ts(), symbol=sym, headline=text, sentiment=sent)
        state.news.append(item)
        # trim
        if len(state.news) > 200:
            del state.news[: len(state.news) - 200]
        await state.emit_market({
            "type": "news", "symbol": sym, "headline": text, "sentiment": sent, "ts": item.ts
        })

        # portfolio impact alert
        if state.portfolio and sym in state.portfolio.holdings:
            impact = estimate_news_impact(sent)
            await alerts.publish({
                "channel": "portfolio",
                "kind": "news-impact",
                "symbol": sym,
                "impact_pct": impact,
                "headline": text,
                "ts": item.ts,
                "message": f"{sym}: {text} — estimated impact {impact:+.1f}%",
            })


async def _sanctions_feed(state: AppState, alerts) -> None:
    # periodically add a new sanctioned name
    sanctioned_names = ["John Doe", "Acme Imports", "GlobalTrade Ltd", "Ivan Petrov"]
    idx = 0
    while True:
        await asyncio.sleep(30)
        name = sanctioned_names[idx % len(sanctioned_names)]
        idx += 1
        ts = state.now_ts()
        state.sanctions[name] = ts
        await alerts.publish({
            "channel": "sanctions",
            "kind": "added",
            "name": name,
            "ts": ts,
            "message": f"Sanctions list updated: {name} added just now.",
        })


async def _payments_feed(state: AppState, alerts) -> None:
    customers = ["cust_1", "cust_2", "cust_3"]
    # bootstrap baseline
    for cid in customers:
        state.customer_baseline[cid] = {"avg": 8000.0, "count": 20}

    tick = 0
    while True:
        await asyncio.sleep(5)
        tick += 1
        for cid in customers:
            base = state.customer_baseline[cid]["avg"]
            amt = random.gauss(base, base * 0.1)
            # sometimes inject a big spike
            if tick % 12 == 0 and cid == "cust_2":
                amt = base * 40
            if tick % 25 == 0 and cid == "cust_3":
                amt = base * 50

            # sanctions match test: pseudo name field
            recipient = random.choice(["John Doe", "CleanVendor", "Ivan Petrov", "GoodBiz"])
            ts = state.now_ts()

            # anomaly check
            avg = state.customer_baseline[cid]["avg"]
            is_anom, ratio = anomaly_ratio(amt, avg)
            if is_anom:
                await alerts.publish({
                    "channel": "fraud",
                    "kind": "anomaly",
                    "customer": cid,
                    "amount": round(amt, 2),
                    "ratio": round(ratio, 1),
                    "ts": ts,
                    "message": f"{cid}: amount {amt:,.0f} is {ratio:.0f}× baseline — suspicious",
                })

            # sanctions check
            hit_ts = state.sanctions.get(recipient)
            if hit_ts:
                ago = int(ts - hit_ts)
                await alerts.publish({
                    "channel": "sanctions",
                    "kind": "match",
                    "customer": cid,
                    "recipient": recipient,
                    "amount": round(amt, 2),
                    "ts": ts,
                    "message": f"Transfer flagged. Recipient '{recipient}' was added {ago} seconds ago.",
                })

            # update baseline with small learning (ignore anomalies)
            if not is_anom:
                stat = state.customer_baseline[cid]
                stat["avg"] = (stat["avg"] * stat["count"] + amt) / (stat["count"] + 1)
                stat["count"] += 1


async def _portfolio_watcher(state: AppState, alerts) -> None:
    # simple watcher is included in news feed; here we could add price-drawdown alerts
    while True:
        await asyncio.sleep(7)
        if not state.portfolio:
            continue
        for sym, qty in state.portfolio.holdings.items():
            price = state.prices.get(sym)
            if not price:
                continue
            # naive drawdown alert: if price moved >2 in the last 30s
            hist = state.price_history.get(sym, [])
            recent = [p for p in hist if (state.now_ts() - p.ts) <= 30]
            if len(recent) >= 2:
                chg = recent[-1].price - recent[0].price
                if abs(chg) > 2.0:
                    await alerts.publish({
                        "channel": "portfolio",
                        "kind": "price-move",
                        "symbol": sym,
                        "ts": state.now_ts(),
                        "message": f"{sym} moved {chg:+.2f} in last 30s.",
                    })
