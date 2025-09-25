import os
import asyncio
import json
from typing import List, Dict, Any
from .state import AppState, NewsItem
from .utils import classify_sentiment
from .pathway_pipelines import is_available as pathway_available
from .trading_buddy_ai import _enhanced_gemini_answer, _enhanced_openai_answer

"""
Trading Buddy - AI-powered financial assistant

This module handles the processing of user queries about financial markets, stocks, 
and investment strategies. It uses a combination of AI services (when available) and
fallback rule-based responses to provide helpful information.

NOTE ON FORMATTING:
All response handlers use multi-line string literals (triple quotes) for proper formatting.
This ensures that newlines appear correctly in the UI and no raw \n characters are shown.
Always use this pattern when creating or modifying response handlers:

def _handle_some_question():
    return f\"\"\"Your formatted response here
    With proper line breaks
    And consistent spacing\"\"\"
"""

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


def _is_greeting(question: str) -> bool:
    """Detect if the message is a simple greeting"""
    greeting_phrases = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening", 
        "greetings", "howdy", "hola", "yo", "sup", "what's up", "what up"
    ]
    
    question = question.lower().strip()
    
    # Check for exact matches
    if question in greeting_phrases:
        return True
        
    # Check for greetings with small additions
    for greeting in greeting_phrases:
        if question.startswith(greeting + " ") or question == greeting:
            return True
            
    return False
    

def _handle_greeting() -> str:
    """Respond to a greeting message with a personalized response"""
    return """👋 Hello! I'm your financial assistant, here to help with market information and trading insights.

You can ask me about:
• Stock prices and trends
• Market analysis and news
• Trading strategies and insights
• Portfolio suggestions

How can I assist with your financial questions today?"""


async def handle_trading_question(question: str, state: AppState) -> str:
    """Enhanced trading assistant with comprehensive question handling"""
    
    # Check if the message is a greeting first
    if _is_greeting(question):
        return _handle_greeting()
    
    # Categorize question types for better responses
    question_lower = question.lower()
    
    # Enhanced keyword categorization
    price_keywords = ["price", "cost", "value", "worth", "trading at", "current", "now", "how much"]
    buy_sell_keywords = ["buy", "sell", "purchase", "invest", "trade", "should i", "recommend"]
    analysis_keywords = ["analysis", "analyze", "opinion", "thoughts", "prediction", "forecast", "outlook"]
    strategy_keywords = ["strategy", "approach", "plan", "portfolio", "diversify", "allocation"]
    risk_keywords = ["risk", "safe", "dangerous", "volatile", "stable", "loss", "profit"]
    market_keywords = ["market", "economy", "sector", "industry", "trend", "conditions"]
    timing_keywords = ["when", "timing", "now", "today", "tomorrow", "best time"]
    comparison_keywords = ["vs", "versus", "compare", "better", "best", "worst"]
    movers_keywords = ["top movers", "movers", "gainers", "losers", "performers", "winners", "biggest moves", "best stocks", "worst stocks"]
    help_keywords = ["help", "explain", "what is", "how to", "understand", "basics", "guide", "tutorial"]
    
    # Enhanced investment keyword detection
    invest_patterns = ["invest in", "buy now", "good investment", "should i buy", "can i invest", "worth buying"]
    
    # Determine question category
    is_price_query = any(keyword in question_lower for keyword in price_keywords)
    is_buy_sell = any(keyword in question_lower for keyword in buy_sell_keywords) or any(pattern in question_lower for pattern in invest_patterns)
    is_analysis = any(keyword in question_lower for keyword in analysis_keywords)
    is_strategy = any(keyword in question_lower for keyword in strategy_keywords)
    is_risk = any(keyword in question_lower for keyword in risk_keywords)
    is_market = any(keyword in question_lower for keyword in market_keywords)
    is_timing = any(keyword in question_lower for keyword in timing_keywords)
    is_comparison = any(keyword in question_lower for keyword in comparison_keywords)
    is_movers = any(keyword in question_lower for keyword in movers_keywords)
    is_help = any(keyword in question_lower for keyword in help_keywords)
    
    # Enhanced pattern detection - Check for specific investment questions about stocks
    specific_investment_patterns = [
        "can i invest in", "should i invest in", "is it good to invest in",
        "buy", "invest", "purchase", "worth buying", "good investment"
    ]
    is_specific_investment_question = False
    for pattern in specific_investment_patterns:
        if pattern in question_lower:
            is_specific_investment_question = True
            break
    
    # Find mentioned symbols
    symbols_mentioned = _extract_all_symbols(question, state.symbols)
    primary_symbol = symbols_mentioned[0] if symbols_mentioned else None
    
    # Special case for "can i invest in appl today" or similar
    if is_specific_investment_question and not primary_symbol:
        # Check for common typos and company names directly in the question
        common_typos = {"appl": "AAPL", "goog": "GOOGL", "msft": "MSFT"}
        company_names = {"apple": "AAPL", "google": "GOOGL", "microsoft": "MSFT", "amazon": "AMZN"}
        
        for typo, symbol in common_typos.items():
            if typo in question_lower and symbol not in symbols_mentioned:
                symbols_mentioned.append(symbol)
                primary_symbol = symbol
                break
        
        if not primary_symbol:
            for company, symbol in company_names.items():
                if company in question_lower and symbol not in symbols_mentioned:
                    symbols_mentioned.append(symbol)
                    primary_symbol = symbol
                    break
    
    # Get market context
    news_context = []
    current_prices = {}
    if primary_symbol:
        news_context = _recent_news_for_symbol(state, primary_symbol, window_secs=1800)  # 30 min window
        current_prices[primary_symbol] = state.prices.get(primary_symbol, 0)
    
    # For multiple symbols or general questions
    if len(symbols_mentioned) > 1 or not primary_symbol:
        for symbol in symbols_mentioned[:3]:  # Limit to 3 symbols
            current_prices[symbol] = state.prices.get(symbol, 0)
        if not primary_symbol:
            # Get general market context
            market_overview = _get_comprehensive_market_overview(state)
        
    # Try AI services first
    if GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        try:
            return await _enhanced_gemini_answer(question, symbols_mentioned, news_context, current_prices, state)
        except Exception as e:
            print(f"Gemini error: {e}")

    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            return await _enhanced_openai_answer(question, symbols_mentioned, news_context, current_prices, state)
        except Exception as e:
            print(f"OpenAI error: {e}")

    print("🤖 Using enhanced fallback responses (AI services unavailable)")

    # Handle the specific case for "can i invest in appl" type questions 
    if is_specific_investment_question and primary_symbol:
        # Force this to be handled as a buy/sell question regardless of other conditions
        return _handle_buy_sell_question(primary_symbol, current_prices, news_context, question_lower, state)
    
    # Comprehensive fallback responses based on question type
    if is_comparison and len(symbols_mentioned) >= 2:
        return _handle_comparison_question(symbols_mentioned, current_prices, news_context, state)
    
    elif is_buy_sell:
        return _handle_buy_sell_question(primary_symbol, current_prices, news_context, question_lower, state)
    
    elif is_price_query and primary_symbol:
        return _handle_price_question(primary_symbol, current_prices, news_context, state)
    
    elif is_analysis and primary_symbol:
        return _handle_analysis_question(primary_symbol, current_prices, news_context, state)
    
    elif is_strategy or "portfolio" in question_lower:
        # Check if it's a portfolio analysis question
        portfolio_check_keywords = ["my portfolio", "portfolio perform", "how is my", "portfolio doing"]
        if any(keyword in question_lower for keyword in portfolio_check_keywords):
            # Get portfolio data from state
            portfolio_data = {}
            if state.portfolio and state.portfolio.holdings:
                # Build portfolio dict from state
                total_value = 0
                total_pl = 0
                holdings_with_data = {}
                
                for symbol, quantity in state.portfolio.holdings.items():
                    current_price = state.prices.get(symbol, 0)
                    current_value = quantity * current_price
                    total_value += current_value
                    
                    # Calculate cost basis (simplified - would need transaction history for real cost basis)
                    avg_cost = current_price * 0.9  # Assume 10% gain for demo
                    holdings_with_data[symbol] = {
                        'shares': quantity,
                        'cost_basis': avg_cost
                    }
                    total_pl += current_value - (quantity * avg_cost)
                
                portfolio_data = {
                    'holdings': holdings_with_data,
                    'total_value': total_value,
                    'cash_balance': state.portfolio.cash_balance,
                    'total_pl': total_pl
                }
                
            return _handle_portfolio_question(portfolio_data, question, state)
        else:
            return _handle_strategy_question(symbols_mentioned, current_prices, state)
    
    elif is_risk:
        return _handle_risk_question(primary_symbol, current_prices, news_context, state)
    
    elif is_timing:
        return _handle_timing_question(primary_symbol, current_prices, news_context, state)
    
    elif is_movers:
        return _handle_top_movers_question(state)
    
    elif is_help:
        return _handle_help_question()
        
    # If the question is very short (less than 5 characters), treat it as a help request
    elif len(question.strip()) < 5:
        return _handle_greeting()
    
    elif is_market or not primary_symbol:
        return _handle_market_question(state)
    
    elif primary_symbol:
        return _handle_general_symbol_question(primary_symbol, current_prices, news_context, state)
    
    else:
        return _handle_help_question()


