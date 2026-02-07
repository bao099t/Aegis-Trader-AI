import unittest
from unittest.mock import MagicMock, patch
import datetime
from src.core.guardian import Guardian
from src.database import models

class TestGuardian(unittest.TestCase):
    def setUp(self):
        self.guardian = Guardian()
        self.mock_db = MagicMock()
        
    @patch('src.core.guardian.db_setup.SessionLocal')
    def test_daily_limit_reached(self, mock_session):
        # Setup
        mock_session.return_value = self.mock_db
        # Mock 10 alerts today
        self.mock_db.query.return_value.filter.return_value.count.return_value = 10
        
        is_safe, reason, _ = self.guardian.check_safety("AAPL", "BULLISH", 10.0)
        
        self.assertFalse(is_safe)
        self.assertIn("Daily Alert Limit Reached", reason)
        
    @patch('src.core.guardian.db_setup.SessionLocal')
    def test_ticker_cooldown(self, mock_session):
        # Setup
        mock_session.return_value = self.mock_db
        # Mock daily limit PASS (count = 0)
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        # Mock existing alert found
        self.mock_db.query.return_value.filter.return_value.first.return_value = models.Alert()
        
        is_safe, reason, _ = self.guardian.check_safety("TSLA", "BULLISH", 10.0)
        
        self.assertFalse(is_safe)
        self.assertIn("Cooldown active", reason)

    @patch('src.core.guardian.db_setup.SessionLocal')
    @patch('src.core.guardian.PerformanceTracker')
    def test_drawdown_block(self, mock_tracker_cls, mock_session):
        # Setup
        mock_session.return_value = self.mock_db
        mock_tracker = mock_tracker_cls.return_value
        
        # Daily limit OK, Cooldown OK
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Drawdown BAD (20% > 15%)
        mock_tracker.get_drawdown_state.return_value = {"current_drawdown": 20.0, "max_drawdown": 25.0}
        
        is_safe, reason, _ = self.guardian.check_safety("GOOG", "BULLISH", 10.0)
        
        self.assertFalse(is_safe)
        self.assertIn("Drawdown 20.0% > Limit", reason)

    @patch('src.core.guardian.db_setup.SessionLocal')
    @patch('src.core.guardian.PerformanceTracker')
    def test_consecutive_loss_block(self, mock_tracker_cls, mock_session):
        # Setup
        mock_session.return_value = self.mock_db
        mock_tracker = mock_tracker_cls.return_value
        
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_tracker.get_drawdown_state.return_value = {"current_drawdown": 5.0}
        
        # 5 Consecutive Losses
        mock_tracker.get_recent_performance.return_value = [-1.0, -2.0, -0.5, -3.0, -1.5]
        
        is_safe, reason, _ = self.guardian.check_safety("AMZN", "BULLISH", 10.0)
        
        self.assertFalse(is_safe)
        self.assertIn("5 consecutive losses", reason)
        
    @patch('src.core.guardian.db_setup.SessionLocal')
    @patch('src.core.guardian.PerformanceTracker')
    def test_allocation_cap(self, mock_tracker_cls, mock_session):
        # Setup
        mock_session.return_value = self.mock_db
        mock_tracker = mock_tracker_cls.return_value
        
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_tracker.get_drawdown_state.return_value = {"current_drawdown": 0.0}
        mock_tracker.get_recent_performance.return_value = [1.0]
        
        # Suggest 20%, Cap is 15%
        is_safe, reason, size = self.guardian.check_safety("MSFT", "BULLISH", 20.0)
        
        self.assertTrue(is_safe)
        self.assertEqual(size, 15.0)

if __name__ == '__main__':
    unittest.main()
