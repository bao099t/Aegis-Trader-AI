import time
import json
import os

class BaseExchange:
    """Base interface for all exchange interactions."""
    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        raise NotImplementedError

    def fetch_balance(self):
        raise NotImplementedError

class SimulatedExchange(BaseExchange):
    """Local JSON-based simulation for paper trading."""
    def __init__(self, log_path="data/broker_orders.json"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump([], f)

    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        order = {
            "order_id": f"SIM_{int(time.time())}",
            "ticker": ticker,
            "direction": direction,
            "size": f"{size_pct:.2f}%",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "status": "EXECUTED",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.log_path, "r") as f:
            orders = json.load(f)
        orders.append(order)
        with open(self.log_path, "w") as f:
            json.dump(orders, f, indent=4)
        return order

class CCXTExchange(BaseExchange):
    """Institutional-grade execution via CCXT."""
    def __init__(self, exchange_id, api_key, secret):
        try:
            import ccxt
            self.exchange = getattr(ccxt, exchange_id)({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True
            })
        except (ImportError, AttributeError):
            print(f"  [CCXT] Error: CCXT not installed or exchange {exchange_id} invalid.")
            self.exchange = None

    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        if not self.exchange:
            print("  [CCXT] Order Blocked: Exchange not initialized.")
            return None
        
        # In production, we would map internal tickers to exchange symbols
        # and handle market/limit orders via self.exchange.create_order(...)
        print(f"  [CCXT] (Live Target) Would place {direction} on {ticker}")
        return {"status": "CCXT_READY", "ticker": ticker, "direction": direction}