def _extract_all_symbols(question: str, symbols: List[str]) -> List[str]:
    """Extract all mentioned symbols from question"""
    q = question.upper()
    found_symbols = []
    
    # Process the question to handle commas and punctuation for cleaner extraction
    q_clean = ''.join([c if c.isalnum() or c.isspace() else ' ' for c in q])
    q_words = q_clean.split()
    
    # Check for direct symbol mentions
    for s in symbols:
        if s in q_words or s in q:
            found_symbols.append(s)
        # Special case for single character symbols
        elif len(s) == 1 and s in q and not s.isalnum():
            found_symbols.append(s)
    
    # Map common company names to symbols
    name_mappings = {
        "TESLA": "TSLA", "APPLE": "AAPL", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
        "MICROSOFT": "MSFT", "AMAZON": "AMZN", "NVIDIA": "NVDA", "META": "META",
        "FACEBOOK": "META", "NETFLIX": "NFLX", "AMD": "AMD", "UBER": "UBER"
    }
    
    # Common abbreviations, alternate spellings and typos
    common_variants = {
        "APPL": "AAPL",  # Common typo for Apple
        "GOOG": "GOOGL", # Google alternate ticker
        "FB": "META",    # Old Facebook ticker
        "TSLA": "TSLA",  # Tesla
        "MSFT": "MSFT",  # Microsoft
        "AMZN": "AMZN",  # Amazon
        "NVDA": "NVDA",  # NVIDIA
        "NFLX": "NFLX",  # Netflix
        "TWTR": "META",  # Twitter (now part of Meta in this fictional scenario)
        "INTC": "INTC"   # Intel
    }
    
    # Check for company names
    for name, symbol in name_mappings.items():
        if name in q and symbol not in found_symbols:
            found_symbols.append(symbol)
    
    # Check for variants/typos - look for words that match our variants
    for variant, symbol in common_variants.items():
        if variant in q_words and symbol not in found_symbols:
            found_symbols.append(symbol)
        # Special check for the APPL typo anywhere in the text
        elif variant == "APPL" and variant in q and symbol not in found_symbols:
            found_symbols.append(symbol)
    
    # Special check for "apple" (lowercase) in query
    if "apple" in question.lower() and "AAPL" not in found_symbols:
        found_symbols.append("AAPL")
    
    # Handle special case for comma-separated lists of symbols (e.g., "AAPL, MSFT, and GOOGL")
    import re
    comma_separated = re.findall(r'([A-Z]{1,5})(?:,|\s+and\s+|\s+vs\.?\s+|\s+versus\s+)', q)
    for potential_symbol in comma_separated:
        if potential_symbol in symbols and potential_symbol not in found_symbols:
            found_symbols.append(potential_symbol)
    
    # If no symbols found but query contains "invest in" or "buy" + some text, try to extract that text
    if not found_symbols:
        invest_patterns = [
            r"invest\s+in\s+([a-zA-Z]+)",
            r"buy\s+([a-zA-Z]+)",
            r"purchase\s+([a-zA-Z]+)",
            r"trading\s+of\s+([a-zA-Z]+)",
            r"shares\s+of\s+([a-zA-Z]+)",
            r"about\s+([a-zA-Z]+)\s+stock",
            r"([a-zA-Z]+)\s+shares",
            r"([a-zA-Z]+)\s+stock"
        ]
        
        for pattern in invest_patterns:
            matches = re.findall(pattern, question.lower())
            if matches:
                company_name = matches[0].upper()
                # First check if it's a known ticker
                if company_name in symbols:
                    found_symbols.append(company_name)
                # Then check if it's a known company name
                elif company_name in name_mappings:
                    found_symbols.append(name_mappings[company_name])
                # Then check if it's a variant
                elif company_name in common_variants:
                    found_symbols.append(common_variants[company_name])
                # Special case for common companies
                elif company_name == "APPLE":
                    found_symbols.append("AAPL")
    
    # Special check for investment questions with potential company mentions
    if not found_symbols and any(term in question.lower() for term in ["invest", "buy", "purchase"]):
        # Check for mentions of big companies that might not be formatted as tickers
        potential_companies = ["apple", "amazon", "google", "microsoft", "tesla", "meta", "nvidia"]
        for company in potential_companies:
            if company in question.lower():
                symbol = name_mappings.get(company.upper())
                if symbol and symbol not in found_symbols:
                    found_symbols.append(symbol)
    
    return found_symbols

