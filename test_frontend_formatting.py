import unittest
import asyncio
from app.services.trading_buddy import handle_trading_question
from app.services.state import AppState

class TestFrontendFormatting(unittest.TestCase):
    def setUp(self):
        self.state = AppState()
    
    def test_newline_formatting(self):
        """Test that responses are formatted with proper newlines that frontend can handle."""
        # Test response with multiple lines
        question = "Should I buy AAPL?"
        
        # Run the async function in a synchronous test
        response = asyncio.run(handle_trading_question(question, self.state))
        
        # Print the raw response for inspection
        print("\nRaw response from handle_trading_question():")
        print(response)
        
        # Check that the response contains proper newlines, not literal \n characters
        self.assertIn('\n', response, "Response should contain actual newline characters")
        self.assertNotIn('\\n', response, "Response should not contain literal backslash-n characters")
        
        # Also verify that triple quoted strings are being used in the response
        # by checking for multiple newlines in sequence which is common in well-formatted output
        self.assertIn('\n\n', response, "Response should contain properly formatted paragraphs with double newlines")

if __name__ == '__main__':
    unittest.main()
