import asyncio
import aiohttp
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json

from .state import AppState, NewsItem
from .utils import classify_sentiment, estimate_news_impact, anomaly_ratio


def realtime_available() -> bool:
    """Check if real-time configuration is available"""
    return bool(
        os.getenv("ALPHA_VANTAGE_API_KEY") or 
        os.getenv("FINNHUB_API_KEY") or 
        os.getenv("POLYGON_API_KEY") or
        os.getenv("REALTIME_WEBHOOK_TOKEN")
    )


async def start_realtime_feeds(state: AppState, alerts) -> None:
    """Start real-time data feeds based on available API keys"""
    print("🚀 Starting real-time feeds...")
    
    # Add some initial demo data while feeds start up
    await _add_demo_data(state)
    
    tasks = []
    
    # Prioritize Finnhub since it's working perfectly
    if os.getenv("FINNHUB_API_KEY"):
        print("� Starting Finnhub price feed...")
        tasks.append(asyncio.create_task(_finnhub_rest_feed(state)))  # Use REST instead of WebSocket for reliability
        print("� Starting Finnhub news feed...")
        tasks.append(asyncio.create_task(_finnhub_news_feed(state, alerts)))
    
    # Use other APIs as backup/supplement
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        print("� Starting Alpha Vantage feed (backup)...")
        tasks.append(asyncio.create_task(_alpha_vantage_feed(state)))
    if os.getenv("POLYGON_API_KEY"):
        print("� Starting Polygon feed (backup)...")
        tasks.append(asyncio.create_task(_polygon_feed(state)))
        
    # News feeds
    if os.getenv("NEWS_API_KEY"):
        print("� Starting NewsAPI feed...")
        tasks.append(asyncio.create_task(_news_api_feed(state, alerts)))
    
    # Mock feeds for demo purposes
    print("🎭 Starting mock feeds...")
    tasks.append(asyncio.create_task(_realtime_sanctions_feed(state, alerts)))
    tasks.append(asyncio.create_task(_realtime_payments_feed(state, alerts)))
    tasks.append(asyncio.create_task(_portfolio_watcher(state, alerts)))
    
    print(f"✅ Started {len(tasks)} real-time feeds")
    
    # Error handling for all tasks
    for task in tasks:
        task.add_done_callback(lambda fut: fut.exception() and print(f"❌ Feed error: {fut.exception()}"))


async def _alpha_vantage_feed(state: AppState) -> None:
    """Alpha Vantage real-time stock prices"""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return
        
    print(f"📊 Alpha Vantage feed starting for symbols: {state.symbols}")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for symbol in state.symbols:
                    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            quote = data.get("Global Quote", {})
                            if quote and "05. price" in quote:
                                price = float(quote.get("05. price", 0))
                                change = float(quote.get("09. change", 0))
                                if price > 0:
                                    ts = state.now_ts()
                                    old_price = state.prices.get(symbol, price)
                                    state.prices[symbol] = price
                                    
                                    market_data = {
                                        "type": "price",
                                        "symbol": symbol,
                                        "price": round(price, 2),
                                        "change": round(change, 2),
                                        "change_percent": round((change / (price - change)) * 100, 2) if (price - change) != 0 else 0,
                                        "ts": ts
                                    }
                                    
                                    await state.emit_market(market_data)
                                    print(f"📈 {symbol}: ${price} ({change:+.2f})")
                            else:
                                print(f"⚠️ No data for {symbol} from Alpha Vantage")
                    await asyncio.sleep(2)  # Rate limiting
                await asyncio.sleep(10)  # Wait between full cycles
            except Exception as e:
                print(f"❌ Alpha Vantage error: {e}")
                await asyncio.sleep(30)