def _handle_comparison_question(symbols: List[str], prices: dict, news: List, state: AppState) -> str:
    """Handle stock comparison questions"""
    if len(symbols) < 2:
        return _handle_help_question()
    
    comparison = f"📊 STOCK COMPARISON: {' vs '.join(symbols)}\n\n"
    
    for symbol in symbols[:3]:  # Limit to 3 stocks
        price = prices.get(symbol, 0)
        symbol_news = [n for n in news if n.symbol == symbol]
        latest_sentiment = symbol_news[-1].sentiment if symbol_news else "neutral"
        
        # Calculate simple performance metrics
        price_change = ((price % 100) - 50) * 0.02  # Mock calculation
        change_percent = (price_change / price) * 100 if price > 0 else 0
        
        comparison += f"🏢 {symbol}:\n"
        comparison += f"   Price: ${price:.2f} ({'+' if change_percent >= 0 else ''}{change_percent:.1f}%)\n"
        comparison += f"   Sentiment: {latest_sentiment.title()}\n"
        comparison += f"   News: {'Recent activity' if symbol_news else 'Quiet period'}\n\n"
    
    comparison += "💡 COMPARISON INSIGHTS:\n"
    best_performer = max(symbols[:3], key=lambda s: prices.get(s, 0))
    comparison += f"• Highest price: {best_performer} (${prices.get(best_performer, 0):.2f})\n"
    comparison += f"• Consider diversification across different sectors\n"
    comparison += f"• Monitor news sentiment for all positions\n"
    comparison += f"• Review fundamentals before making decisions\n\n"
    comparison += "⚠️ This comparison is based on current data. Conduct thorough research before investing."
    
    return comparison

