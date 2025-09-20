#!/usr/bin/env python3
"""
Comprehensive API Data Availability Test
Tests all APIs with different symbols to find what works
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DataAvailabilityTester:
    def __init__(self):
        self.results = {}
        self.symbols = ["TSLA", "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX", "AMD", "UBER"]
        
    async def test_all_sources(self):
        """Test all data sources for all symbols"""
        print("🔍 Testing Data Availability Across All Sources")
        print("=" * 80)
        
        # Test each API
        await self.test_alpha_vantage_detailed()
        await self.test_finnhub_detailed()
        await self.test_polygon_detailed()
        await self.test_newsapi_detailed()
        
        # Print comprehensive summary
        self.print_detailed_summary()
        
    async def test_alpha_vantage_detailed(self):
        """Test Alpha Vantage for all symbols"""
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            self.results["Alpha Vantage"] = {"status": "❌", "message": "No API key"}
            return
            
        print("\n📊 Testing Alpha Vantage API...")
        working_symbols = []
        failed_symbols = []
        
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Try different functions
                    urls = [
                        f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}",
                        f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={api_key}",
                        f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
                    ]
                    
                    for i, url in enumerate(urls):
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                # Check for valid data
                                if i == 0 and "Global Quote" in data and data["Global Quote"]:
                                    quote = data["Global Quote"]
                                    if "05. price" in quote:
                                        price = quote["05. price"]
                                        working_symbols.append(f"{symbol}:${price}")
                                        print(f"  ✅ {symbol} - Global Quote: ${price}")
                                        break
                                elif i == 1 and "Time Series (5min)" in data:
                                    print(f"  ✅ {symbol} - Intraday data available")
                                    working_symbols.append(f"{symbol}:Intraday")
                                    break
                                elif i == 2 and "Symbol" in data:
                                    print(f"  ✅ {symbol} - Company overview available")
                                    working_symbols.append(f"{symbol}:Overview")
                                    break
                                elif "Note" in data:
                                    print(f"  ⚠️ {symbol} - Rate limit hit")
                                    failed_symbols.append(f"{symbol}:RateLimit")
                                    break
                                elif "Error Message" in data:
                                    print(f"  ❌ {symbol} - {data['Error Message']}")
                                    failed_symbols.append(f"{symbol}:Error")
                                    break
                            else:
                                print(f"  ❌ {symbol} - HTTP {resp.status}")
                                
                        await asyncio.sleep(0.5)  # Rate limiting
                        
                    if symbol not in [s.split(':')[0] for s in working_symbols + failed_symbols]:
                        failed_symbols.append(f"{symbol}:NoData")
                        
                except Exception as e:
                    print(f"  ❌ {symbol} - Exception: {e}")
                    failed_symbols.append(f"{symbol}:Exception")
                    
                await asyncio.sleep(1)  # Rate limiting between symbols
        
        self.results["Alpha Vantage"] = {
            "working": working_symbols,
            "failed": failed_symbols,
            "status": "✅" if working_symbols else "❌"
        }
        
    async def test_finnhub_detailed(self):
        """Test Finnhub for all symbols"""
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            self.results["Finnhub"] = {"status": "❌", "message": "No API key"}
            return
            
        print("\n📈 Testing Finnhub API...")
        working_symbols = []
        failed_symbols = []
        
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Test quote endpoint
                    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "c" in data and data["c"] > 0:
                                price = data["c"]
                                change = data.get("d", 0)
                                working_symbols.append(f"{symbol}:${price}({change:+.2f})")
                                print(f"  ✅ {symbol} - Quote: ${price} ({change:+.2f})")
                            else:
                                print(f"  ❌ {symbol} - No valid quote data: {data}")
                                failed_symbols.append(f"{symbol}:NoQuote")
                        else:
                            print(f"  ❌ {symbol} - HTTP {resp.status}")
                            failed_symbols.append(f"{symbol}:HTTP{resp.status}")
                            
                except Exception as e:
                    print(f"  ❌ {symbol} - Exception: {e}")
                    failed_symbols.append(f"{symbol}:Exception")
                    
                await asyncio.sleep(0.2)  # Rate limiting
        
        self.results["Finnhub"] = {
            "working": working_symbols,
            "failed": failed_symbols,
            "status": "✅" if working_symbols else "❌"
        }
        
    async def test_polygon_detailed(self):
        """Test Polygon for all symbols"""
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            self.results["Polygon"] = {"status": "❌", "message": "No API key"}
            return
            
        print("\n📉 Testing Polygon API...")
        working_symbols = []
        failed_symbols = []
        
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Test different endpoints
                    urls = [
                        f"https://api.polygon.io/v2/last/trade/{symbol}?apikey={api_key}",
                        f"https://api.polygon.io/v1/last/stocks/{symbol}?apikey={api_key}",
                        f"https://api.polygon.io/v3/reference/tickers/{symbol}?apikey={api_key}"
                    ]
                    
                    for i, url in enumerate(urls):
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                if i == 0 and "results" in data and data["results"]:
                                    price = data["results"].get("p")
                                    if price:
                                        working_symbols.append(f"{symbol}:${price}")
                                        print(f"  ✅ {symbol} - Last trade: ${price}")
                                        break
                                elif i == 1 and "last" in data:
                                    last_data = data["last"]
                                    if "price" in last_data:
                                        price = last_data["price"]
                                        working_symbols.append(f"{symbol}:${price}")
                                        print(f"  ✅ {symbol} - Last price: ${price}")
                                        break
                                elif i == 2 and "results" in data:
                                    working_symbols.append(f"{symbol}:Info")
                                    print(f"  ✅ {symbol} - Ticker info available")
                                    break
                            elif resp.status == 403:
                                print(f"  ❌ {symbol} - Access denied (check API key permissions)")
                                failed_symbols.append(f"{symbol}:AccessDenied")
                                break
                            else:
                                print(f"  ⚠️ {symbol} - HTTP {resp.status}")
                                
                        await asyncio.sleep(0.1)
                        
                    if symbol not in [s.split(':')[0] for s in working_symbols + failed_symbols]:
                        failed_symbols.append(f"{symbol}:NoData")
                        
                except Exception as e:
                    print(f"  ❌ {symbol} - Exception: {e}")
                    failed_symbols.append(f"{symbol}:Exception")
                    
                await asyncio.sleep(0.3)  # Rate limiting
        
        self.results["Polygon"] = {
            "working": working_symbols,
            "failed": failed_symbols,
            "status": "✅" if working_symbols else "❌"
        }
        
    async def test_newsapi_detailed(self):
        """Test NewsAPI for all symbols"""
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            self.results["NewsAPI"] = {"status": "❌", "message": "No API key"}
            return
            
        print("\n📰 Testing NewsAPI...")
        news_count = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test general financial news
                url = f"https://newsapi.org/v2/everything?q=stocks OR market OR trading&sortBy=publishedAt&pageSize=20&apiKey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        news_count = len(articles)
                        
                        symbol_mentions = {}
                        for article in articles:
                            title = article.get("title", "").upper()
                            for symbol in self.symbols:
                                if symbol in title:
                                    symbol_mentions[symbol] = symbol_mentions.get(symbol, 0) + 1
                        
                        print(f"  ✅ Found {news_count} financial articles")
                        for symbol, count in symbol_mentions.items():
                            print(f"    📌 {symbol}: {count} mentions")
                    else:
                        print(f"  ❌ HTTP {resp.status}")
                        
        except Exception as e:
            print(f"  ❌ NewsAPI - Exception: {e}")
        
        self.results["NewsAPI"] = {
            "articles": news_count,
            "status": "✅" if news_count > 0 else "❌"
        }
        
    def print_detailed_summary(self):
        """Print comprehensive summary"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE DATA AVAILABILITY REPORT")
        print("=" * 80)
        
        for api_name, result in self.results.items():
            print(f"\n{result['status']} {api_name}")
            print("-" * 40)
            
            if "working" in result:
                if result["working"]:
                    print("  ✅ Working symbols:")
                    for symbol_data in result["working"]:
                        print(f"    • {symbol_data}")
                else:
                    print("  ❌ No working symbols")
                    
                if result["failed"]:
                    print("  ⚠️ Failed symbols:")
                    for symbol_data in result["failed"]:
                        print(f"    • {symbol_data}")
            elif "articles" in result:
                print(f"  📰 Articles found: {result['articles']}")
            elif "message" in result:
                print(f"  📝 {result['message']}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATIONS")
        print("=" * 80)
        
        working_apis = [name for name, result in self.results.items() if result.get("status") == "✅"]
        
        if working_apis:
            print(f"✅ Working APIs: {', '.join(working_apis)}")
            
            # Find best symbols
            best_symbols = set()
            for api_name, result in self.results.items():
                if result.get("status") == "✅" and "working" in result:
                    for symbol_data in result["working"]:
                        symbol = symbol_data.split(':')[0]
                        best_symbols.add(symbol)
            
            if best_symbols:
                print(f"🎯 Symbols with data: {', '.join(sorted(best_symbols))}")
                print(f"\n📋 Recommended .env update:")
                print(f"SYMBOLS={','.join(sorted(best_symbols))}")
            else:
                print("⚠️ Try using demo mode or check API key permissions")
        else:
            print("❌ No APIs working - using demo/mock data mode recommended")


async def main():
    """Main function"""
    print("🔍 FinSense AI - Data Availability Diagnostic")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = DataAvailabilityTester()
    await tester.test_all_sources()


if __name__ == "__main__":
    asyncio.run(main())
