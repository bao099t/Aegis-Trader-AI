import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from src.intelligence.market_analyst import MarketAnalyst
from src.database import db_setup, models
from unittest.mock import MagicMock

class TestMarketHardening(unittest.TestCase):
    def setUp(self):
        self.analyst = MarketAnalyst()

    def test_bull_trap_detection(self):
        """Test if the system detects BULLISH news in a DOWNTREND as a trap."""
        # Mock Technicals to return DOWNTREND
        self.analyst.tech.analyze = MagicMock(return_value={
            "rsi": 45, "rsi_state": "NEUTRAL", "trend": "DOWNTREND", "price": 100.0
        })
        
        # Bullish news title
        title = "NVIDIA reaches record partnership with Microsoft"
        result = self.analyst.analyze(title)
        
        # Assertions
        self.assertEqual(result['direction'], "BULLISH")
        self.assertFalse(result['is_verified'], "Should be unverified due to downtrend divergence")
        self.assertIn("DECEPTION ALERT", result['reason'])

    def test_stop_loss_calculation(self):
        """Verify 3% Stop-Loss math."""
        # MSFT at $400
        mock_analysis = {
            "direction": "BULLISH",
            "context": {"current_price": 400.0}
        }
        
        # Bullish case
        score, verdict, size, sl = self.analyst.calculate_synthesis(mock_analysis)
        self.assertEqual(sl, 400.0 * 0.97)
        
        # Bearish case
        mock_analysis["direction"] = "BEARISH"
        score, verdict, size, sl = self.analyst.calculate_synthesis(mock_analysis)
        self.assertEqual(sl, 400.0 * 1.03)

    def test_vix_storm_warning(self):
        """Ensure high VIX triggers risk warning."""
        self.analyst.macro.analyze = MagicMock(return_value={"vix": 35, "risk_status": "RISK-OFF"})
        
        # Using a keyword that triggers BULLISH
        result = self.analyst.analyze("Apple reports record earnings beat")
        self.assertIn("🌪️ WARNING: Market is Risk-Off", result['reason'])

if __name__ == "__main__":
    unittest.main()
