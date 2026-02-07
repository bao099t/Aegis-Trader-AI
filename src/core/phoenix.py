import datetime
import os
import shutil
import json
from src.database import db_setup, models
from src.intelligence.performance_tracker import PerformanceTracker

class Phoenix:
    """
    The Phoenix Protocol (Phase 29).
    Handles:
    1. Resurrection (Unlock Circuit Breakers via Paper Trading Verification)
    2. Maintenance (Database Hygiene)
    3. Morning Routine (Health Checks)
    """
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.RESURRECTION_STREAK_NEEDED = 3 # Need 3 winning virtual trades to unlock
        self.ARCHIVE_DIR = "data/archive"
        if not os.path.exists(self.ARCHIVE_DIR):
            os.makedirs(self.ARCHIVE_DIR)

    def assess_redemption(self):
        """
        Check if we have enough winning virtual trades to unlock the Guardian.
        Called when Guardian is in PROBATION mode.
        """
        db = db_setup.SessionLocal()
        try:
            # Find recent virtual trades that have closed PnL
            # We look for the last N virtual trades
            recent = db.query(models.Alert).filter(
                models.Alert.is_virtual == True,
                models.Alert.pnl_percent != None
            ).order_by(models.Alert.published_at.desc()).limit(self.RESURRECTION_STREAK_NEEDED).all()
            
            if len(recent) < self.RESURRECTION_STREAK_NEEDED:
                return False, f"Need {self.RESURRECTION_STREAK_NEEDED} virtual trades. Found {len(recent)}."
                
            # Check if all are winners
            wins = [a for a in recent if a.pnl_percent > 0]
            if len(wins) >= self.RESURRECTION_STREAK_NEEDED:
                # UNLOCK SYSTEM
                tracker = PerformanceTracker(db)
                dd = tracker.get_drawdown_state()['current_drawdown']
                
                self.guardian.reset_breakers(current_drawdown=dd)
                return True, "🔥 PHOENIX RISEN: System unlocked after winning streak."
            
            return False, f"Streak broken. Last {len(recent)} trades: {[a.pnl_percent for a in recent]}"
            
        finally:
            db.close()

    def clean_house(self):
        """
        Moves alerts older than 30 days to JSON archive to keep DB fast.
        """
        db = db_setup.SessionLocal()
        try:
            now = datetime.datetime.utcnow()
            cutoff = now - datetime.timedelta(days=30)
            
            old_alerts = db.query(models.Alert).filter(
                models.Alert.published_at < cutoff
            ).all()
            
            if not old_alerts:
                return "Clean"

            # Serialize to JSON
            filename = f"{self.ARCHIVE_DIR}/archive_{now.strftime('%Y%m%d')}.json"
            data = []
            ids_to_delete = []
            
            for a in old_alerts:
                data.append({
                    "id": a.id,
                    "title": a.title,
                    "ticker": a.ticker,
                    "pnl": a.pnl_percent,
                    "date": str(a.published_at)
                })
                ids_to_delete.append(a.id)
            
            with open(filename, 'w') as f:
                json.dump(data, f)
            
            # Delete from DB
            db.query(models.Alert).filter(models.Alert.id.in_(ids_to_delete)).delete(synchronize_session=False)
            db.commit()
            
            return f"Archived {len(old_alerts)} alerts."
            
        except Exception as e:
            print(f"[Phoenix] Error cleaning house: {e}")
            return "Error"
        finally:
            db.close()

    def morning_routine(self):
        """
        Runs at startup or daily. Checks system health.
        """
        print("☀️ [Phoenix] Morning Routine executed.")
        # Reset any temporary RAM counters if we had them (handled by Guardian checking DB time)
        # Check DB connection
        try:
            db = db_setup.SessionLocal()
            db.execute("SELECT 1")
            db.close()
            return True, "System Healthy"
        except Exception as e:
            return False, f"DB Error: {e}"
