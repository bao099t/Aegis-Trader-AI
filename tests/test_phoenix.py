import unittest
from unittest.mock import MagicMock, patch
import json
import os
from src.core.guardian import Guardian
from src.core.phoenix import Phoenix
from src.database import models

class TestPhoenix(unittest.TestCase):
    def setUp(self):
        # Reset state file
        if os.path.exists("data/guardian_state.json"):
            os.remove("data/guardian_state.json")
        self.guardian = Guardian()
        self.phoenix = Phoenix(self.guardian)
        self.mock_db = MagicMock()
        
    def tearDown(self):
        if os.path.exists("data/guardian_state.json"):
            os.remove("data/guardian_state.json")

    def test_resurrection_flow(self):
        # Setup Mocks
        mock_db = MagicMock()
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_drawdown_state.return_value = {"current_drawdown": 20.0}
        
        # Patch dependencies only where needed
        with patch('src.core.guardian.db_setup.SessionLocal', return_value=mock_db), \
             patch('src.core.guardian.PerformanceTracker', return_value=mock_tracker_instance):
            
            # 1. Trigger Breaker
            # DB Mock Setup (Fallback)
            mock_db.query.return_value.filter.return_value.count.return_value = 0
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Check Safety -> Should Trigger Breaker
            is_safe, reason, _ = self.guardian.check_safety("AAPL", "BULLISH", 10.0)
            self.assertFalse(is_safe)
            self.assertIn("TRIGGERED", reason)
            self.assertEqual(self.guardian.state, "PROBATION")
            
            # Verify Persistence
            with open("data/guardian_state.json", 'r') as f:
                data = json.load(f)
                self.assertEqual(data['state'], "PROBATION")

        # 2. Probation Mode
        # Reload state check
        with patch('src.core.guardian.db_setup.SessionLocal', return_value=mock_db):
             is_safe, reason, _ = self.guardian.check_safety("AAPL", "BULLISH", 10.0)
             self.assertFalse(is_safe)
             self.assertIn("Virtual Trade Only", reason)
        
        # 3. Resurrection
        # Mock 3 winning virtual trades
        winning_trade = models.Alert(is_virtual=True, pnl_percent=5.0)
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [winning_trade, winning_trade, winning_trade]
        
        with patch('src.core.phoenix.db_setup.SessionLocal', return_value=mock_db), \
             patch('src.core.phoenix.PerformanceTracker', return_value=mock_tracker_instance):
             
             redeemed, msg = self.phoenix.assess_redemption()
                 
        self.assertTrue(redeemed)
        self.assertIn("RISEN", msg)
        self.assertEqual(self.guardian.state, "ACTIVE")
        self.assertEqual(self.guardian.baseline_drawdown, 20.0)
        
        # 4. Re-entry (Soft Reset)
        # Tracker still reports 20% by default mock
        with patch('src.core.guardian.db_setup.SessionLocal', return_value=mock_db), \
             patch('src.core.guardian.PerformanceTracker', return_value=mock_tracker_instance):
                 
             is_safe, reason, _ = self.guardian.check_safety("AAPL", "BULLISH", 10.0)
             self.assertTrue(is_safe)
             self.assertEqual(reason, "OK")

if __name__ == '__main__':
    unittest.main()
