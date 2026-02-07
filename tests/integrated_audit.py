import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Prevent DB issues during import
with patch('src.database.db_setup.SessionLocal'):
    from src.intelligence.market_analyst import MarketAnalyst
    from src.intelligence.entity_extractor import EntityExtractor

class SystemIntegrityTest(unittest.TestCase):
    def setUp(self):
        # We need to mock DB dependencies within MarketAnalyst
        with patch('src.database.db_setup.SessionLocal'):
            self.analyst = MarketAnalyst()
        
        self.analyst.get_fundamentals = MagicMock(return_value={
            "current_price": 100.0,
            "sector": "Technology"
        })
        self.analyst.get_atr = MagicMock(return_value=2.0)

    def test_logic_hole_invalid_ticker(self):
        """Test if system rejects nonsensical tickers (Logic Hole Prevention)."""
        extractor = EntityExtractor()
        # Mock yfinance to return NO info for this ticker
        with patch('yfinance.Ticker') as mock_ticker:
            # yfinance returns a dict when .info is accessed
            mock_ticker.return_value.info = {} 
            ticker = extractor.extract("Trade fake stock $NONEXIST")
            self.assertIsNone(ticker, "System should reject non-existent tickers via verification layer")

    def test_overfitting_weighted_logic(self):
        """Test if Weighted Synthesis prevents 'Filter Paralysis'."""
        analysis_input = {
            "direction": "BULLISH",
            "technical": {"trend": "UPTREND", "regime": "TRENDING"},
            "macro": {"risk_status": "RISK-OFF"}, 
            "institutional": {"volume": {"score": "HIGH"}, "relative_strength": {"score": "LEADER"}},
            "psychology": {"divergence": {"msg": "NONE"}}
        }
        score, _, _, _ = self.analyst.calculate_synthesis(analysis_input)
        
        # Base(50) + Sent(85*0.4=34) + Tech(70*0.25=17.5) + Macro(30*0.15=4.5) + IP(70*0.2=14) = 70 approx
        self.assertGreater(score, 65, "Elite catalyst should yield a strong score despite minor macro risk")

    def test_execution_threshold(self):
        """Test if 'The Executioner' thresholds are stable."""
        analysis = {
            "direction": "BULLISH",
            "technical": {"trend": "UPTREND", "regime": "TRENDING"},
            "macro": {"risk_status": "RISK-ON"},
            "institutional": {"volume": {"score": "HIGH"}, "relative_strength": {"score": "LEADER"}},
            "psychology": {"divergence": {"msg": "NONE"}}
        }
        score, _, _, _ = self.analyst.calculate_synthesis(analysis)
        self.assertGreaterEqual(score, 75, "Perfect setup must be near or above high-conviction threshold")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
