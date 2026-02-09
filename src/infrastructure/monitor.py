import time
import os
import json
import datetime

class InfrastructureMonitor:
    def __init__(self, state_file="data/system_health.json"):
        self.state_file = state_file
        self.start_time = time.time()
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

    def log_heartbeat(self, cycle_latency, status="HEALTHY", details=""):
        """
        Records a heartbeat event with latency metrics.
        """
        stat = {
            "last_heartbeat": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "latency_ms": round(cycle_latency * 1000, 2),
            "uptime_sec": round(time.time() - self.start_time, 2),
            "details": details
        }
        
        with open(self.state_file, "w") as f:
            json.dump(stat, f, indent=4)
            
    def log_trades(self, active_trades):
        """
        Records active trades for the dashboard.
        """
        trades_file = os.path.join(os.path.dirname(self.state_file), "active_trades.json")
        try:
            with open(trades_file, "w") as f:
                json.dump(active_trades, f, indent=4)
        except Exception as e:
            print(f"[Mon] Failed to log trades: {e}")

    def get_status(self):
        """Reads current health status from the state file."""
        if not os.path.exists(self.state_file):
            return {"status": "UNKNOWN", "last_heartbeat": "N/A"}
        
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except:
            return {"status": "ERROR", "last_heartbeat": "N/A"}

if __name__ == "__main__":
    mon = InfrastructureMonitor()
    mon.log_heartbeat(0.45, "HEALTHY", "System normal")
    print(mon.get_status())