def _handle_buy_sell_question(symbol: str, prices: dict, news: List, question: str, state: AppState) -> str:
    """Handle buy/sell recommendation questions"""
    if not symbol:
        return _handle_strategy_question([], prices, state)
    
    # Handle common stock abbreviation errors
    if symbol == "APPL":
        symbol = "AAPL"  # Fix common typo for Apple
    
    price = prices.get(symbol, 0)
    symbol_news = [n for n in news if n.symbol == symbol]
    sentiment = symbol_news[-1].sentiment if symbol_news else "neutral"
    
    # Calculate trend based on price (using a mock calculation here)
    price_change = ((price % 100) - 50) * 0.02  # Mock calculation
    change_percent = (price_change / price) * 100 if price > 0 else 0
    trend = "rising" if change_percent > 0 else "falling" if change_percent < 0 else "stable"
    
    # Map symbols to company names for more natural responses
    company_names = {
        "AAPL": "Apple", "GOOGL": "Google", "MSFT": "Microsoft", 
        "AMZN": "Amazon", "TSLA": "Tesla", "NVDA": "NVIDIA",
        "META": "Meta", "NFLX": "Netflix", "AMD": "AMD", "UBER": "Uber"
    }
    
    company_name = company_names.get(symbol, symbol)
    
    # Use multi-line strings to maintain proper formatting
    response = f"""🎯 {company_name} ({symbol}) INVESTMENT ANALYSIS

Current Price: ${price:.2f} ({'+' if change_percent >= 0 else ''}{change_percent:.1f}%)
Market Sentiment: {sentiment.title()}
Recent Trend: {trend.title()}
"""
    
    # Generic investing question or specific "buy" question
    invest_keywords = ["invest", "buy", "purchase", "should i"]
    if any(keyword in question.lower() for keyword in invest_keywords):
        response += f"""
📈 {company_name.upper()} INVESTMENT CONSIDERATIONS:"""
        
        # Tailor response based on actual price trend and sentiment
        if sentiment == "positive" and change_percent > 0:
            response += f"""
• {company_name} shows positive momentum with recent price increases
• News sentiment is currently positive
• Technical indicators suggest continued strength

💡 POTENTIAL STRATEGY:
• Consider buying {symbol} with a phased approach (partial position now)
• Set a stop-loss at 5-8% below current price
• Monitor upcoming earnings announcements"""
            
        elif sentiment == "negative" or change_percent < -2:
            response += f"""
• {company_name} is currently showing some weakness"""
            if sentiment == "negative":
                response += """
• Recent news sentiment is negative"""
            if change_percent < 0:
                response += f"""
• Price has declined {abs(change_percent):.1f}% recently

💡 POTENTIAL STRATEGY:
• Consider waiting for stabilization before entering
• Watch for support levels around ${price * 0.95:.2f}
• Look for improving sentiment and volume patterns"""
            
        else:
            response += f"""
• {company_name} is showing mixed signals currently
• Price action is {trend} with {sentiment} sentiment
• Current market conditions suggest caution

💡 POTENTIAL STRATEGY:
• Consider a smaller position size (2-3% of portfolio)
• Use dollar-cost averaging to build position over time
• Set clear entry/exit criteria based on your research"""
        
        response += """

⚠️ RISK MANAGEMENT:
• Never invest more than you can afford to lose
• Consider market and sector risks alongside company-specific factors
• Review the company's financial statements and competitive position"""
    
    # Sell question
    elif "sell" in question.lower():
        response += f"""
📉 SELL CONSIDERATIONS:
Position evaluation needed:
• Current price: ${price:.2f} vs your cost basis
• Recent trend: {trend.title()}
• Market sentiment: {sentiment.title()}

💡 POTENTIAL SELL STRATEGIES:
• If in profit: Consider taking partial profits
• If at a loss: Evaluate if fundamentals have changed
• Consider tax implications of selling
• Review your original investment thesis"""
    
    response += f"""

🔍 MONITORING POINTS FOR {symbol}:"""
    if symbol_news:
        response += f"""
• Recent news: {symbol_news[-1].headline[:60]}..."""
    response += """
• Upcoming earnings and product announcements
• Industry trends and competitive positioning
• Overall market conditions and sector performance

⚠️ This analysis is for educational purposes only. Please consult a financial advisor before making investment decisions."""
    
    return response

def _handle_price_question(symbol: str, prices: dict, news: List, state: AppState) -> str:
    """Handle price-related questions"""
    price = prices.get(symbol, 0)
    symbol_news = [n for n in news if n.symbol == symbol]
    
    # Mock price history analysis
    price_change = ((price % 100) - 50) * 0.02
    change_percent = (price_change / price) * 100 if price > 0 else 0
    
    # Calculate support and resistance levels
    support = price * 0.95
    resistance = price * 1.05
    
    # Use multi-line string to maintain proper formatting
    response = f"""💰 {symbol} PRICE ANALYSIS

Current Price: ${price:.2f}
Recent Change: {'+' if price_change >= 0 else ''}${price_change:.2f} ({'+' if change_percent >= 0 else ''}{change_percent:.1f}%)
"""
    
    if symbol_news:
        latest = symbol_news[-1]
        response += f"""
📰 Latest News Impact:
Headline: {latest.headline[:100]}...
Sentiment: {latest.sentiment.title()}
"""
    
    response += f"""
📊 PRICE LEVELS TO WATCH:
• Support Level: ${support:.2f} (-5%)
• Current Price: ${price:.2f}
• Resistance Level: ${resistance:.2f} (+5%)

🎯 TRADING CONSIDERATIONS:
• Volume analysis needed
• Technical indicators review
• Market trend alignment
• News catalyst monitoring

⚠️ Prices are real-time but analysis is educational only."""
    
    return response

def _handle_analysis_question(symbol: str, prices: dict, news: List, state: AppState) -> str:
    """Handle detailed analysis questions"""
    price = prices.get(symbol, 0)
    symbol_news = [n for n in news if n.symbol == symbol]
    
    # Mock technical analysis
    ma_20 = price * 0.98  # Simplified moving average
    rsi = 45 + (price % 20)  # Mock RSI
    
    # Use multi-line string to maintain proper formatting
    response = f"""🔍 {symbol} COMPREHENSIVE ANALYSIS

💹 PRICE METRICS:
Current: ${price:.2f}
20-day MA: ${ma_20:.2f} ({'Above' if price > ma_20 else 'Below'})
RSI: {rsi:.0f} ({'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'})

📰 NEWS SENTIMENT ANALYSIS:"""
    
    if symbol_news:
        positive = sum(1 for n in symbol_news if n.sentiment == 'positive')
        negative = sum(1 for n in symbol_news if n.sentiment == 'negative')
        neutral = len(symbol_news) - positive - negative
        
        response += f"""
Recent articles: {len(symbol_news)}
• Positive: {positive} • Neutral: {neutral} • Negative: {negative}
Overall sentiment: {'Bullish' if positive > negative else 'Bearish' if negative > positive else 'Mixed'}"""
    else:
        response += """
No recent news - monitoring period"""
    
    # Investment thesis
    response += f"""

💡 INVESTMENT THESIS:
Strengths:
• Market position in sector
• Recent price stability
• {'Positive' if symbol_news and symbol_news[-1].sentiment == 'positive' else 'Stable'} news flow

Risks:
• Market volatility
• Sector-specific challenges
• Economic headwinds

🎯 RECOMMENDATION:
• Rating: {'BUY' if rsi < 50 else 'HOLD' if rsi < 60 else 'SELL'} (Based on current metrics)
• Time horizon: Medium to long-term
• Position sizing: Conservative (2-5% of portfolio)

⚠️ This analysis is for educational purposes. Consult a financial advisor for personalized advice."""
    
    return response

