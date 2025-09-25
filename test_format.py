import asyncio
from app.services.trading_buddy import handle_trading_question
from app.services.state import AppState

async def test_response_formatting():
    """Test the formatting of the response for specific queries"""
    # Create a mock state
    state = AppState()
    state.symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA"]
    state.prices = {"AAPL": 252.31, "GOOGL": 180.45, "MSFT": 420.15}
    
    # Test the specific query
    query = "can i buy appl stocks today"
    response = await handle_trading_question(query, state)
    
    print("\n=== RESPONSE TO 'can i buy appl stocks today' ===")
    print(response)
    print("\n=== END OF RESPONSE ===")
    
    # Test a greeting
    greeting_response = await handle_trading_question("hi", state)
    print("\n=== RESPONSE TO 'hi' ===")
    print(greeting_response)
    print("\n=== END OF RESPONSE ===")

if __name__ == "__main__":
    asyncio.run(test_response_formatting())
