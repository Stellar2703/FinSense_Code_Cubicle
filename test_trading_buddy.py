#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.trading_buddy import handle_trading_question
from app.services.state import AppState

async def test_trading_questions():
    """Test various trading questions with the enhanced AI"""
    
    # Initialize app state like in main.py
    state = AppState()
    
    # Add some mock data
    state.prices = {
        'TSLA': 245.67, 'AAPL': 184.52, 'GOOGL': 164.89, 'MSFT': 419.32,
        'AMZN': 181.45, 'NVDA': 134.76, 'META': 523.89, 'NFLX': 789.23, 
        'AMD': 119.87, 'UBER': 67.43
    }
    
    # Test questions covering different categories
    test_questions = [
        "What's the price of TSLA?",
        "Should I buy Apple stock?", 
        "Compare Tesla vs Apple stock",
        "Analysis of GOOGL",
        "Is NVIDIA risky?",
        "Market conditions today",
        "When should I buy stocks?",
        "Portfolio strategy advice",
        "How is my portfolio performing?",
        "Help me understand trading"
    ]
    
    print("🤖 TESTING ENHANCED TRADING AI ASSISTANT\n" + "="*60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. QUESTION: {question}")
        print("-" * 50)
        
        try:
            response = await handle_trading_question(question, state)
            print(response)
            
            # Add separator between questions
            if i < len(test_questions):
                print("\n" + "="*60)
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n{'='*60}\n✅ TESTING COMPLETE - AI ASSISTANT READY!")

if __name__ == "__main__":
    asyncio.run(test_trading_questions())
