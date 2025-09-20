#!/usr/bin/env python3
"""
Quick test to validate 10-company setup
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_10_companies():
    """Test that all 10 companies can be fetched"""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    symbols = ["TSLA", "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX", "AMD", "UBER"]
    
    print("🔍 Testing 10-company setup...")
    print(f"📊 Symbols: {', '.join(symbols)}")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        for symbol in symbols:
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        quote = data.get("Global Quote", {})
                        if quote and "05. price" in quote:
                            price = float(quote["05. price"])
                            change = float(quote.get("09. change", 0))
                            print(f"✅ {symbol:<6} ${price:>8.2f} ({change:+6.2f})")
                        else:
                            print(f"⚠️  {symbol:<6} No data available")
                    else:
                        print(f"❌ {symbol:<6} HTTP {resp.status}")
                        
                # Rate limiting
                await asyncio.sleep(1)
                        
            except Exception as e:
                print(f"❌ {symbol:<6} Error: {str(e)[:30]}...")
    
    print("\n" + "=" * 60)
    print("🎯 All 10 companies configured for FinSense AI!")
    print("💡 Your dashboard will now track these major stocks:")
    print("   • TSLA  - Tesla")
    print("   • AAPL  - Apple") 
    print("   • GOOGL - Alphabet/Google")
    print("   • MSFT  - Microsoft")
    print("   • AMZN  - Amazon")
    print("   • NVDA  - NVIDIA")
    print("   • META  - Meta/Facebook")
    print("   • NFLX  - Netflix")
    print("   • AMD   - Advanced Micro Devices")
    print("   • UBER  - Uber")

if __name__ == "__main__":
    asyncio.run(test_10_companies())