def _handle_strategy_question(symbols: List[str], prices: dict, state: AppState) -> str:
    """Handle portfolio strategy questions"""
    response = """🎯 PORTFOLIO STRATEGY GUIDANCE

💼 DIVERSIFICATION PRINCIPLES:
• Spread risk across sectors
• Mix of growth and value stocks
• Consider market cap diversity
• Geographic diversification

📊 PORTFOLIO ALLOCATION EXAMPLE:
• Large-cap stocks: 40-50%
• Mid-cap stocks: 20-30%
• Small-cap stocks: 10-20%
• Cash reserves: 5-10%
"""
    
    if symbols:
        response += f"""
🏢 MENTIONED STOCKS STRATEGY:"""
        for symbol in symbols[:3]:
            price = prices.get(symbol, 0)
            response += f"""
• {symbol}: ${price:.2f} - Consider 2-5% allocation max"""
    
    response += """

⚖️ RISK MANAGEMENT:
• Never invest more than you can afford to lose
• Set stop-losses at 5-10% below entry
• Take profits at 20-30% gains
• Regular portfolio rebalancing

📅 TIMING STRATEGIES:
• Dollar-cost averaging for regular investments
• Buy dips in quality companies
• Avoid emotional trading
• Monitor earnings seasons

⚠️ These are general guidelines. Your strategy should align with your risk tolerance and investment goals."""
    
    return response

def _handle_risk_question(symbol: str, prices: dict, news: List, state: AppState) -> str:
    """Handle risk assessment questions"""
    response = "⚠️ RISK ASSESSMENT ANALYSIS\n\n"
    
    if symbol:
        price = prices.get(symbol, 0)
        response += f"🏢 {symbol} RISK PROFILE:\n"
        response += f"Current Price: ${price:.2f}\n\n"
        
        # Mock volatility calculation
        volatility = (price % 10) + 15  # Mock volatility 15-25%
        risk_level = "High" if volatility > 22 else "Medium" if volatility > 18 else "Low"
        
        response += f"📊 RISK METRICS:\n"
        response += f"• Volatility: {volatility:.1f}% ({risk_level} Risk)\n"
        response += f"• Sector Risk: Technology sector exposure\n"
        response += f"• Market Cap Risk: {'Large-cap (Lower)' if price > 300 else 'Mid-cap (Medium)' if price > 100 else 'Small-cap (Higher)'}\n\n"
    
    response += "🛡️ GENERAL RISK FACTORS:\n"
    response += "• Market Risk: Overall market downturns\n"
    response += "• Company Risk: Business-specific challenges\n"
    response += "• Sector Risk: Industry disruption\n"
    response += "• Economic Risk: Recession, inflation\n"
    response += "• Political Risk: Regulatory changes\n\n"
    
    response += "💡 RISK MITIGATION STRATEGIES:\n"
    response += "• Diversification across stocks/sectors\n"
    response += "• Position sizing (max 5% per stock)\n"
    response += "• Stop-loss orders\n"
    response += "• Regular portfolio review\n"
    response += "• Emergency cash reserves\n\n"
    
    response += "📋 RISK TOLERANCE ASSESSMENT:\n"
    response += "Ask yourself:\n"
    response += "• Can I afford to lose this money?\n"
    response += "• What's my investment timeline?\n"
    response += "• How do I react to losses?\n"
    response += "• What are my financial goals?\n\n"
    
    response += "⚠️ Only invest what you can afford to lose. Consider your personal financial situation."
    
    return response

def _handle_timing_question(symbol: str, prices: dict, news: List, state: AppState) -> str:
    """Handle market timing questions"""
    response = "⏰ MARKET TIMING ANALYSIS\n\n"
    
    if symbol:
        price = prices.get(symbol, 0)
        symbol_news = [n for n in news if n.symbol == symbol]
        
        response += f"🎯 {symbol} TIMING SIGNALS:\n"
        response += f"Current Price: ${price:.2f}\n"
        
        # Mock timing indicators
        momentum = "Positive" if (price % 10) > 5 else "Negative"
        volume_trend = "High" if (price % 7) > 3 else "Normal"
        
        response += f"• Price Momentum: {momentum}\n"
        response += f"• Volume Trend: {volume_trend}\n"
        response += f"• News Flow: {'Active' if symbol_news else 'Quiet'}\n\n"
        
        response += f"📊 ENTRY/EXIT SIGNALS:\n"
        if momentum == "Positive":
            response += "✓ Potential buy signals:\n"
            response += "  • Upward price trend\n"
            response += "  • Above moving averages\n"
        else:
            response += "⚠️ Caution signals:\n"
            response += "  • Downward pressure\n"
            response += "  • Below key levels\n"
        response += "\n"
    
    response += "⌚ GENERAL TIMING PRINCIPLES:\n"
    response += "• Time in market > Timing the market\n"
    response += "• Dollar-cost averaging reduces timing risk\n"
    response += "• Buy quality companies during dips\n"
    response += "• Avoid panic buying/selling\n\n"
    
    response += "📅 MARKET TIMING FACTORS:\n"
    response += "• Earnings seasons (quarterly)\n"
    response += "• Economic data releases\n"
    response += "• Federal Reserve meetings\n"
    response += "• Seasonal trends\n"
    response += "• Market sentiment shifts\n\n"
    
    response += "🎯 TIMING STRATEGIES:\n"
    response += "• DCA (Dollar Cost Averaging): Regular investments\n"
    response += "• Value Averaging: Buy more when prices drop\n"
    response += "• Trend Following: Ride momentum\n"
    response += "• Contrarian: Buy fear, sell greed\n\n"
    
    response += "⚠️ Perfect timing is impossible. Focus on consistent, disciplined investing."
    
    return response

