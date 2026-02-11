import shutil
import os
import time
import glob
import sqlite3
from datetime import datetime, timedelta
class SystemHygiene:
    """
    The Janitor (Phase 7).
    Responsibility: Keep the system clean and performant over decades.
    """
    
    def __init__(self, log_dir="data/logs", db_path="data/alerts.db"):
        self.log_dir = log_dir
        self.db_path = db_path
        
    def clean_logs(self, max_age_days=30):
        print("🧹 [Hygiene] Scanning for old logs...")
        now = time.time()
        cutoff = now - (max_age_days * 86400)
        
        count = 0
        # Check src log dir or wherever logs are. 
        # Assuming typical structure.
        # We might need to check multiple dirs.
        targets = [
            os.path.join(self.log_dir, "*.log"),
            os.path.join(self.log_dir, "*.txt"), # Sometimes logs are txt
            "nohup.out" # If running on linux
        ]
        
        for pattern in targets:
            files = glob.glob(pattern)
            for f in files:
                try:
                    if os.stat(f).st_mtime < cutoff:
                        os.remove(f)
                        count += 1
                        print(f"    -> Deleted old log: {f}")
                except Exception as e:
                    print(f"    -> Error deleting {f}: {e}")
                    
        print(f"  [Hygiene] Deleted {count} old log files.")

    def backup_db(self):
        """Phase 8: Black Box Recorder"""
        print("📦 [Hygiene] Backing up Database...")
        if not os.path.exists(self.db_path):
            print("  [Hygiene] No DB to backup.")
            return

        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y_%m_%d")
        backup_path = os.path.join(backup_dir, f"alerts_{timestamp}.db")
        
        try:
            # Check if backup exists for today
            if not os.path.exists(backup_path):
                shutil.copy2(self.db_path, backup_path)
                print(f"  [Hygiene] Backup created: {backup_path}")
            else:
                print("  [Hygiene] Backup for today already exists.")
                
            # Retention Policy (Keep last 7)
            backups = sorted(glob.glob(os.path.join(backup_dir, "alerts_*.db")))
            while len(backups) > 7:
                oldest = backups.pop(0)
                os.remove(oldest)
                print(f"  [Hygiene] Pruned old backup: {oldest}")
                
        except Exception as e:
            print(f"  [Hygiene] Backup Error: {e}")
        
    def optimization_db(self):
        print("🧹 [Hygiene] Optimizing Database...")
        if not os.path.exists(self.db_path):
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prune old alerts > 90 days?
            # User might want history. Let's archive first?
            # For now, just VACUUM to reclaim space from deleted rows.
            # Maybe delete very old unverified alerts.
            
            ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            
            # Delete uninteresting logs/alerts if any
            # cursor.execute("DELETE FROM alerts WHERE published_at < ? AND is_sent = 0", (ninety_days_ago,))
            
            # Vacuum
            cursor.execute("VACUUM")
            conn.commit()
            conn.close()
            print("  [Hygiene] Database VACUUM complete.")
            
        except Exception as e:
            print(f"  [Hygiene] DB Error: {e}")

if __name__ == "__main__":
    h = SystemHygiene()
    h.clean_logs()
    h.backup_db()
    h.optimization_db()
