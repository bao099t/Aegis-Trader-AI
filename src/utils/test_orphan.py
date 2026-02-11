import sys
import os
import json
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.delivery.broker_api import BrokerAPI

def test_orphan_protocol():
    print("Testing Orphan Protocol...")
    
    # 1. Setup Mock Broker Log
    broker = BrokerAPI(simulation_mode=True)
    log_path = broker.adapter.log_path
    
    # Inject a "Legacy" Buy Order for a stock NOT in Top 5 (e.g. 'IBM')
    fake_order = {
        "order_id": "LEGACY_TEST_01",
        "ticker": "IBM",
        "direction": "BULLISH",
        "size": "10%",
        "entry_price": 150.0,
        "status": "EXECUTED",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(log_path, "w") as f:
        json.dump([fake_order], f, indent=4)
        
    print(f"  [Test] Injected BUY order for IBM into {log_path}")
    
    # 2. Check Active Positions
    active = broker.get_active_positions()
    print(f"  [Test] Broker Reports Active: {active}")
    
    if "IBM" in active:
        print("  ✅ SUCCESS: IBM is detected as an Active Position.")
    else:
        print("  ❌ FAILURE: IBM was ignored.")

    # 3. Inject SELL to Clear
    sell_order = {
        "ticker": "IBM",
        "direction": "BEARISH",
        "status": "EXECUTED"
    }
    with open(log_path, "r") as f:
        orders = json.load(f)
    orders.append(sell_order)
    with open(log_path, "w") as f:
        json.dump(orders, f, indent=4)
        
    active_after = broker.get_active_positions()
    print(f"  [Test] After SELL, Active: {active_after}")
    
    if "IBM" not in active_after:
        print("  ✅ SUCCESS: IBM is properly cleared after SELL.")

if __name__ == "__main__":
    test_orphan_protocol()
