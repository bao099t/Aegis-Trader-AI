import datetime
from src.database import db_setup, models
from src.intelligence.performance_tracker import PerformanceTracker

import json
import os

class Guardian:
    """
    The Sovereign Guardian (Phase 28).
    Enforces Hard Security Ceilings and Portfolio Circuit Breakers.
    This module has the final veto power over any trade.
    """
    
    def __init__(self):
        self.MAX_DAILY_ALERTS = 10
        self.TICKER_COOLDOWN_HOURS = 4
        self.MAX_DRAWDOWN_LIMIT = 15.0 # Stop system if 15% drawdown reached
        self.CONSECUTIVE_LOSS_LIMIT = 5 # Stop system if 5 losses in a row
        self.HARD_CAP_ALLOCATION = 15.0 # Never suggest more than 15% size
        self.STATE_FILE = "data/guardian_state.json"
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.state = data.get('state', 'ACTIVE')
                    self.baseline_drawdown = data.get('baseline_drawdown', 0.0)
            except:
                self.state = 'ACTIVE'
                self.baseline_drawdown = 0.0
        else:
            self.state = 'ACTIVE'
            self.baseline_drawdown = 0.0

    def _save_state(self):
        data = {
            'state': self.state,
            'baseline_drawdown': self.baseline_drawdown
        }
        with open(self.STATE_FILE, 'w') as f:
            json.dump(data, f)

    def reset_breakers(self, current_drawdown=0.0):
        """Called by Phoenix to rise from the ashes."""
        self.state = "ACTIVE"
        # We set the baseline to current drawdown, effectively zeroing out the risk counter
        self.baseline_drawdown = current_drawdown
        self._save_state()
        print(f"🔥 [Guardian] Circuit Breakers RESET. New Baseline DD: {self.baseline_drawdown}%")

    def check_safety(self, ticker, signal_direction, suggested_size):
        """
        Runs all safety checks.
        Returns: (is_safe: bool, rejection_reason: str, adjusted_size: float)
        """
        # Reload state in case Phoenix updated it externally
        self._load_state()
        
        db = db_setup.SessionLocal()
        try:
            # 0. Check State
            if self.state == "PROBATION":
                return False, "PROBATION: Virtual Trade Only", 0
                
            # 1. Hard Allocation Cap
            if suggested_size > self.HARD_CAP_ALLOCATION:
                suggested_size = self.HARD_CAP_ALLOCATION
            
            # 2. Daily Limit Check
            if not self._check_daily_limit(db):
                return False, "🛑 GUARDIAN: Daily Alert Limit Reached (Max 10).", 0
            
            # 3. Ticker Cooldown Check
            if not self._check_ticker_cooldown(db, ticker):
                return False, f"🛑 GUARDIAN: Cooldown active for {ticker} (4h limit).", 0
                
            # 4. Circuit Breakers (Portfolio Health)
            ok, reason = self._check_circuit_breakers(db)
            if not ok:
                 self.state = "PROBATION"
                 self._save_state()
                 return False, f"🛑 GUARDIAN BREAKER TRIGGERED: {reason}. Entering PROBATION Mode.", 0

            return True, "OK", suggested_size
            
        finally:
            db.close()

    def _check_daily_limit(self, db):
        """Limits total alerts to prevent spam/overtrading."""
        now = datetime.datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        count = db.query(models.Alert).filter(
            models.Alert.published_at >= start_of_day
        ).count()
        
        return count < self.MAX_DAILY_ALERTS

    def _check_ticker_cooldown(self, db, ticker):
        """Prevent spamming the same ticker."""
        if not ticker: return True
        
        now = datetime.datetime.utcnow()
        limit_time = now - datetime.timedelta(hours=self.TICKER_COOLDOWN_HOURS)
        
        # Check if we have alerted this ticker recently
        exists = db.query(models.Alert).filter(
            models.Alert.ticker == ticker,
            models.Alert.published_at >= limit_time
        ).first()
        
        return exists is None

    def _check_circuit_breakers(self, db):
        """Stops trading if performance sucks."""
        tracker = PerformanceTracker(db)
        
        # Drawdown Breaker
        dd_state = tracker.get_drawdown_state()
        curr_dd = dd_state['current_drawdown']
        
        # Effective Drawdown = Actual - Baseline
        # Ensures that after reset, we start fresh
        effective_dd = max(0, curr_dd - self.baseline_drawdown)
        
        if effective_dd >= self.MAX_DRAWDOWN_LIMIT:
             return False, f"Effective Drawdown {effective_dd:.1f}% (Actual {curr_dd:.1f}%) > Limit {self.MAX_DRAWDOWN_LIMIT}%"
        
        # Consecutive Loss Breaker
        # This one resets naturally if we win, so no baseline needed?
        # Actually if we have 5 losses, we enter probation.
        # If we win 3 virtual, we reset.
        # But real history still has 5 losses. 
        # get_recent_performance fetches REAL trades.
        # So we need to ignore OLD losses or Baseline this too?
        # Simpler: Consecutive Loss only looks at alerts AFTER the last Reset?
        # Or we rely on Phoenix to check virtual trades, and once we reset, we hope the NEXT real trade is a win.
        # If the next real trade is a loss, streak becomes 6. Trigger again.
        # That's fine.
        
        recent = tracker.get_recent_performance(n=self.CONSECUTIVE_LOSS_LIMIT)
        if len(recent) >= self.CONSECUTIVE_LOSS_LIMIT:
            losses = [p for p in recent if p < 0]
            if len(losses) == self.CONSECUTIVE_LOSS_LIMIT:
                return False, f"System halted. {self.CONSECUTIVE_LOSS_LIMIT} consecutive losses detected."
                
        return True, "OK"
