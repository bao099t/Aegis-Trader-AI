import os
from dotenv import load_dotenv

# Load Sim and Real
from src.defi.yield_aggregator import SimulationYieldAggregator
try:
    from src.defi.real_aggregator import RealYieldAggregator
except ImportError:
    RealYieldAggregator = None

load_dotenv()

class DeFiManager:
    """
    Factory to return the appropriate Aggregator based on configuration.
    Safety First: Defaults to Simulation if misconfigured.
    """
    @staticmethod
    def get_aggregator():
        mode = os.getenv("TRADING_MODE", "PAPER").upper()
        
        if mode == "LIVE":
            print("\n🚨 [SYSTEM] TRADING_MODE=LIVE. Initializing REAL DEFI MODULE...")
            try:
                if RealYieldAggregator:
                    return RealYieldAggregator()
                else:
                    print("❌ [SYSTEM] RealYieldAggregator dependencies missing. Fallback to SIMULATION.")
            except Exception as e:
                print(f"❌ [SYSTEM] Failed to init Real Mode: {e}. Fallback to SIMULATION.")
                return SimulationYieldAggregator()
        else:
            print("\n🛡️ [SYSTEM] TRADING_MODE=PAPER. Initializing DEFI SIMULATION.")
            
        return SimulationYieldAggregator()

if __name__ == "__main__":
    agg = DeFiManager.get_aggregator()
