import os
import asyncio
from typing import List
from .state import AppState, NewsItem
from .utils import classify_sentiment

OPENAI_AVAILABLE = False
GEMINI_AVAILABLE = False

try:
    import openai  # type: ignore
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


async def handle_trading_question(question: str, state: AppState) -> str:
    # Check if this is a general investment question
    general_keywords = [
        "which stock", "what stock", "best stock", "recommend", "should i buy",
        "invest in", "portfolio", "market analysis", "today", "now"
    ]
    
    # Check if this is a price query
    price_keywords = [
        "price", "cost", "value", "worth", "trading at", "current", "now"
    ]
    
    question_lower = question.lower()
    is_general_question = any(keyword in question_lower for keyword in general_keywords)
    is_price_query = any(keyword in question_lower for keyword in price_keywords)
    
    # Find mentioned symbol and get news context
    symbol = _infer_symbol(question, state.symbols)
    news_context = _recent_news_for_symbol(state, symbol, window_secs=600)
    
    # Get current price data if available
    current_price = None
    if symbol and symbol in state.prices:
        current_price = state.prices[symbol]
    
    # For general questions, provide market overview context
    market_context = None
    if is_general_question and not symbol:
        market_context = _get_market_overview(state)

    # Try Gemini first, then OpenAI, then fallback
    if GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        try:
            return await _gemini_answer(question, symbol, news_context, market_context, current_price, is_price_query)
        except Exception as e:
            print(f"Gemini error: {e}")

    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            return await _openai_answer(question, symbol, news_context, market_context, current_price, is_price_query)
        except Exception as e:
            print(f"OpenAI error: {e}")

    print("🤖 Using enhanced fallback responses (AI services unavailable)")

    # Enhanced fallback for different question types
    if is_price_query and symbol and current_price:
        recent_change = ""
        if news_context:
            latest_news = news_context[-1]
            recent_change = f"\n\nRecent News: '{latest_news.headline}' (Sentiment: {latest_news.sentiment})"
        return f"💰 CURRENT PRICE: {symbol} is trading at ${current_price:.2f}{recent_change}\n\nThis reflects real-time market data. Consider market trends and news when making investment decisions.\n\n⚠️ This is not financial advice."
    
    elif is_general_question and not symbol:
        detailed_advice = _enhanced_general_market_advice(state)
        return detailed_advice
    
    elif symbol and news_context:
        item = news_context[-1]
        price_info = f"\nCurrent Price: ${current_price:.2f}" if current_price else ""
        sentiment_guidance = {
            'positive': 'This positive news may indicate potential upward momentum. Consider this alongside broader market trends.',
            'negative': 'This negative news suggests caution may be advised. Evaluate the long-term impact carefully.',
            'neutral': 'This neutral news indicates stable conditions. Monitor for additional developments.'
        }
        guidance = sentiment_guidance.get(item.sentiment, 'Monitor this development carefully.')
        
        return f"📊 {symbol} ANALYSIS:{price_info}\n\nLatest News: '{item.headline}'\nSentiment: {item.sentiment.title()}\n\nAnalysis: {guidance}\n\n⚠️ This is not financial advice. Always do your own research."
    
    elif symbol:
        price_info = f"\nCurrent Price: ${current_price:.2f}" if current_price else ""
        return f"📈 {symbol} STATUS:{price_info}\n\nNo recent news in the last 10 minutes. This could indicate:\n• Stable trading conditions\n• Limited market-moving events\n• Good time to review fundamentals\n\nConsider checking broader market trends and company fundamentals before making investment decisions.\n\n⚠️ This is not financial advice."
    
    else:
        return "🤔 HELP WITH YOUR QUERY:\n\nPlease specify:\n• A stock symbol (e.g., TSLA, AAPL, GOOGL) for specific analysis\n• Ask about 'market conditions' for general market overview\n• Request 'price of [stock]' for current pricing\n\nI can provide current prices, recent news analysis, and market insights to help inform your investment decisions."


def _infer_symbol(question: str, symbols: List[str]) -> str | None:
    q = question.upper()
    for s in symbols:
        if s in q:
            return s
    # Map common company names to symbols
    name_mappings = {
        "TESLA": "TSLA",
        "APPLE": "AAPL", 
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "MICROSOFT": "MSFT",
        "AMAZON": "AMZN",
        "NVIDIA": "NVDA",
        "META": "META",
        "FACEBOOK": "META",
        "NETFLIX": "NFLX",
        "AMD": "AMD",
        "UBER": "UBER"
    }
    
    for name, symbol in name_mappings.items():
        if name in q:
            return symbol
    return None


