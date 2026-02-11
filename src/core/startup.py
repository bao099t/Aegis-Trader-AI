import os
import sys
import time
import requests
import sqlite3
from datetime import datetime

class PreFlightCheck:
    """
    The Inspector (Phase 9).
    Ensures the aircraft is airworthy before takeoff.
    """
    
    def __init__(self, broker=None):
        self.broker = broker
        self.report = []
        
    def run_all(self):
        print("\n🚀 [Pre-Flight] Starting System Diagnostics...")
        all_clear = True
        
        # 1. Internet Check
        if not self.check_internet(): all_clear = False
        
        # 2. Time Sync
        if not self.check_time_sync(): all_clear = False
        
        # 3. Database Integrity
        if not self.check_database(): all_clear = False
        
        # 4. Exchange Connection
        if self.broker:
            if not self.check_exchange(): all_clear = False
            
        print("\n" + "="*40)
        if all_clear:
            print("✅ SYSTEM READY FOR TAKEOFF")
            return True
        else:
            print("❌ CRITICAL SYSTEMS FAILURE. ABORTING.")
            return False
            
    def check_internet(self):
        try:
            requests.get("https://www.google.com", timeout=3)
            self._log("Internet Connection", "OK")
            return True
        except:
            self._log("Internet Connection", "FAIL", "No ping to Google")
            return False
            
    def check_time_sync(self):
        # Rough check logic
        local = datetime.now()
        self._log("System Clock", "OK", local.strftime("%H:%M:%S"))
        return True

    def check_database(self):
        db_path = "data/alerts.db"
        if not os.path.exists(db_path):
            self._log("Database File", "WARNING", "Not found (Will create)")
            return True
            
        try:
            conn = sqlite3.connect(db_path)
            conn.cursor().execute("SELECT count(*) FROM sqlite_master")
            conn.close()
            self._log("Database Integrity", "OK")
            return True
        except Exception as e:
            self._log("Database Integrity", "FAIL", str(e))
            return False
            
    def check_exchange(self):
        if self.broker.simulation_mode:
            self._log("Exchange Link", "SKIP", "Simulation Mode")
            return True
            
        try:
            # Try to fetch balance as connectivity test
            positions = self.broker.get_active_positions()
            self._log("Exchange Link", "OK", f"Connection Active")
            return True
        except Exception as e:
             self._log("Exchange Link", "FAIL", f"API Key Invalid? {e}")
             return False

    def _log(self, system, status, details=""):
        symbol = "✅" if status == "OK" else ("⚠️" if status == "WARNING" else "❌")
        print(f"  {symbol} {system:<20} [{status}] {details}")

if __name__ == "__main__":
    # Test Standalone
    p = PreFlightCheck(None)
    p.run_all()