async def _finnhub_rest_feed(state: AppState) -> None:
    """Finnhub REST API for reliable real-time prices"""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return
        
    print(f"📈 Finnhub REST feed starting for symbols: {state.symbols}")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for symbol in state.symbols:
                    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "c" in data and data["c"] > 0:
                                current_price = data["c"]
                                change = data.get("d", 0)
                                change_percent = data.get("dp", 0)
                                ts = state.now_ts()
                                
                                old_price = state.prices.get(symbol, current_price)
                                state.prices[symbol] = current_price
                                
                                market_data = {
                                    "type": "price",
                                    "symbol": symbol,
                                    "price": round(current_price, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_percent, 2),
                                    "ts": ts
                                }
                                
                                await state.emit_market(market_data)
                                print(f"📈 {symbol}: ${current_price} ({change:+.2f}, {change_percent:+.1f}%)")
                            else:
                                print(f"⚠️ No data for {symbol} from Finnhub")
                        else:
                            print(f"❌ Finnhub HTTP {resp.status} for {symbol}")
                    
                    await asyncio.sleep(0.2)  # Rate limiting between symbols
                    
                await asyncio.sleep(5)  # Wait between full cycles
            except Exception as e:
                print(f"❌ Finnhub REST error: {e}")
                await asyncio.sleep(30)


async def _finnhub_feed(state: AppState) -> None:
    """Finnhub WebSocket for real-time prices"""
    import websockets
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return
        
    uri = f"wss://ws.finnhub.io?token={api_key}"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to symbols
        for symbol in state.symbols:
            await websocket.send(json.dumps({"type": "subscribe", "symbol": symbol}))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "trade":
                    for trade in data.get("data", []):
                        symbol = trade.get("s")
                        price = trade.get("p")
                        if symbol and price:
                            ts = trade.get("t", state.now_ts() * 1000) / 1000
                            state.prices[symbol] = price
                            await state.emit_market({
                                "type": "price",
                                "symbol": symbol,
                                "price": round(price, 2),
                                "ts": ts
                            })
            except Exception as e:
                print(f"Finnhub WebSocket error: {e}")


async def _polygon_feed(state: AppState) -> None:
    """Polygon.io real-time data"""
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        return
        
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for symbol in state.symbols:
                    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apikey={api_key}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results = data.get("results", {})
                            if results:
                                price = results.get("p")
                                if price:
                                    ts = results.get("t", state.now_ts() * 1000) / 1000
                                    state.prices[symbol] = price
                                    await state.emit_market({
                                        "type": "price",
                                        "symbol": symbol,
                                        "price": round(price, 2),
                                        "ts": ts
                                    })
                    await asyncio.sleep(1)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Polygon error: {e}")
                await asyncio.sleep(30)


async def _news_api_feed(state: AppState, alerts) -> None:
    """News API for financial news"""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return
        
    print(f"📰 NewsAPI feed starting for symbols: {state.symbols}")
    async with aiohttp.ClientSession() as session:
        seen_urls = set()
        while True:
            try:
                # Search for news about our symbols
                symbols_query = " OR ".join(state.symbols)
                url = f"https://newsapi.org/v2/everything?q=({symbols_query}) AND (stock OR market OR earnings OR trading)&sortBy=publishedAt&pageSize=10&apiKey={api_key}"
                
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        print(f"📰 Found {len(articles)} articles")
                        
                        for article in articles:
                            url_key = article.get("url", "")
                            if url_key in seen_urls:
                                continue
                            seen_urls.add(url_key)
                            
                            title = article.get("title", "")
                            # Try to infer symbol from title and description
                            symbol = None
                            content = f"{title} {article.get('description', '')}".lower()
                            
                            # Check for symbol mentions
                            for s in state.symbols:
                                if s.lower() in content or s in content.upper():
                                    symbol = s
                                    break
                            
                            # If no symbol found, assign to first symbol for demo
                            if not symbol and state.symbols:
                                symbol = state.symbols[0]
                            
                            if symbol and title:
                                sentiment = classify_sentiment(title)
                                ts = state.now_ts()
                                
                                item = NewsItem(ts=ts, symbol=symbol, headline=title, sentiment=sentiment)
                                state.news.append(item)
                                
                                news_data = {
                                    "type": "news",
                                    "symbol": symbol,
                                    "headline": title,
                                    "sentiment": sentiment,
                                    "source": article.get("source", {}).get("name", "Unknown"),
                                    "ts": ts
                                }
                                
                                await state.emit_market(news_data)
                                print(f"📰 {symbol}: {title[:50]}... ({sentiment})")
                                
                                # Portfolio impact
                                if state.portfolio and symbol in state.portfolio.holdings:
                                    impact = estimate_news_impact(sentiment)
                                    await alerts.publish({
                                        "channel": "portfolio",
                                        "kind": "news-impact",
                                        "symbol": symbol,
                                        "impact_pct": impact,
                                        "headline": title,
                                        "ts": ts,
                                        "message": f"{symbol}: {title} — estimated impact {impact:+.1f}%",
                                    })
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                print(f"News API error: {e}")
                await asyncio.sleep(600)