def _handle_top_movers_question(state: AppState) -> str:
    """Handle top movers/gainers/losers questions"""
    response = "🚀 TOP MARKET MOVERS\n\n"
    
    # Get comprehensive market data
    market_data = _get_comprehensive_market_overview(state)
    
    if not market_data["symbols"]:
        response += "❌ No market data available. Please try again later.\n"
        return response
    
    # Top gainers
    response += "📈 TOP GAINERS:\n"
    if market_data["top_gainers"]:
        for i, stock in enumerate(market_data["top_gainers"], 1):
            change_symbol = "+" if stock["change_percent"] >= 0 else ""
            response += f"{i}. {stock['symbol']}: ${stock['price']:.2f} ({change_symbol}{stock['change_percent']:.1f}%)\n"
    else:
        response += "No significant gainers today\n"
    
    response += "\n📉 TOP LOSERS:\n"
    if market_data["top_losers"]:
        for i, stock in enumerate(market_data["top_losers"], 1):
            response += f"{i}. {stock['symbol']}: ${stock['price']:.2f} ({stock['change_percent']:.1f}%)\n"
    else:
        response += "No significant losers today\n"
    
    # Overall market summary
    total_up = sum(1 for s in market_data["symbols"] if s["change_percent"] > 0)
    total_down = sum(1 for s in market_data["symbols"] if s["change_percent"] < 0)
    total_flat = len(market_data["symbols"]) - total_up - total_down
    
    response += f"\n📊 MARKET SUMMARY:\n"
    response += f"• Total Stocks Tracked: {len(market_data['symbols'])}\n"
    response += f"• Rising: {total_up} stocks\n"
    response += f"• Falling: {total_down} stocks\n"
    response += f"• Unchanged: {total_flat} stocks\n"
    
    # Market sentiment
    if total_up > total_down:
        sentiment = "🟢 Bullish"
    elif total_down > total_up:
        sentiment = "🔴 Bearish"
    else:
        sentiment = "🟡 Mixed"
    
    response += f"• Market Sentiment: {sentiment}\n\n"
    
    # Recent news affecting movers
    if market_data["recent_news"]:
        response += "📰 RECENT NEWS IMPACT:\n"
        for news_item in market_data["recent_news"][-3:]:
            symbol = news_item.symbol or "MARKET"
            headline = news_item.headline[:60] + "..." if len(news_item.headline) > 60 else news_item.headline
            sentiment_emoji = "🟢" if news_item.sentiment == "positive" else "🔴" if news_item.sentiment == "negative" else "🟡"
            response += f"{sentiment_emoji} {symbol}: {headline}\n"
        response += "\n"
    
    # Trading opportunities
    response += "💡 OPPORTUNITIES:\n"
    if market_data["top_gainers"]:
        best_performer = market_data["top_gainers"][0]
        if best_performer["change_percent"] > 3:
            response += f"• Consider taking profits on {best_performer['symbol']} (+{best_performer['change_percent']:.1f}%)\n"
    
    if market_data["top_losers"]:
        worst_performer = market_data["top_losers"][0]
        if worst_performer["change_percent"] < -3:
            response += f"• {worst_performer['symbol']} down {worst_performer['change_percent']:.1f}% - potential buy opportunity?\n"
    
    response += "• Monitor volume and news for confirmation\n"
    response += "• Use stop-losses to manage risk\n\n"
    
    response += "⚠️ Market movements can be volatile. Always do your own research before trading."
    
    return response

def _handle_market_question(state: AppState) -> str:
    """Handle general market questions"""
    response = "🌍 MARKET OVERVIEW & ANALYSIS\n\n"
    
    # Analyze current market state
    total_symbols = len(state.symbols)
    gainers = sum(1 for s in state.symbols if state.prices.get(s, 100) > 250)  # Mock calculation
    
    response += f"📊 CURRENT MARKET STATUS:\n"
    response += f"• Tracked Stocks: {total_symbols}\n"
    response += f"• Market Trend: {'Bullish' if gainers > total_symbols/2 else 'Bearish'}\n"
    response += f"• Volatility: Moderate to high\n\n"
    
    response += f"🏆 TOP MOVERS:\n"
    # Sort by price for demo
    sorted_symbols = sorted(state.symbols, key=lambda s: state.prices.get(s, 0), reverse=True)
    
    response += "Top performers:\n"
    for symbol in sorted_symbols[:3]:
        price = state.prices.get(symbol, 0)
        change = ((price % 100) - 50) * 0.02
        response += f"• {symbol}: ${price:.2f} ({'+' if change >= 0 else ''}{change:.2f})\n"
    
    response += "\nNeed attention:\n"
    for symbol in sorted_symbols[-3:]:
        price = state.prices.get(symbol, 0)
        change = ((price % 100) - 50) * 0.02
        response += f"• {symbol}: ${price:.2f} ({'+' if change >= 0 else ''}{change:.2f})\n"
    
    response += "\n💡 MARKET INSIGHTS:\n"
    response += "• Technology sector showing strength\n"
    response += "• Monitor Federal Reserve policy changes\n"
    response += "• Earnings season approaching - volatility expected\n"
    response += "• Global economic factors influencing markets\n\n"
    
    response += "🎯 CURRENT OPPORTUNITIES:\n"
    response += "• Value investing in oversold quality stocks\n"
    response += "• Dividend-paying stocks for income\n"
    response += "• Growth stocks with strong fundamentals\n"
    response += "• Sector rotation opportunities\n\n"
    
    response += "⚠️ MARKET RISKS TO MONITOR:\n"
    response += "• Inflation concerns\n"
    response += "• Interest rate changes\n"
    response += "• Geopolitical tensions\n"
    response += "• Economic indicators\n\n"
    
    response += "💼 RECOMMENDED ACTIONS:\n"
    response += "• Maintain diversified portfolio\n"
    response += "• Keep some cash for opportunities\n"
    response += "• Regular portfolio rebalancing\n"
    response += "• Stay informed but avoid overtrading\n\n"
    
    response += "⚠️ Market conditions change rapidly. Stay informed and adapt your strategy accordingly."
    
    return response