def _recent_news_for_symbol(state: AppState, symbol: str | None, window_secs: int) -> List[NewsItem]:
    if not symbol:
        return []
    now = state.now_ts()
    return [n for n in state.news if n.symbol == symbol and (now - n.ts) <= window_secs]


def _get_market_overview(state: AppState) -> dict:
    """Get current market overview for general questions"""
    overview = {
        "symbols": [],
        "top_gainers": [],
        "top_losers": [],
        "recent_news": []
    }
    
    # Analyze current prices and changes
    for symbol in state.symbols:
        if symbol in state.prices:
            price = state.prices[symbol]
            # For demo, calculate a simple change (you can enhance this)
            change = ((price % 100) - 50) * 0.1  # Simplified calculation
            change_percent = (change / price) * 100
            
            symbol_data = {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent
            }
            overview["symbols"].append(symbol_data)
            
            if change_percent > 1:
                overview["top_gainers"].append(symbol_data)
            elif change_percent < -1:
                overview["top_losers"].append(symbol_data)
    
    # Sort gainers and losers
    overview["top_gainers"] = sorted(overview["top_gainers"], key=lambda x: x["change_percent"], reverse=True)[:3]
    overview["top_losers"] = sorted(overview["top_losers"], key=lambda x: x["change_percent"])[:3]
    
    # Get recent news
    now = state.now_ts()
    overview["recent_news"] = [n for n in state.news if (now - n.ts) <= 3600][-5:]  # Last hour, max 5
    
    return overview


def _general_market_advice(state: AppState) -> str:
    """Provide general market advice when no specific symbol is mentioned"""
    overview = _get_market_overview(state)
    
    advice_parts = []
    
    if overview["top_gainers"]:
        gainer = overview["top_gainers"][0]
        advice_parts.append(f"📈 {gainer['symbol']} is up {gainer['change_percent']:.1f}% today")
    
    if overview["top_losers"]:
        loser = overview["top_losers"][0]
        advice_parts.append(f"📉 {loser['symbol']} is down {abs(loser['change_percent']):.1f}%")
    
    if overview["recent_news"]:
        recent = overview["recent_news"][-1]
        advice_parts.append(f"📰 Latest: {recent.symbol} - {recent.headline[:60]}...")
    
    if advice_parts:
        return "Based on current market data: " + " | ".join(advice_parts) + "\n\n⚠️ This is not financial advice. Please do your own research before investing."
    else:
        return "Market data is loading. Please try asking about a specific stock like TSLA, AAPL, or GOOGL."


def _enhanced_general_market_advice(state: AppState) -> str:
    """Provide enhanced general market advice with detailed analysis"""
    overview = _get_market_overview(state)
    
    advice_sections = []
    
    # Market momentum analysis
    if overview["top_gainers"] and overview["top_losers"]:
        advice_sections.append("📊 MARKET MOMENTUM ANALYSIS:")
        
        if overview["top_gainers"]:
            gainers_text = ", ".join([f"{g['symbol']} (+{g['change_percent']:.1f}%)" for g in overview["top_gainers"][:3]])
            advice_sections.append(f"🟢 Top Gainers: {gainers_text}")
        
        if overview["top_losers"]:
            losers_text = ", ".join([f"{l['symbol']} ({l['change_percent']:.1f}%)" for l in overview["top_losers"][:3]])
            advice_sections.append(f"🔴 Top Decliners: {losers_text}")
    
    # Investment strategy recommendations
    advice_sections.append("\n💡 INVESTMENT STRATEGY CONSIDERATIONS:")
    
    if len(overview["top_gainers"]) > len(overview["top_losers"]):
        advice_sections.append("• Market showing bullish sentiment - consider growth stocks")
        advice_sections.append("• Monitor momentum stocks for potential breakouts")
    elif len(overview["top_losers"]) > len(overview["top_gainers"]):
        advice_sections.append("• Market showing bearish sentiment - consider defensive positions")
        advice_sections.append("• Look for quality stocks at discounted prices")
    else:
        advice_sections.append("• Mixed market signals - consider balanced portfolio approach")
        advice_sections.append("• Focus on fundamentally strong companies")
    
    # News impact analysis
    if overview["recent_news"]:
        advice_sections.append("\n📰 RECENT NEWS IMPACT:")
        for news in overview["recent_news"][-3:]:
            sentiment_emoji = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
            advice_sections.append(f"{sentiment_emoji.get(news.sentiment, '🟡')} {news.symbol}: {news.headline[:60]}...")
    
    # Cap size recommendation based on question
    advice_sections.append("\n🎯 SMALL CAP vs LARGE CAP ANALYSIS:")
    advice_sections.append("")
    advice_sections.append("LARGE CAP FUNDS:")
    advice_sections.append("✓ More stable and predictable returns")
    advice_sections.append("✓ Lower volatility during market downturns")
    advice_sections.append("✓ Established companies with proven track records")
    advice_sections.append("✓ Better liquidity and easier to buy/sell")
    advice_sections.append("✗ Lower growth potential compared to small caps")
    advice_sections.append("")
    advice_sections.append("SMALL CAP FUNDS:")
    advice_sections.append("✓ Higher growth potential over long term")
    advice_sections.append("✓ Greater opportunity for capital appreciation")
    advice_sections.append("✓ Often undervalued companies with room to grow")
    advice_sections.append("✗ Higher volatility and risk")
    advice_sections.append("✗ Less liquidity, harder to exit quickly")
    advice_sections.append("✗ More sensitive to economic downturns")
    advice_sections.append("")
    advice_sections.append("🎯 RECOMMENDATION:")
    advice_sections.append("For balanced growth and risk management, consider:")
    advice_sections.append("• 70% Large Cap funds (stability and steady growth)")
    advice_sections.append("• 30% Small Cap funds (higher growth potential)")
    advice_sections.append("• Adjust ratio based on your risk tolerance and investment timeline")
    
    result = "\n".join(advice_sections)
    result += "\n\n⚠️ DISCLAIMER: This analysis is based on current market data and is not personalized financial advice. Always consult with a financial advisor and conduct your own research before making investment decisions."
    
    return result


