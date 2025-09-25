#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.trading_buddy import handle_trading_question
from app.services.state import AppState

async def test_specific_question():
    """Test the specific 'What are the top movers?' question"""
    
    # Initialize app state like in main.py
    state = AppState()
    
    # Add realistic mock data with actual price movements
    state.prices = {
        'TSLA': 442.79,   # +4.0% (top gainer)
        'AAPL': 252.31,   # -0.8%
        'GOOGL': 247.14,  # -1.8%
        'MSFT': 510.15,   # +0.2%
        'AMZN': 220.21,   # -0.2%
        'NVDA': 176.97,   # -0.8%
        'META': 760.66,   # +0.7%
        'NFLX': 1203.95,  # -1.2% (top loser)
        'AMD': 160.88,    # -0.0%
        'UBER': 97.78     # -0.0%
    }
    
    question = "What are the top movers?"
    print(f"QUESTION: {question}")
    print("=" * 50)
    
    try:
        response = await handle_trading_question(question, state)
        print(response)
        print("\n" + "=" * 50)
        print("✅ SUCCESS: Question properly categorized and handled!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_question())
