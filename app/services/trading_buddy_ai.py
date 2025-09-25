import os
import json
from typing import List, Dict, Any

from .state import AppState
from .pathway_pipelines import is_available as pathway_available


def _fallback_response(symbols_mentioned, current_prices, news_context):
    """Create a generic fallback response when AI models fail"""
    symbol = symbols_mentioned[0] if symbols_mentioned else None
    price = current_prices.get(symbol, 0) if symbol else 0
    
    response = f"I'm sorry, I couldn't process your request through the AI model. "
    
    if symbol:
        response += f"However, I can tell you that {symbol} is currently trading at ${price:.2f}. "
        response += f"For more detailed analysis, please try again or ask a more specific question."
    else:
        response += f"Please try asking a more specific question about a particular stock or market trend."
    
    return response


async def _enhanced_gemini_answer(
    question: str, 
    symbols_mentioned: List[str], 
    news_context: List, 
    current_prices: Dict[str, float], 
    state: AppState
) -> str:
    """Generate enhanced answers using Gemini with Pathway processed data"""
    try:
        import google.generativeai as genai
        
        # Configure the API
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Build system prompt with data context
        system_prompt = _build_financial_assistant_prompt(symbols_mentioned, news_context, current_prices, state)
        
        # Create model instance with appropriate settings
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config
        )
        
        # Build conversation with system prompt
        convo = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["I understand the financial context and will provide accurate, helpful information based on the market data provided."]}
        ])
        
        # Generate response based on user question
        response = convo.send_message(question)
        
        # Format response
        formatted_response = response.text
        
        # Add disclaimer
        if not formatted_response.endswith("This is not financial advice."):
            formatted_response += "\n\n⚠️ This information is for educational purposes only. This is not financial advice."
        
        return formatted_response
        
    except Exception as e:
        print(f"Error generating Gemini response: {str(e)}")
        # Fallback to template responses if AI fails
        return _fallback_response(symbols_mentioned, current_prices, news_context)


async def _enhanced_openai_answer(
    question: str, 
    symbols_mentioned: List[str], 
    news_context: List, 
    current_prices: Dict[str, float], 
    state: AppState
) -> str:
    """Generate enhanced answers using OpenAI with Pathway processed data"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Build system prompt with data context
        system_prompt = _build_financial_assistant_prompt(symbols_mentioned, news_context, current_prices, state)
        
        # Generate completion using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        # Format response
        formatted_response = response.choices[0].message.content
        
        # Add disclaimer
        if not formatted_response.endswith("This is not financial advice."):
            formatted_response += "\n\n⚠️ This information is for educational purposes only. This is not financial advice."
        
        return formatted_response
        
    except Exception as e:
        print(f"Error generating OpenAI response: {str(e)}")
        # Fallback to template responses if AI fails
        return _fallback_response(symbols_mentioned, current_prices, news_context)


def _build_financial_assistant_prompt(
    symbols_mentioned: List[str], 
    news_context: List, 
    current_prices: Dict[str, float], 
    state: AppState
) -> str:
    """Build a comprehensive system prompt for the AI models with Pathway data integration"""
    
    # Check if Pathway processed data is available
    pathway_data = {}
    if pathway_available():
        try:
            # Try to read from Pathway output files
            try:
                with open("./data/market_output.jsonl", "r") as f:
                    last_line = None
                    for line in f:
                        last_line = line
                    if last_line:
                        pathway_data["market"] = json.loads(last_line)
            except:
                pass
            
            try:
                with open("./data/news_output.jsonl", "r") as f:
                    news_data = []
                    for line in f:
                        news_data.append(json.loads(line))
                    if news_data:
                        pathway_data["news"] = news_data[-10:]  # Last 10 news items
            except:
                pass
        except Exception as e:
            print(f"Error reading Pathway data: {str(e)}")
    
    # Start building the prompt
    prompt = """You are a financial market assistant with access to real-time market data.
Your goal is to provide accurate, helpful responses to financial and trading questions.

Here's the current market data you have access to:
"""

    # Add symbol data
    if symbols_mentioned:
        prompt += "\nSTOCK DATA:\n"
        for symbol in symbols_mentioned:
            price = current_prices.get(symbol, 0)
            prompt += f"- {symbol}: ${price:.2f}\n"
    
    # Add news context
    if news_context:
        prompt += "\nRECENT NEWS:\n"
        for item in news_context[-5:]:  # Last 5 news items
            prompt += f"- {item.symbol}: {item.headline} (Sentiment: {item.sentiment})\n"
    
    # Add Pathway processed data if available
    if pathway_data:
        prompt += "\nADVANCED ANALYTICS (from Pathway processing):\n"
        
        if "market" in pathway_data:
            market = pathway_data["market"]
            prompt += f"- Market data timestamp: {market.get('timestamp', 'N/A')}\n"
            prompt += f"- Processed market indicators available\n"
        
        if "news" in pathway_data:
            news = pathway_data["news"]
            prompt += f"- {len(news)} processed news items with sentiment analysis\n"
            
            # Add sentiment summary
            sentiments = [item.get("sentiment", "neutral") for item in news]
            pos = sum(1 for s in sentiments if s == "positive")
            neg = sum(1 for s in sentiments if s == "negative")
            neutral = sum(1 for s in sentiments if s == "neutral")
            
            prompt += f"- Overall sentiment: "
            if pos > neg and pos > neutral:
                prompt += "Mostly positive\n"
            elif neg > pos and neg > neutral:
                prompt += "Mostly negative\n"
            else:
                prompt += "Mixed or neutral\n"
    
    # Add instructions
    prompt += """
RESPONSE GUIDELINES:
- Provide accurate, data-backed answers
- Use bullet points for clarity when appropriate
- Include both bullish and bearish perspectives
- Be clear about limitations in the data
- Always include a disclaimer that this is not financial advice
- Be concise but thorough

The user will now ask a question about the market or specific stocks.
"""
    
    return prompt