async def _gemini_answer(question: str, symbol: str | None, news: List[NewsItem], market_context: dict = None, current_price: float = None, is_price_query: bool = False) -> str:
    """Generate answer using Google Gemini with enhanced context"""
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    
    sys_prompt = (
        "You are a professional financial trading assistant and market analyst with access to real-time market data. "
        "Provide detailed, informative responses about stocks, market movements, and investment strategies. "
        
        "Response Format Guidelines:"
        "- Use clear section headings in UPPERCASE (e.g., 'PRICE ANALYSIS:', 'INVESTMENT RECOMMENDATION:')"
        "- Use bullet points with • for lists"
        "- Use ✓ for advantages and ✗ for disadvantages"
        "- Use emojis sparingly for visual clarity (📊, 💰, 📈, 📉, ⚠️)"
        "- Avoid markdown formatting like **bold** or _italic_"
        "- Use plain text formatting with clear spacing"

        "Content Requirements:"
        "1. Price Queries: Include current price, recent changes, and brief analysis"
        "2. Investment Advice: Compare options with clear pros/cons and risk analysis"
        "3. Stock Analysis: Include price trends, recent news impact, and technical indicators"
        "4. General Questions: Provide comprehensive market overview with specific recommendations"
        
        "Always translate foreign language news to English, include current prices when available, "
        "and end with appropriate disclaimers about financial advice. Use structured, readable formatting."
    )
    
    ctx_lines = []
    
    # Add current price data if available
    if symbol and current_price:
        ctx_lines.append(f"Current Price Data: {symbol} = ${current_price:.2f}")
    
    # Add specific symbol context if available
    if symbol:
        ctx_lines.append(f"Focused Symbol: {symbol}")
        for n in news[-3:]:
            # Check if headline needs translation
            headline = n.headline
            if _needs_translation(headline):
                ctx_lines.append(f"News[{n.symbol}] @{int(n.ts)}: {headline} (foreign language - please translate) (sentiment={n.sentiment})")
            else:
                ctx_lines.append(f"News[{n.symbol}] @{int(n.ts)}: {headline} (sentiment={n.sentiment})")
    
    # Add market overview for general questions
    if market_context:
        ctx_lines.append("Market Overview:")
        if market_context["top_gainers"]:
            gainers = ", ".join([f"{s['symbol']} (+{s['change_percent']:.1f}%)" for s in market_context["top_gainers"]])
            ctx_lines.append(f"Top Gainers: {gainers}")
        if market_context["top_losers"]:
            losers = ", ".join([f"{s['symbol']} ({s['change_percent']:.1f}%)" for s in market_context["top_losers"]])
            ctx_lines.append(f"Top Losers: {losers}")
        if market_context["recent_news"]:
            ctx_lines.append("Recent News:")
            for n in market_context["recent_news"][-3:]:
                headline = n.headline
                if _needs_translation(headline):
                    ctx_lines.append(f"- {n.symbol}: {headline} (translate to English)")
                else:
                    ctx_lines.append(f"- {n.symbol}: {headline}")
    
    # Special instructions for price queries
    if is_price_query and symbol and current_price:
        ctx_lines.append(f"User is asking for current price information. Current {symbol} price: ${current_price:.2f}")
    
    ctx = "\n".join(ctx_lines) if ctx_lines else "No recent context available."
    
    full_prompt = f"{sys_prompt}\n\nQuestion: {question}\nReal-time Context:\n{ctx}\n\nPlease provide a helpful response with current data when available."
    
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: model.generate_content(full_prompt)
    )
    return response.text or "Unable to generate response."