async def _finnhub_news_feed(state: AppState, alerts) -> None:
    """Finnhub news feed"""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return
        
    async with aiohttp.ClientSession() as session:
        seen_ids = set()
        while True:
            try:
                url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        articles = await resp.json()
                        
                        for article in articles[:10]:
                            article_id = article.get("id")
                            if article_id in seen_ids:
                                continue
                            seen_ids.add(article_id)
                            
                            headline = article.get("headline", "")
                            # Try to match symbols
                            symbol = None
                            for s in state.symbols:
                                if s.lower() in headline.lower():
                                    symbol = s
                                    break
                            
                            if symbol and headline:
                                sentiment = classify_sentiment(headline)
                                ts = article.get("datetime", state.now_ts())
                                
                                item = NewsItem(ts=ts, symbol=symbol, headline=headline, sentiment=sentiment)
                                state.news.append(item)
                                
                                await state.emit_market({
                                    "type": "news",
                                    "symbol": symbol,
                                    "headline": headline,
                                    "sentiment": sentiment,
                                    "ts": ts
                                })
                
                await asyncio.sleep(180)  # Check every 3 minutes
            except Exception as e:
                print(f"Finnhub news error: {e}")
                await asyncio.sleep(300)


async def _realtime_sanctions_feed(state: AppState, alerts) -> None:
    """Real-time sanctions feed (placeholder - adapt to your sanctions API)"""
    sanctions_api = os.getenv("SANCTIONS_API_URL")
    if not sanctions_api:
        # Fallback to periodic mock updates
        return await _mock_sanctions_updates(state, alerts)
    
    # TODO: Implement your actual sanctions API polling
    # For now, fallback to mock
    await _mock_sanctions_updates(state, alerts)


async def _realtime_payments_feed(state: AppState, alerts) -> None:
    """Real-time payments feed (placeholder - adapt to your payment stream)"""
    payments_webhook = os.getenv("PAYMENTS_WEBHOOK_URL")
    if not payments_webhook:
        # Fallback to mock payment generation
        return await _mock_payments_stream(state, alerts)
    
    # TODO: Implement your actual payment stream processing
    # For now, fallback to mock
    await _mock_payments_stream(state, alerts)


async def _mock_sanctions_updates(state: AppState, alerts) -> None:
    """Mock sanctions updates for demo"""
    sanctioned_names = ["John Doe", "Acme Imports", "GlobalTrade Ltd", "Ivan Petrov"]
    idx = 0
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
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


async def _mock_payments_stream(state: AppState, alerts) -> None:
    """Mock payment stream for demo"""
    customers = ["cust_1", "cust_2", "cust_3"]
    # Initialize baselines
    for cid in customers:
        if cid not in state.customer_baseline:
            state.customer_baseline[cid] = {"avg": 8000.0, "count": 20}

    tick = 0
    while True:
        await asyncio.sleep(10)  # Every 10 seconds
        tick += 1
        
        for cid in customers:
            base = state.customer_baseline[cid]["avg"]
            amt = abs(random.gauss(base, base * 0.15))
            
            # Occasional spikes
            if tick % 20 == 0 and cid == "cust_2":
                amt = base * 25
            
            recipient = random.choice(["John Doe", "CleanVendor", "Ivan Petrov", "GoodBiz"])
            ts = state.now_ts()
            
            # Anomaly detection
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
            
            # Sanctions check
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
            
            # Update baseline (exclude anomalies)
            if not is_anom:
                stat = state.customer_baseline[cid]
                stat["avg"] = (stat["avg"] * stat["count"] + amt) / (stat["count"] + 1)
                stat["count"] += 1


