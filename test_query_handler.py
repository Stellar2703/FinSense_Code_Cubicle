import unittest
from app.services.trading_buddy import _extract_all_symbols, _is_greeting
from app.services.state import AppState

class TestTradingBuddyFunctions(unittest.TestCase):
    """Test the trading buddy functions"""

    def setUp(self):
        self.symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        self.app_state = AppState()
        self.app_state.symbols = self.symbols

    def test_extract_symbols_direct_mention(self):
        """Test extracting directly mentioned symbols"""
        question = "What's the price of AAPL today?"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)
        
    def test_extract_symbols_company_name(self):
        """Test extracting symbols from company names"""
        question = "Tell me about Apple's stock performance"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)

    def test_extract_symbols_typos(self):
        """Test extracting symbols with common typos"""
        question = "Can I invest in APPL today?"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)
        
    def test_extract_multiple_symbols(self):
        """Test extracting multiple symbols"""
        question = "Compare AAPL, MSFT, and GOOGL"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)
        self.assertIn("MSFT", symbols)
        self.assertIn("GOOGL", symbols)
        
    def test_extract_from_invest_pattern(self):
        """Test extracting symbols from investment patterns"""
        question = "Should I invest in Apple right now?"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)

    def test_extract_from_buy_pattern(self):
        """Test extracting symbols from buy patterns"""
        question = "Is it a good time to buy Tesla shares?"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("TSLA", symbols)
        
    def test_user_specific_issue(self):
        """Test the specific issue the user was having"""
        question = "can i buy appl stocks today"
        symbols = _extract_all_symbols(question, self.symbols)
        self.assertIn("AAPL", symbols)
        
    def test_greeting_detection_simple(self):
        """Test simple greeting detection"""
        self.assertTrue(_is_greeting("hi"))
        self.assertTrue(_is_greeting("hello"))
        self.assertTrue(_is_greeting("hey"))
        
    def test_greeting_detection_with_name(self):
        """Test greeting with name detection"""
        self.assertTrue(_is_greeting("hi there"))
        self.assertTrue(_is_greeting("hello assistant"))
        
    def test_not_greeting(self):
        """Test non-greetings"""
        self.assertFalse(_is_greeting("what's the stock price?"))
        self.assertFalse(_is_greeting("should I invest in Apple?"))

if __name__ == "__main__":
    unittest.main()