def _needs_translation(text: str) -> bool:
    """Check if text contains non-Latin characters (likely foreign language)"""
    import re
    # Check for common non-Latin scripts
    if re.search(r'[\u4e00-\u9fff]', text):  # Chinese characters
        return True
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Japanese characters
        return True
    if re.search(r'[\u0400-\u04ff]', text):  # Cyrillic characters
        return True
    if re.search(r'[\u0590-\u05ff]', text):  # Hebrew characters
        return True
    if re.search(r'[\u0600-\u06ff]', text):  # Arabic characters
        return True
    if re.search(r'[\u0900-\u097f]', text):  # Hindi characters
        return True
    return False


async def _openai_answer(question: str, symbol: str | None, news: List[NewsItem], market_context: dict = None, current_price: float = None, is_price_query: bool = False) -> str:
    """Generate answer using OpenAI with enhanced context"""
    client = OpenAI()
    sys = (
        "You are a professional financial trading assistant and market analyst with access to real-time market data. "
        "Provide detailed, structured responses about stocks, market movements, and investment strategies. "
        
        "Response Format Requirements:"
        "- Use clear section headings in UPPERCASE followed by colon"
        "- Use bullet points with • for lists"
        "- Use ✓ for advantages and ✗ for disadvantages"
        "- Use simple emojis for clarity (📊, 💰, 📈, 📉, ⚠️)"
        "- NO markdown formatting (**bold**, _italic_, etc.)"
        "- Use plain text with clear line breaks and spacing"
        
        "Content Structure:"
        "- For price queries: Current price + recent performance + brief analysis"
        "- For investment comparisons: Detailed pros/cons with risk assessment"
        "- For stock analysis: Price data + news impact + market context"
        "- For general advice: Market overview + specific recommendations"
        
        "Always use real-time data when available, translate foreign language news to English, "
        "and include appropriate financial disclaimers. Keep formatting clean and readable."
    )
    
    ctx_lines = []
    
    # Add current price data if available
    if symbol and current_price:
        ctx_lines.append(f"Current Price Data: {symbol} = ${current_price:.2f}")
    
    # Add specific symbol context if available
    if symbol:
        ctx_lines.append(f"Focused Symbol: {symbol}")
        for n in news[-3:]:
            headline = n.headline
            if _needs_translation(headline):
                ctx_lines.append(f"News[{n.symbol}] @{int(n.ts)}: {headline} (foreign language - please translate) (sent={n.sentiment})")
            else:
                ctx_lines.append(f"News[{n.symbol}] @{int(n.ts)}: {headline} (sent={n.sentiment})")
    
    # Add market overview for general questions
    if market_context:
        ctx_lines.append("Market Overview:")
        if market_context["top_gainers"]:
            gainers = ", ".join([f"{s['symbol']} (+{s['change_percent']:.1f}%)" for s in market_context["top_gainers"]])
            ctx_lines.append(f"Top Gainers: {gainers}")
        if market_context["top_losers"]:
            losers = ", ".join([f"{s['symbol']} ({s['change_percent']:.1f}%)" for s in market_context["top_losers"]])
            ctx_lines.append(f"Top Losers: {losers}")
    
    # Special instructions for price queries
    if is_price_query and symbol and current_price:
        ctx_lines.append(f"User is asking for current price information. Current {symbol} price: ${current_price:.2f}")
    
    ctx = "\n".join(ctx_lines) if ctx_lines else "No recent context available."

    msg = [
        {"role": "system", "content": sys},
        {"role": "user", "content": f"Question: {question}\nReal-time Context:\n{ctx}\n\nPlease provide a helpful response with current data when available."},
    ]
    resp = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.chat.completions.create(model="gpt-4o-mini", messages=msg),
    )
    return resp.choices[0].message.content or ""