async def _portfolio_watcher(state: AppState, alerts) -> None:
    """Portfolio monitoring for price movements"""
    while True:
        await asyncio.sleep(15)
        if not state.portfolio:
            continue
            
        for symbol, qty in state.portfolio.holdings.items():
            price = state.prices.get(symbol)
            if not price:
                continue
                
            # Check for significant moves
            hist = state.price_history.get(symbol, [])
            recent = [p for p in hist if (state.now_ts() - p.ts) <= 60]  # Last minute
            if len(recent) >= 2:
                change = recent[-1].price - recent[0].price
                change_pct = (change / recent[0].price) * 100
                if abs(change_pct) > 1.0:  # >1% move
                    await alerts.publish({
                        "channel": "portfolio",
                        "kind": "price-move",
                        "symbol": symbol,
                        "change_pct": round(change_pct, 2),
                        "ts": state.now_ts(),
                        "message": f"{symbol} moved {change_pct:+.1f}% in last minute ({qty} shares held).",
                    })


# For webhook/manual ingestion
async def ingest_price_data(state: AppState, symbol: str, price: float, timestamp: Optional[float] = None) -> None:
    """Manually ingest price data"""
    ts = timestamp or state.now_ts()
    state.prices[symbol] = price
    await state.emit_market({
        "type": "price",
        "symbol": symbol,
        "price": round(price, 2),
        "ts": ts
    })


async def ingest_news_data(state: AppState, alerts, symbol: str, headline: str, timestamp: Optional[float] = None) -> None:
    """Manually ingest news data"""
    ts = timestamp or state.now_ts()
    sentiment = classify_sentiment(headline)
    
    item = NewsItem(ts=ts, symbol=symbol, headline=headline, sentiment=sentiment)
    state.news.append(item)
    
    await state.emit_market({
        "type": "news",
        "symbol": symbol,
        "headline": headline,
        "sentiment": sentiment,
        "ts": ts
    })
    
    # Portfolio impact
    if state.portfolio and symbol in state.portfolio.holdings:
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


# Add missing import
import random


async def _add_demo_data(state: AppState) -> None:
    """Add some initial demo data to show the system working"""
    # Add initial prices for 10 major companies
    demo_prices = {
        "TSLA": 416.85,    # Tesla
        "AAPL": 225.20,    # Apple
        "GOOGL": 172.45,   # Alphabet
        "MSFT": 428.90,    # Microsoft
        "AMZN": 185.30,    # Amazon
        "NVDA": 125.75,    # NVIDIA
        "META": 545.20,    # Meta
        "NFLX": 682.15,    # Netflix
        "AMD": 158.40,     # AMD
        "UBER": 73.25      # Uber
    }
    
    for symbol, price in demo_prices.items():
        state.prices[symbol] = price
        await state.emit_market({
            "type": "price",
            "symbol": symbol,
            "price": price,
            "change": random.uniform(-3.5, 3.5),
            "change_percent": random.uniform(-2.2, 2.2),
            "ts": state.now_ts()
        })
    
    # Add demo news for various companies
    demo_news = [
        ("TSLA", "Tesla reports strong Q3 delivery numbers, beating analyst expectations"),
        ("AAPL", "Apple unveils new AI features for iPhone, shares up in after-hours trading"),
        ("GOOGL", "Google announces breakthrough in quantum computing research"),
        ("MSFT", "Microsoft Azure revenue grows 30% year-over-year, exceeding forecasts"),
        ("AMZN", "Amazon Web Services launches new AI infrastructure services"),
        ("NVDA", "NVIDIA partners with major automakers for autonomous driving chips"),
        ("META", "Meta's VR division shows promising user growth in Q3 earnings"),
        ("NFLX", "Netflix subscriber growth accelerates with international expansion"),
        ("AMD", "AMD introduces next-generation datacenter processors"),
        ("UBER", "Uber achieves record profitability as ride-sharing demand surges")
    ]
    
    for symbol, headline in demo_news:
        sentiment = classify_sentiment(headline)
        ts = state.now_ts()
        
        item = NewsItem(ts=ts, symbol=symbol, headline=headline, sentiment=sentiment)
        state.news.append(item)
        
        await state.emit_market({
            "type": "news",
            "symbol": symbol,
            "headline": headline,
            "sentiment": sentiment,
            "source": "Demo News",
            "ts": ts
        })


