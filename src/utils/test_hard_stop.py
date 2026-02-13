import unittest
import sys
import os
import json
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.delivery.broker_api import BrokerAPI
from src.delivery.exchange_adapter import SimulatedExchange

class TestHardStopLoss(unittest.TestCase):
    def setUp(self):
        # Use a temporary log file
        self.test_log = "data/test_orders.json"
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.test_log), exist_ok=True)
        # Create empty list
        with open(self.test_log, "w") as f:
            json.dump([], f)
            
    def tearDown(self):
        if os.path.exists(self.test_log):
            os.remove(self.test_log)

    def test_hard_stop_loss_trigger(self):
        print("\n--- Testing Hard Stop-Loss Trigger ---")
        
        # Initialize Broker with Sim Adapter pointing to test log
        broker = BrokerAPI(simulation_mode=True)
        broker.adapter.log_path = self.test_log
        
        # Place a BUY order
        ticker = "BTC/USDT"
        entry_price = 50000.0
        stop_loss = 49000.0
        
        print(f"1. Placing Limit Buy Order for {ticker} @ ${entry_price}...")
        broker.place_order(ticker, "BULLISH", 10.0, entry_price, stop_loss)
        
        # Read the log file
        with open(self.test_log, 'r') as f:
            orders = json.load(f)
            
        # We expect 2 orders: 
        # 1. The Entry Limit Order
        # 2. The Stop Market Order
        
        print(f"2. Verifying Orders in Log (Count: {len(orders)})...")
        
        self.assertEqual(len(orders), 2, "Should have 2 orders (Entry + Stop Loss)")
        
        entry_order = orders[0]
        stop_order = orders[1]
        
        print(f"   [Order 1] {entry_order['direction']} {entry_order['ticker']} ({entry_order['status']})")
        print(f"   [Order 2] {stop_order['type']} {stop_order['stop_price']} ({stop_order['status']})")
        
        # Verify Entry
        self.assertEqual(entry_order['direction'], "BULLISH")
        
        # Verify Stop Loss
        self.assertEqual(stop_order['type'], "STOP_MARKET")
        self.assertEqual(stop_order['stop_price'], stop_loss)
        self.assertEqual(stop_order['direction'], "SELL") # Long entry -> Sell stop
        
        print("✅ Hard Stop-Loss Verified Successfully.")

if __name__ == '__main__':
    unittest.main()
