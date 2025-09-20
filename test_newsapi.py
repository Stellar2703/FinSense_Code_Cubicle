#!/usr/bin/env python3
"""
Test script to check NewsAPI functionality
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_newsapi():
    """Test NewsAPI directly"""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print("❌ No NEWS_API_KEY found in environment")
        return False
    
    print(f"🔑 Using NewsAPI key: {api_key[:10]}...")
    
    # Test symbols
    symbols = ["TSLA", "AAPL", "GOOGL", "MSFT", "AMZN"]
    symbols_query = " OR ".join(symbols)
    
    url = f"https://newsapi.org/v2/everything?q=({symbols_query}) AND (stock OR market OR earnings OR trading)&sortBy=publishedAt&pageSize=10&apiKey={api_key}"
    
    print(f"🌐 Testing NewsAPI URL...")
    print(f"Query: ({symbols_query}) AND (stock OR market OR earnings OR trading)")
    
    try:
        async with aiohttp.ClientSession() as session:
            print("📡 Making request to NewsAPI...")
            async with session.get(url) as resp:
                print(f"📊 Response status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    articles = data.get("articles", [])
                    total_results = data.get("totalResults", 0)
                    
                    print(f"✅ NewsAPI working!")
                    print(f"📰 Total results available: {total_results}")
                    print(f"📰 Articles returned: {len(articles)}")
                    
                    if articles:
                        print("\n📑 First few articles:")
                        for i, article in enumerate(articles[:3]):
                            title = article.get("title", "No title")
                            source = article.get("source", {}).get("name", "Unknown")
                            published = article.get("publishedAt", "Unknown")
                            print(f"  {i+1}. [{source}] {title[:80]}...")
                            print(f"     Published: {published}")
                    
                    return True
                else:
                    print(f"❌ NewsAPI error: HTTP {resp.status}")
                    error_text = await resp.text()
                    print(f"Error details: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def test_specific_company_news():
    """Test news for specific companies"""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return False
    
    companies = ["Tesla", "Apple", "Google", "Microsoft", "Amazon"]
    
    for company in companies:
        try:
            url = f"https://newsapi.org/v2/everything?q={company}&sortBy=publishedAt&pageSize=3&apiKey={api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        print(f"\n🏢 {company} news: {len(articles)} articles")
                        
                        for article in articles[:2]:
                            title = article.get("title", "No title")
                            print(f"  • {title[:60]}...")
                    else:
                        print(f"❌ Error getting {company} news: HTTP {resp.status}")
                        
        except Exception as e:
            print(f"❌ Error getting {company} news: {e}")

async def main():
    print("🧪 Testing NewsAPI functionality...\n")
    
    # Test main NewsAPI functionality
    newsapi_works = await test_newsapi()
    
    if newsapi_works:
        print("\n" + "="*50)
        # Test specific company news
        await test_specific_company_news()
    
    print("\n" + "="*50)
    print("🏁 NewsAPI test completed")

if __name__ == "__main__":
    asyncio.run(main())