async def _rss_feed(state: AppState, alerts) -> None:
    """RSS feed for financial news"""
    try:
        import feedparser
    except ImportError:
        print("❌ feedparser not available for RSS feeds")
        return
    
    rss_feeds = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "https://www.marketwatch.com/rss/topstories", 
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    ]
    
    print("📡 Starting RSS feeds...")
    
    while True:
        try:
            for feed_url in rss_feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:5]:  # Limit to 5 latest per feed
                        title = entry.title
                        pub_date = entry.get('published_parsed')
                        
                        # Extract symbols from title/description
                        symbol = None
                        for sym in state.symbols:
                            if sym.lower() in title.lower() or sym in title:
                                symbol = sym
                                break
                        
                        if symbol:
                            sentiment = classify_sentiment(title)
                            ts = state.now_ts()
                            
                            # Create news item
                            news_data = {
                                "type": "news",
                                "symbol": symbol,
                                "headline": title,
                                "sentiment": sentiment,
                                "source": "RSS",
                                "ts": ts
                            }
                            
                            await state.emit_market(news_data)
                            print(f"📡 RSS {symbol}: {title[:50]}... ({sentiment})")
                            
                            # Portfolio impact
                            if state.portfolio and symbol in state.portfolio.holdings:
                                impact = estimate_news_impact(sentiment)
                                await alerts.publish({
                                    "channel": "portfolio",
                                    "kind": "news-impact",
                                    "symbol": symbol,
                                    "impact_pct": impact,
                                    "headline": title,
                                    "ts": ts,
                                    "message": f"{symbol}: {title} — RSS impact {impact:+.1f}%",
                                })
                
                except Exception as e:
                    print(f"RSS feed error for {feed_url}: {e}")
                    
            await asyncio.sleep(600)  # Check every 10 minutes
        except Exception as e:
            print(f"RSS feed error: {e}")
            await asyncio.sleep(900)


async def _twitter_feed(state: AppState, alerts) -> None:
    """Twitter/X feed for financial news (placeholder for API v2)"""
    # Note: Twitter API v2 requires special access and authentication
    twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not twitter_bearer_token:
        print("⚠️ Twitter API not configured, skipping Twitter feed")
        return
    
    # Financial Twitter accounts to monitor
    financial_accounts = [
        "Bloomberg",
        "Reuters", 
        "MarketWatch",
        "CNBC",
        "FinancialTimes",
        "WSJ"
    ]
    
    print("🐦 Starting Twitter feed...")
    
    while True:
        try:
            # This would use Twitter API v2 to fetch recent tweets
            # For demo purposes, we'll simulate with mock data
            for account in financial_accounts:
                # Mock Twitter integration - replace with real API calls
                mock_tweets = [
                    f"Breaking: {account} reports on market volatility affecting major indices",
                    f"{account}: Tech stocks showing mixed signals in after-hours trading",
                    f"Market update from {account}: Energy sector gains while utilities decline"
                ]
                
                for tweet in mock_tweets[:1]:  # One per account
                    # Extract symbols
                    symbol = None
                    for sym in state.symbols:
                        if sym.lower() in tweet.lower() or sym in tweet:
                            symbol = sym
                            break
                    
                    if symbol:
                        sentiment = classify_sentiment(tweet)
                        ts = state.now_ts()
                        
                        news_data = {
                            "type": "news", 
                            "symbol": symbol,
                            "headline": tweet,
                            "sentiment": sentiment,
                            "source": f"Twitter/@{account}",
                            "ts": ts
                        }
                        
                        await state.emit_market(news_data)
                        print(f"🐦 Twitter {symbol}: {tweet[:50]}... ({sentiment})")
                        
                        # Portfolio impact
                        if state.portfolio and symbol in state.portfolio.holdings:
                            impact = estimate_news_impact(sentiment)
                            await alerts.publish({
                                "channel": "portfolio",
                                "kind": "news-impact", 
                                "symbol": symbol,
                                "impact_pct": impact,
                                "headline": tweet,
                                "ts": ts,
                                "message": f"{symbol}: {tweet} — Twitter impact {impact:+.1f}%",
                            })
            
            await asyncio.sleep(1800)  # Check every 30 minutes
        except Exception as e:
            print(f"Twitter feed error: {e}")
            await asyncio.sleep(2400)
