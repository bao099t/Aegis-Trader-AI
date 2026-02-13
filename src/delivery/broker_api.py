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
            
            # --- PHASE 59: HARD STOP-LOSS (EXCHANGE NATIVE) ---
            # Immediately protect the position
            qty = order.get('amount')
            if not qty and 'quantity' in order: qty = order['quantity'] # Handle sim vs ccxt structure
            if not qty: qty = 0 # Fallback
            
            self.adapter.place_stop_loss(ticker, direction, qty, stop_loss)
            # --------------------------------------------------
            
        return order

    def get_active_positions(self):
        """
        Calculates Net Open Positions.
        - Simulation: Replays log history.
        - Live: Queries Exchange Adapter directly.
        """
        # 1. Live Execution (Phase 43.5)
        if not self.simulation_mode:
            if hasattr(self.adapter, 'fetch_positions'):
                return self.adapter.fetch_positions()
            else:
                 print("  [Broker] Error: Adapter lacking fetch_positions()")
                 return []
        
        # 2. Simulation Mode (Log Replay)
        if not hasattr(self.adapter, 'log_path') or not os.path.exists(self.adapter.log_path):
             return []
             
        try:
            with open(self.adapter.log_path, "r") as f:
                orders = json.load(f)
            
            portfolio = {} 
            for o in orders:
                ticker = o.get('ticker')
                direction = o.get('direction') 
                if direction == "BULLISH":
                    portfolio[ticker] = "LONG"
                elif direction == "BEARISH":
                     portfolio[ticker] = "FLAT"
            
            active = [t for t, state in portfolio.items() if state == "LONG"]
            return active
            
        except Exception as e:
            print(f"  [Broker] Error reconciling portfolio: {e}")
            return []

if __name__ == "__main__":
    broker = BrokerAPI()
    broker.place_order("NVDA", "BULLISH", 5.0, 120.5, 115.0)
