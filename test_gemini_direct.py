#!/usr/bin/env python3
"""
Simple Gemini API Test using the REST API method
Tests the Gemini API key directly via HTTP request
"""

import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gemini_rest_api():
    """Test Gemini API using direct REST API call"""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    if not api_key:
        print("❌ No GOOGLE_API_KEY found in .env file")
        return
    
    print(f"🔑 Testing Gemini API Key: {api_key[:10]}...")
    print(f"📱 Using Model: {model}")
    print("-" * 50)
    
    # Prepare the request data
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Explain how AI works in a few words"
                    }
                ]
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print("📡 Sending request to Gemini API...")
            
            async with session.post(url, headers=headers, json=data) as response:
                print(f"📊 Response Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract the response text
                    if 'candidates' in result and result['candidates']:
                        candidate = result['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            text = candidate['content']['parts'][0]['text']
                            print("✅ SUCCESS! Gemini API is working")
                            print(f"🤖 AI Response: {text}")
                            return True
                    
                    print("❌ Unexpected response format:")
                    print(json.dumps(result, indent=2))
                    return False
                
                else:
                    # Print error details
                    error_text = await response.text()
                    print(f"❌ API Error ({response.status}):")
                    print(error_text)
                    return False
                    
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return False

async def test_with_trading_question():
    """Test with a trading-related question"""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    if not api_key:
        return
    
    print("\n" + "=" * 50)
    print("🔄 Testing with Trading Question...")
    print("=" * 50)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Why is Tesla stock volatile? Give me 2-3 key reasons in simple terms."
                    }
                ]
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    if 'candidates' in result and result['candidates']:
                        candidate = result['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            text = candidate['content']['parts'][0]['text']
                            print("✅ Trading Question Response:")
                            print(f"🎯 {text}")
                            return True
                    
                    print("❌ No valid response received")
                    return False
                
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🚀 Gemini API Direct Test")
    print("=" * 50)
    
    # Test 1: Basic API functionality
    basic_test = await test_gemini_rest_api()
    
    # Test 2: Trading-specific question
    if basic_test:
        trading_test = await test_with_trading_question()
        
        print("\n" + "=" * 50)
        print("📋 SUMMARY")
        print("=" * 50)
        
        if basic_test and trading_test:
            print("✅ Gemini API is working perfectly!")
            print("✅ Ready for FinSense AI integration")
            print("\n🚀 Your FinSense AI app should work with Gemini!")
            print("💡 Run the server with: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        else:
            print("⚠️  Basic test passed but trading question failed")
    else:
        print("\n❌ Gemini API test failed")
        print("🔧 Check your API key at: https://makersuite.google.com/app/apikey")

if __name__ == "__main__":
    asyncio.run(main())
