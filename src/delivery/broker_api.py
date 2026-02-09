import os
import json
import time

from src.delivery.exchange_adapter import SimulatedExchange, CCXTExchange

class BrokerAPI:
    """
    Advanced Broker Controller for Aegis Evolution (Phase 43).
    Supports multiple exchange adapters and multi-market execution.
    """
    def __init__(self, simulation_mode=True, exchange_id=None, api_key=None, secret=None):
        self.simulation_mode = simulation_mode
        if simulation_mode:
            self.adapter = SimulatedExchange()
        else:
            self.adapter = CCXTExchange(exchange_id, api_key, secret)

    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        """
        Executes an order (BUY_LONG, SELL_SHORT, etc.) via the selected adapter.
        """
        # --- Institutional Pre-Trade Check (Phase 43.3) ---
        # Note: In a full SOR implementation, we'd check spread here.
        
        print(f"  [Broker] Routing {direction} order for {ticker} (Size: {size_pct:.2f}%)...")
        
        order = self.adapter.place_order(ticker, direction, size_pct, entry_price, stop_loss)
        
        if order:
            print(f"  [Broker] {order['status']}: {direction} {ticker} at ${entry_price}")
        return order

    def get_active_orders(self):
        if hasattr(self.adapter, 'log_path'):
             with open(self.adapter.log_path, "r") as f:
                import json
                return json.load(f)
        return []

if __name__ == "__main__":
    broker = BrokerAPI()
    broker.place_order("NVDA", "BULLISH", 5.0, 120.5, 115.0)
