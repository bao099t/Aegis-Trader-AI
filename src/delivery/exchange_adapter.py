import time
import json
import os

class BaseExchange:
    """Base interface for all exchange interactions."""
    def place_stop_loss(self, ticker, direction, size_pct, stop_price):
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

    def place_stop_loss(self, ticker, direction, quantity, stop_price):
        """
        Simulates placing a generic Stop Market order on the exchange.
        """
        order = {
            "order_id": f"SL_{int(time.time())}",
            "ticker": ticker,
            "type": "STOP_MARKET",
            "direction": "SELL" if direction == "BULLISH" else "BUY",
            "quantity": quantity, # In simulation, we might not track precise qty, but good to log
            "stop_price": stop_price,
            "status": "PENDING (On Exchange)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"  [SimExchange] 🛡️ HARD STOP-LOSS PLACED: {ticker} @ {stop_price}")
        
        with open(self.log_path, "r") as f:
            orders = json.load(f)
        orders.append(order)
        with open(self.log_path, "w") as f:
            json.dump(orders, f, indent=4)
        return order


class CCXTExchange(BaseExchange):
    """Institutional-grade execution via CCXT with Multi-Currency Support."""
    def __init__(self, exchange_id, api_key, secret):
        try:
            import ccxt
            self.exchange = getattr(ccxt, exchange_id)({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'} # Default to spot
            })
            self.exchange.load_markets() # Pre-load markets for symbol validation
            print(f"  [CCXT] Connected to {exchange_id} successfully.")
        except (ImportError, AttributeError) as e:
            print(f"  [CCXT] Error: CCXT not installed or exchange {exchange_id} invalid: {e}")
            self.exchange = None
        except Exception as e:
            print(f"  [CCXT] Connection Failed: {e}")
            self.exchange = None

    def get_quote_currency(self, symbol):
        """
        Determines the quote currency (Collateral) for a given symbol.
        Rules:
        - If symbol contains '/', split it (e.g., 'BTC/USDT' -> 'USDT').
        - If symbol is a Stock/Forex (no '/'), default to 'USD'.
        """
        if '/' in symbol:
            return symbol.split('/')[1]
        return 'USD'

    def normalize_symbol(self, ticker):
        """
        Maps internal ticker to exchange symbol.
        - 'BTC-USD' -> 'BTC/USDT' (Crypto default)
        - 'NVDA' -> 'NVDA' (Stock)
        """
        if '-' in ticker: # Likely Crypto 'BTC-USD'
            base = ticker.split('-')[0]
            # Check if exchange supports USDC or USDT, prioritize USDT for now
            return f"{base}/USDT"
        
        # Check if it's a raw crypto symbol like 'BTC'
        if len(ticker) <= 4 and ticker.isupper() and ticker != 'USDT':
             # Try to see if it's in markets
             if self.exchange:
                 if f"{ticker}/USDT" in self.exchange.markets:
                     return f"{ticker}/USDT"
        
        return ticker # Return as-is for Stocks

    def place_order(self, ticker, direction, size_pct, entry_price, stop_loss):
        if not self.exchange:
            print("  [CCXT] Order Blocked: Exchange not initialized.")
            return None
            
        try:
            # 1. Normalize Symbol & Currency
            symbol = self.normalize_symbol(ticker)
            quote_currency = self.get_quote_currency(symbol)
            side = 'buy' if direction == 'BULLISH' else 'sell'
            
            # 2. Fetch Available Balance (Safe check)
            balance = self.exchange.fetch_free_balance()
            available_cash = balance.get(quote_currency, 0.0)
            
            print(f"  [CCXT] Preparing {side.upper()} logic for {symbol} using {quote_currency}...")
            print(f"         Available {quote_currency}: {available_cash:.2f}")

            if available_cash <= 0:
                print(f"  [CCXT] ❌ ABORT: No {quote_currency} available.")
                return None

            # 3. Safe Position Sizing (The 'Money Safety' Fix)
            # - Cap size at 99% to reserve 1% for fees (Buffer)
            # - Check Minimum Order Size (approx $10 usually)
            
            alloc_pct = min(size_pct, 99.0) / 100.0
            alloc_amount = available_cash * alloc_pct
            
            if alloc_amount < 10.0: # Hardcoded safety floor
                print(f"  [CCXT] ⚠️ Insufficient Capital for trade (${alloc_amount:.2f}). Min $10 required.")
                return None
                
            # Calculate Quantity
            quantity = alloc_amount / entry_price
            
            # 4. Precision Truncation (Avoid API errors with too many decimals)
            if symbol in self.exchange.markets:
                market = self.exchange.markets[symbol]
                quantity = self.exchange.amount_to_precision(symbol, quantity)
                entry_price = self.exchange.price_to_precision(symbol, entry_price)
            else:
                 # Fallback formatting if market not loaded
                 quantity = "{:.6f}".format(float(quantity))
                 entry_price = "{:.2f}".format(float(entry_price))

            print(f"  [CCXT] Executing LIVE {side.upper()} on {symbol}")
            print(f"         Allocated: ${alloc_amount:.2f} ({alloc_pct*100:.1f}%)")
            print(f"         Qty: {quantity} @ ${entry_price}")
            
            # 5. Execute Limit Order
            order = self.exchange.create_order(symbol, 'limit', side, quantity, entry_price)
            
            print(f"  [CCXT] ✅ Order Success: ID {order['id']}")
            return order
            
        except Exception as e:
            print(f"  [CCXT] ❌ Execution Failed: {e}")
            return None

    def place_stop_loss(self, ticker, direction, quantity, stop_price):
        """
        Executes a STOP_MARKET order to protect the position.
        """
        if not self.exchange:
            return None
            
        try:
            symbol = self.normalize_symbol(ticker)
            # If we bought (BULLISH), we need to SELL to stop loss
            side = 'sell' if direction == 'BULLISH' else 'buy'
            
            params = {'stopPrice': stop_price}
            
            print(f"  [CCXT] 🛡️ Placing HARD STOP-LOSS for {symbol}...")
            print(f"         Stop Price: {stop_price} | Qty: {quantity}")

            # Note: 'stop_market' is widely supported but params vary.
            # Binance: 'stopPrice'
            order = self.exchange.create_order(symbol, 'stop_market', side, quantity, params=params)
            
            print(f"  [CCXT] ✅ Stop-Loss Set: ID {order['id']}")
            return order
            
        except Exception as e:
            print(f"  [CCXT] ❌ Stop-Loss Failed: {e}")
            print("  ⚠️ CRITICAL: MANUAL INTERVENTION REQUIRED TO SET STOP LOSS.")
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
