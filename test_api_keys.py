#!/usr/bin/env python3
"""
API Key Validation Script for FinSense AI
Tests all configured API keys and real-time data sources
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class APITester:
    def __init__(self):
        self.results = {}
        
    async def test_all(self):
        """Test all configured APIs"""
        print("🔍 Testing API Keys and Real-time Data Sources...")
        print("=" * 60)
        
        # Test AI/LLM APIs
        await self.test_gemini()
        await self.test_openai()
        
        # Test Market Data APIs
        await self.test_alpha_vantage()
        await self.test_finnhub()
        await self.test_polygon()
        
        # Test News API
        await self.test_news_api()
        
        # Print summary
        self.print_summary()
        
    async def test_gemini(self):
        """Test Google Gemini API"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.results["Gemini"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content("Say 'API key is working' in exactly 5 words.")
            if response.text:
                self.results["Gemini"] = {"status": "✅", "message": f"Working - Response: {response.text[:50]}..."}
            else:
                self.results["Gemini"] = {"status": "❌", "message": "No response received"}
                
        except Exception as e:
            self.results["Gemini"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    async def test_openai(self):
        """Test OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.results["OpenAI"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'API working' in 2 words."}],
                max_tokens=10
            )
            
            if response.choices[0].message.content:
                self.results["OpenAI"] = {"status": "✅", "message": f"Working - Response: {response.choices[0].message.content}"}
            else:
                self.results["OpenAI"] = {"status": "❌", "message": "No response received"}
                
        except Exception as e:
            self.results["OpenAI"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    async def test_alpha_vantage(self):
        """Test Alpha Vantage API"""
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            self.results["Alpha Vantage"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TSLA&apikey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        quote = data.get("Global Quote", {})
                        if quote and "05. price" in quote:
                            price = quote["05. price"]
                            self.results["Alpha Vantage"] = {"status": "✅", "message": f"Working - TSLA: ${price}"}
                        else:
                            self.results["Alpha Vantage"] = {"status": "❌", "message": f"Invalid response: {data}"}
                    else:
                        self.results["Alpha Vantage"] = {"status": "❌", "message": f"HTTP {resp.status}"}
                        
        except Exception as e:
            self.results["Alpha Vantage"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    async def test_finnhub(self):
        """Test Finnhub API"""
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            self.results["Finnhub"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://finnhub.io/api/v1/quote?symbol=TSLA&token={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "c" in data and data["c"] > 0:
                            price = data["c"]
                            self.results["Finnhub"] = {"status": "✅", "message": f"Working - TSLA: ${price}"}
                        else:
                            self.results["Finnhub"] = {"status": "❌", "message": f"Invalid response: {data}"}
                    else:
                        self.results["Finnhub"] = {"status": "❌", "message": f"HTTP {resp.status}"}
                        
        except Exception as e:
            self.results["Finnhub"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    async def test_polygon(self):
        """Test Polygon.io API"""
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            self.results["Polygon.io"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.polygon.io/v2/last/trade/TSLA?apikey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", {})
                        if results and "p" in results:
                            price = results["p"]
                            self.results["Polygon.io"] = {"status": "✅", "message": f"Working - TSLA: ${price}"}
                        else:
                            self.results["Polygon.io"] = {"status": "❌", "message": f"Invalid response: {data}"}
                    else:
                        self.results["Polygon.io"] = {"status": "❌", "message": f"HTTP {resp.status}"}
                        
        except Exception as e:
            self.results["Polygon.io"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    async def test_news_api(self):
        """Test NewsAPI"""
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            self.results["NewsAPI"] = {"status": "❌", "message": "No API key configured"}
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://newsapi.org/v2/everything?q=Tesla&sortBy=publishedAt&pageSize=1&apiKey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        if articles:
                            headline = articles[0].get("title", "")[:50]
                            self.results["NewsAPI"] = {"status": "✅", "message": f"Working - Latest: {headline}..."}
                        else:
                            self.results["NewsAPI"] = {"status": "❌", "message": "No articles found"}
                    else:
                        self.results["NewsAPI"] = {"status": "❌", "message": f"HTTP {resp.status}"}
                        
        except Exception as e:
            self.results["NewsAPI"] = {"status": "❌", "message": f"Error: {str(e)[:100]}"}
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 API KEY VALIDATION RESULTS")
        print("=" * 60)
        
        working_count = 0
        total_count = len(self.results)
        
        for api_name, result in self.results.items():
            status = result["status"]
            message = result["message"]
            print(f"{status} {api_name:<15} - {message}")
            if status == "✅":
                working_count += 1
        
        print("\n" + "-" * 60)
        print(f"🎯 Summary: {working_count}/{total_count} APIs working")
        
        if working_count > 0:
            print("✅ Real-time data feeds should work!")
            print("\n📋 To enable real-time mode:")
            print("   $env:REALTIME = '1'")
            print("   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        else:
            print("❌ No APIs configured. Using mock data only.")
        
        print("\n🔑 Get API keys from:")
        print("   • Gemini: https://makersuite.google.com/app/apikey")
        print("   • Alpha Vantage: https://www.alphavantage.co/support/#api-key")
        print("   • Finnhub: https://finnhub.io/register")
        print("   • Polygon: https://polygon.io/")
        print("   • NewsAPI: https://newsapi.org/register")


async def main():
    """Main function"""
    print("🚀 FinSense AI - API Key Validator")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = APITester()
    await tester.test_all()


if __name__ == "__main__":
    asyncio.run(main())
