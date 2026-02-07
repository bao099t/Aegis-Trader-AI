import os
import json
import time

class BrokerAPI:
    """
    Simulation/Alpha Connector for Automated Execution.
    In a real scenario, this would use Alpaca-trade-api or similar.
    We are implementing a 'Safe Execution Layer' for Paper Trading.
    """
    def __init__(self, simulation_mode=True):
        self.simulation_mode = simulation_mode
        self.orders_log = "data/broker_orders.json"
        self._ensure_log()

    def _ensure_log(self):
        os.makedirs(os.path.dirname(self.orders_log), exist_ok=True)
        if not os.path.exists(self.orders_log):
            with open(self.orders_log, "w") as f:
                json.dump([], f)

    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        """
        Simulates/Executes an order placement.
        """
        order = {
            "order_id": f"ORD_{int(time.time())}",
            "ticker": ticker,
            "direction": direction,
            "size": f"{size_pct:.2f}%",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "status": "EXECUTED" if self.simulation_mode else "PENDING",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Load and append
        with open(self.orders_log, "r") as f:
            orders = json.load(f)
        
        orders.append(order)
        
        with open(self.orders_log, "w") as f:
            json.dump(orders, f, indent=4)
            
        print(f"  [Broker] {order['status']}: {direction} {ticker} at ${entry_price} | SL: ${stop_loss}")
        return order

    def get_active_orders(self):
        with open(self.orders_log, "r") as f:
            return json.load(f)

if __name__ == "__main__":
    broker = BrokerAPI()
    broker.place_order("NVDA", "BULLISH", 5.0, 120.5, 115.0)