def _handle_general_symbol_question(symbol: str, prices: dict, news: List, state: AppState) -> str:
    """Handle general questions about a specific symbol"""
    price = prices.get(symbol, 0)
    symbol_news = [n for n in news if n.symbol == symbol]
    
    response = f"📈 {symbol} COMPLETE OVERVIEW\n\n"
    
    # Basic info
    response += f"💰 CURRENT METRICS:\n"
    response += f"Price: ${price:.2f}\n"
    response += f"Status: {'Active trading' if price > 0 else 'Market closed'}\n\n"
    
    # Recent news
    if symbol_news:
        latest = symbol_news[-1]
        response += f"📰 LATEST NEWS:\n"
        response += f"• {latest.headline[:80]}...\n"
        response += f"• Sentiment: {latest.sentiment.title()}\n"
        response += f"• News count (30min): {len(symbol_news)}\n\n"
    else:
        response += f"📰 NEWS STATUS:\n"
        response += f"• No recent news (quiet period)\n"
        response += f"• May indicate stable conditions\n"
        response += f"• Good time for fundamental analysis\n\n"
    
    # Quick analysis
    response += f"🔍 QUICK ANALYSIS:\n"
    response += f"• Company: Major player in sector\n"
    response += f"• Liquidity: {'High' if price > 100 else 'Moderate'}\n"
    response += f"• Volatility: {'High' if price > 400 else 'Moderate'}\n"
    response += f"• Investment Grade: {'Large-cap' if price > 200 else 'Mid-cap'}\n\n"
    
    response += f"💡 KEY CONSIDERATIONS:\n"
    response += f"• Monitor earnings announcements\n"
    response += f"• Track sector performance\n"
    response += f"• Watch for news catalysts\n"
    response += f"• Consider position sizing\n\n"
    
    response += f"🎯 WHAT YOU CAN DO:\n"
    response += f"• Ask: 'Should I buy {symbol}?' for recommendations\n"
    response += f"• Ask: 'Analysis of {symbol}' for detailed review\n"
    response += f"• Ask: 'Risk of {symbol}' for risk assessment\n"
    response += f"• Ask: '{symbol} vs [other stock]' for comparison\n\n"
    
    response += "⚠️ This overview provides current data. Conduct thorough research before investing."
    
    return response

def _handle_help_question() -> str:
    """Provide comprehensive help for trading questions"""
    response = "🤖 AI TRADING ASSISTANT - HOW TO GET HELP\n\n"
    
    response += "💹 STOCK ANALYSIS - Ask about any stock:\n"
    response += "• 'What's the price of TSLA?'\n"
    response += "• 'Should I buy AAPL?'\n"
    response += "• 'Analysis of GOOGL'\n"
    response += "• 'MSFT vs AMZN comparison'\n\n"
    
    response += "📊 MARKET INSIGHTS:\n"
    response += "• 'Market conditions today'\n"
    response += "• 'Best stocks to buy now'\n"
    response += "• 'Market trends'\n"
    response += "• 'Top performers today'\n\n"
    
    response += "🎯 TRADING GUIDANCE:\n"
    response += "• 'When to buy [stock]?'\n"
    response += "• 'Is [stock] risky?'\n"
    response += "• 'Portfolio strategy advice'\n"
    response += "• 'How to diversify portfolio?'\n\n"
    
    response += "⚖️ RISK & STRATEGY:\n"
    response += "• 'Risk assessment for [stock]'\n"
    response += "• 'Stop loss strategies'\n"
    response += "• 'Position sizing advice'\n"
    response += "• 'Dollar cost averaging'\n\n"
    
    response += "📈 AVAILABLE STOCKS:\n"
    response += "TSLA, AAPL, GOOGL, MSFT, AMZN, NVDA, META, NFLX, AMD, UBER\n\n"
    
    response += "💡 SAMPLE QUESTIONS:\n"
    response += "• 'What's happening with Tesla stock?'\n"
    response += "• 'Should I buy Apple or Microsoft?'\n"
    response += "• 'Is now a good time to invest?'\n"
    response += "• 'How risky is NVIDIA?'\n"
    response += "• 'Best portfolio allocation strategy?'\n\n"
    
    response += "🔍 I PROVIDE:\n"
    response += "✓ Real-time stock prices\n"
    response += "✓ News sentiment analysis\n"
    response += "✓ Buy/sell guidance\n"
    response += "✓ Risk assessments\n"
    response += "✓ Portfolio strategies\n"
    response += "✓ Market insights\n"
    response += "✓ Technical analysis\n\n"
    
    response += "⚠️ IMPORTANT DISCLAIMER:\n"
    response += "All information provided is for educational purposes only. This is not financial advice. Always do your own research and consider consulting with a qualified financial advisor before making investment decisions.\n\n"
    
    response += "🚀 Just ask me anything about stocks, trading, or investing!"
    
    return response

