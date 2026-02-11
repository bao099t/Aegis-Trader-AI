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
            
        try:
            # 1. Map Symbol (Simplistic mapping for now)
            # Assumption: Internal Tickers are like 'BTC-USD', 'NVDA'
            # CCXT expects 'BTC/USDT' or 'NVDA/USD' usually.
            symbol = ticker.replace('-', '/') 
            if '/' not in symbol and len(symbol) > 4: # Crypto guess
                 symbol += '/USDT' # Default to USDT pair for crypto
            
            # 2. Map Side
            side = 'buy' if direction == 'BULLISH' else 'sell'
            
            # 3. Dynamic Position Sizing (Compound Interest)
            # Fetch Free Balance (Assuming USDT for Crypto)
            balance = self.exchange.fetch_free_balance()
            usdt_bal = balance.get('USDT', balance.get('USD', 0))
            
            if usdt_bal < 10: # Minimum execution
                print(f"  [CCXT] ⚠️ Insufficient Funds (${usdt_bal}). Min $10 required.")
                return None
                
            # Allocation Amount
            alloc_amount = usdt_bal * (size_pct / 100.0)
            quantity = alloc_amount / entry_price
            
            print(f"  [CCXT] Executing LIVE {side.upper()} on {symbol}")
            print(f"         Balance: ${usdt_bal:.2f} | Size: {size_pct}% (${alloc_amount:.2f})")
            print(f"         Qty: {quantity:.6f} @ ${entry_price}")
            
            # 4. Execute Limit Order (Safety First)
            # We use Limit order to avoid slippage.
            order = self.exchange.create_order(symbol, 'limit', side, quantity, entry_price)
            
            # 5. Stop Loss Execution? 
            # Many exchanges require a separate call for OCO or Stop Market.
            # For Phase 9, we start with the Entry. Stop Loss is managed by the Shepherd (Exit Logic).
            
            print(f"  [CCXT] ✅ Order Success: ID {order['id']}")
            return order
            
        except Exception as e:
            print(f"  [CCXT] ❌ Execution Failed: {e}")
            return None

    def fetch_positions(self):
        """
        Fetches real-time balances/positions from the exchange.
        """
        if not self.exchange:
            return []
            
        try:
            # 1. Fetch Balance (Spot)
            # For Futures, we might need fetch_positions()
            # We try standard balance first.
            bal = self.exchange.fetch_balance()
            
            active_assets = []
            
            # Check Non-Zero Total Balance
            if 'total' in bal:
                for currency, amount in bal['total'].items():
                    if amount > 0:
                        # Normalize Ticker?
                        # Internal system uses BTC-USD. Exchange has BTC.
                        # Simple Heuristic: If it's a known crypto, append -USD
                        # For now, just return raw currency, logic elsewhere can handle fuzzy match if needed.
                        # Or better: return f"{currency}-USD" check?
                        # Let's return raw for safety.
                        active_assets.append(currency)
            
            print(f"  [CCXT] Active Positions: {active_assets}")
            return active_assets
            
        except Exception as e:
            print(f"  [CCXT] Fetch Error: {e}")
            return []
