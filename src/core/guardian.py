import datetime
from src.database import db_setup, models
from src.intelligence.performance_tracker import PerformanceTracker

import json
import os

from src.intelligence.anti_manipulation import AntiManipulationFilter

class Guardian:
    """
    The Sovereign Guardian (Evolution Phase 44).
    Enforces Hard Security Ceilings and AI-Driven Anti-Manipulation Filters.
    """
    
    def __init__(self):
        self.MAX_DAILY_ALERTS = 10
        self.TICKER_COOLDOWN_HOURS = 4
        self.MAX_DRAWDOWN_LIMIT = 15.0 
        self.CONSECUTIVE_LOSS_LIMIT = 5 
        self.HARD_CAP_ALLOCATION = 15.0 
        self.anti_manip = AntiManipulationFilter() # Phase 44
        self.TOTAL_MAX_DRAWDOWN_LIMIT = 30.0 # GLOBAL HARD STOP
        self.STATE_FILE = "data/guardian_state.json"
        
        # Load State
        self._load_state()

        if self.state == "PERMANENT_LOCKDOWN":
            print("🚨 GUARDIAN: SYSTEM IS IN PERMANENT LOCKDOWN. MANUAL INTERVENTION REQUIRED.")

    def _load_state(self):
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.state = data.get('state', 'ACTIVE')
                    self.baseline_drawdown = data.get('baseline_drawdown', 0.0)
                    self.global_peak_equity = data.get('global_peak_equity', 100.0) # Default to 100 base
            except:
                self.state = 'ACTIVE'
                self.baseline_drawdown = 0.0
                self.global_peak_equity = 100.0
        else:
            self.state = 'ACTIVE'
            self.baseline_drawdown = 0.0
            self.global_peak_equity = 100.0

        data = {
            'state': self.state,
            'baseline_drawdown': self.baseline_drawdown,
            'global_peak_equity': self.global_peak_equity
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

    def check_safety(self, ticker, signal_direction, suggested_size, df=None):
        """
        Runs all safety checks.
        Returns: (is_safe: bool, rejection_reason: str, adjusted_size: float)
        """
        # Reload state in case Phoenix updated it externally
        self._load_state()
        
        db = db_setup.SessionLocal()
        try:
            # 0. Check State
            if self.state == "PERMANENT_LOCKDOWN":
                 return False, "⛔ SYSTEM LOCKED: TOTAL DRAWDOWN LIMIT EXCEEDED.", 0

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
                
            # 4. AI Anti-Manipulation Filter (Evolution Phase 44)
            if df is not None:
                is_manip, score, reason = self.anti_manip.analyze(ticker, df)
                if is_manip:
                    return False, f"🛑 GUARDIAN: Anti-Manipulation Veto: {reason}", 0

            # 5. Circuit Breakers (Portfolio Health)
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
        
        # 1. Update Global Peak Check
        # We need current equity relative to base 100
        # This is strictly theoretical based on pnl sum, in reality we'd pull NAV
        # For now, we rely on Performance Tracker's equity curve simulation
        
        # Calculate Global Drawdown
        # Current Equity = 100 * product(1 + pnl) ... handled by tracker
        equity_stats = tracker.get_drawdown_state()
        
        # We assume tracker.get_drawdown_state() calculates Max DD from Start
        # current_drawdown is from Peer Peak.
        
        # NOTE: To implement "Infinite Loss" protection, we need to ensure that 
        # resetting baseline_drawdown DOES NOT reset our concept of "Global Peak".
        
        # If current drawdown (from tracker) > Total Limit, we LOCK.
        # But wait, tracker calculates from start of DB. So it IS global?
        # Yes, tracker uses ALL history.
        # The issue was 'baseline_drawdown' in check_circuit_breakers masked it?
        
        curr_dd = equity_stats['current_drawdown']
        
        # GLOBAL KILL SWITCH
        if curr_dd >= self.TOTAL_MAX_DRAWDOWN_LIMIT:
             self.state = "PERMANENT_LOCKDOWN"
             self._save_state()
             return False, f"💀 FATAL: Total Drawdown {curr_dd}% > Limit {self.TOTAL_MAX_DRAWDOWN_LIMIT}%. SYSTEM LOCKED."

        # SESSION / LOCAL BREAKER
        # Effective Drawdown = Actual - Baseline (The "Reset" logic)
        effective_dd = max(0, curr_dd - self.baseline_drawdown)
        
        if effective_dd >= self.MAX_DRAWDOWN_LIMIT:
             return False, f"Effective Drawdown {effective_dd:.1f}% (Actual {curr_dd:.1f}%) > Limit {self.MAX_DRAWDOWN_LIMIT}%"
        
        # Consecutive Loss Breaker
        recent = tracker.get_recent_performance(n=self.CONSECUTIVE_LOSS_LIMIT)
        if len(recent) >= self.CONSECUTIVE_LOSS_LIMIT:
            losses = [p for p in recent if p < 0]
            if len(losses) == self.CONSECUTIVE_LOSS_LIMIT:
                return False, f"System halted. {self.CONSECUTIVE_LOSS_LIMIT} consecutive losses detected."
                
        return True, "OK"