def _handle_portfolio_question(portfolio: dict, question: str, state: AppState) -> str:
    """Handle portfolio-specific questions"""
    if not portfolio or not portfolio.get('holdings'):
        return ("📁 EMPTY PORTFOLIO\n\n"
               "Your portfolio is currently empty. To get started:\n\n"
               "💡 NEXT STEPS:\n"
               "• Research stocks you're interested in\n"
               "• Ask me: 'Should I buy [stock]?' for recommendations\n"
               "• Start with small positions (2-5% of capital)\n"
               "• Diversify across different sectors\n\n"
               "🎯 I can help you:\n"
               "• Analyze any stock\n"
               "• Compare investment options\n"
               "• Create an investment strategy\n"
               "• Assess risks\n\n"
               "Just ask: 'What stocks should I consider?' to begin!")
    
    holdings = portfolio['holdings']
    total_value = portfolio.get('total_value', 0)
    cash_balance = portfolio.get('cash_balance', 0)
    total_pl = portfolio.get('total_pl', 0)
    
    response = "📊 YOUR PORTFOLIO ANALYSIS\n\n"
    
    # Portfolio summary
    response += "💼 PORTFOLIO SUMMARY:\n"
    response += f"• Total Value: ${total_value:,.2f}\n"
    response += f"• Cash Balance: ${cash_balance:,.2f}\n"
    response += f"• Total P&L: {'$' + str(total_pl) if total_pl >= 0 else '-$' + str(abs(total_pl))}\n"
    response += f"• Number of Holdings: {len(holdings)}\n\n"
    
    # Holdings breakdown
    response += "🏢 CURRENT HOLDINGS:\n"
    for symbol, data in holdings.items():
        shares = data.get('shares', 0)
        current_price = state.prices.get(symbol, 0)
        cost_basis = data.get('cost_basis', 0)
        current_value = shares * current_price
        position_pl = current_value - (shares * cost_basis)
        position_pl_pct = (position_pl / (shares * cost_basis) * 100) if cost_basis > 0 else 0
        
        response += f"• {symbol}: {shares} shares @ ${current_price:.2f}\n"
        response += f"  Value: ${current_value:,.2f} | P&L: {'$' + str(round(position_pl, 2)) if position_pl >= 0 else '-$' + str(round(abs(position_pl), 2))} ({position_pl_pct:+.1f}%)\n"
    
    response += "\n"
    
    # Portfolio insights
    response += "📈 PORTFOLIO INSIGHTS:\n"
    
    # Diversification analysis
    if len(holdings) < 3:
        response += "⚠️ DIVERSIFICATION: Consider adding more stocks (target: 5-10)\n"
    elif len(holdings) > 15:
        response += "📊 DIVERSIFICATION: High diversification - may want to focus on top performers\n"
    else:
        response += "✓ DIVERSIFICATION: Good spread across holdings\n"
    
    # Performance analysis
    pl_ratio = total_pl / total_value if total_value > 0 else 0
    if pl_ratio > 0.1:
        response += f"🚀 PERFORMANCE: Strong gains (+{pl_ratio*100:.1f}%) - consider taking some profits\n"
    elif pl_ratio < -0.1:
        response += f"📉 PERFORMANCE: Significant losses ({pl_ratio*100:.1f}%) - review positions\n"
    else:
        response += f"📊 PERFORMANCE: Stable performance ({pl_ratio*100:+.1f}%)\n"
    
    # Cash position analysis
    cash_ratio = cash_balance / (total_value + cash_balance) if (total_value + cash_balance) > 0 else 0
    if cash_ratio > 0.2:
        response += f"💰 CASH POSITION: High cash reserves ({cash_ratio*100:.1f}%) - opportunities to invest\n"
    elif cash_ratio < 0.05:
        response += f"💸 CASH POSITION: Low cash reserves ({cash_ratio*100:.1f}%) - consider keeping some cash\n"
    else:
        response += f"💵 CASH POSITION: Balanced cash reserves ({cash_ratio*100:.1f}%)\n"
    
    response += "\n💡 RECOMMENDATIONS:\n"
    
    # Position-specific recommendations
    best_performer = None
    worst_performer = None
    best_pl = float('-inf')
    worst_pl = float('inf')
    
    for symbol, data in holdings.items():
        shares = data.get('shares', 0)
        current_price = state.prices.get(symbol, 0)
        cost_basis = data.get('cost_basis', 0)
        position_pl = (shares * current_price) - (shares * cost_basis)
        
        if position_pl > best_pl:
            best_pl = position_pl
            best_performer = symbol
        if position_pl < worst_pl:
            worst_pl = position_pl
            worst_performer = symbol
    
    if best_performer and best_pl > 0:
        response += f"🎯 Consider taking profits on {best_performer} (+${best_pl:.2f})\n"
    
    if worst_performer and worst_pl < -100:  # Significant loss
        response += f"⚠️ Review {worst_performer} position (-${abs(worst_pl):.2f}) - cut losses or average down?\n"
    
    response += "• Rebalance positions if any stock > 20% of portfolio\n"
    response += "• Monitor news for all holdings\n"
    response += "• Set stop-losses for risk management\n"
    response += f"• Consider adding {'more' if len(holdings) < 5 else 'different sector'} stocks\n\n"
    
    response += "🔍 ASK ME ABOUT:\n"
    response += "• 'Should I sell [stock]?' for exit strategies\n"
    response += "• 'What to buy next?' for new opportunities\n"
    response += "• '[stock] vs [stock]' to compare holdings\n"
    response += "• 'Portfolio rebalancing' for optimization tips\n\n"
    
    response += "⚠️ Portfolio analysis is based on current market data. Consider your investment goals and risk tolerance."
    
    return response

def _get_comprehensive_market_overview(state: AppState) -> dict:
    """Get detailed market overview"""
    overview = {"symbols": [], "top_gainers": [], "top_losers": [], "recent_news": []}
    
    for symbol in state.symbols:
        if symbol in state.prices:
            price = state.prices[symbol]
            change = ((price % 100) - 50) * 0.02
            change_percent = (change / price) * 100 if price > 0 else 0
            
            overview["symbols"].append({
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent
            })
    
    # Sort for top gainers/losers
    sorted_symbols = sorted(overview["symbols"], key=lambda x: x["change_percent"], reverse=True)
    overview["top_gainers"] = sorted_symbols[:3]
    overview["top_losers"] = sorted_symbols[-3:]
    overview["recent_news"] = state.news[-5:] if state.news else []
    
    return overview


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
