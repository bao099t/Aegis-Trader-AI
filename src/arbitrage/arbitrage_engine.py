import time
import random

class ArbitrageEngine:
    """
    AEGIS ARBITRAGE ENGINE (Phase 7.1)
    Detects and exploits price discrepancies between multiple exchanges.
    """
    def __init__(self, exchanges=None, base_fee=0.001):
        self.exchanges = exchanges or ["BINANCE", "COINBASE", "KRAKEN"]
        self.base_fee = base_fee # 0.1% base fee
        self.order_books = {ext: {"bid": 0, "ask": 0} for ext in self.exchanges}

    def update_price(self, exchange, bid, ask):
        """Update the internal order book state for an exchange."""
        if exchange in self.order_books:
            self.order_books[exchange]["bid"] = bid
            self.order_books[exchange]["ask"] = ask

    def find_cross_spreads(self):
        """Standard A->B Cross-exchange scan."""
        opportunities = []
        for buy_ex in self.exchanges:
            for sell_ex in self.exchanges:
                if buy_ex == sell_ex: continue
                buy_price = self.order_books[buy_ex]["ask"]
                sell_price = self.order_books[sell_ex]["bid"]
                if buy_price == 0 or sell_price == 0: continue
                spread_pct = (sell_price / buy_price - 1) * 100
                net_spread_pct = spread_pct - (self.base_fee * 2 * 100)
                if net_spread_pct > 0.05: # Lowered threshold for demo
                    opportunities.append({
                        "type": "CROSS_EXCHANGE",
                        "route": f"{buy_ex} -> {sell_ex}",
                        "net_profit_pct": net_spread_pct
                    })
        return opportunities

    def find_triangular_spreads(self, prices):
        """
        Detects triangular arbitrage opportunities.
        Example: USD -> BTC -> ETH -> USD
        """
        # prices = {'BTC/USD': 50000, 'ETH/USD': 3000, 'ETH/BTC': 0.062}
        if not all(k in prices for k in ['BTC/USD', 'ETH/USD', 'ETH/BTC']):
            return []

        # Route 1: USD -> BTC -> ETH -> USD
        # 1. Buy BTC with USD (Cost = price_btc)
        # 2. Buy ETH with BTC (Cost = 1/price_eth_btc)
        # 3. Sell ETH for USD (Price = price_eth)
        
        # Calculation: (1 / price_btc) * (1 / price_eth_btc) * price_eth
        # Simpler: (price_eth) / (price_btc * price_eth_btc)
        
        profit_ratio = prices['ETH/USD'] / (prices['BTC/USD'] * prices['ETH/BTC'])
        net_profit_pct = (profit_ratio - 1 - (self.base_fee * 3)) * 100
        
        if net_profit_pct > 0.02:
            return [{
                "type": "TRIANGULAR",
                "route": "USD -> BTC -> ETH -> USD",
                "net_profit_pct": net_profit_pct
            }]
        
        return []

    def simulate_feed(self, iterations=50):
        base_prices = {'BTC/USD': 50000.0, 'ETH/USD': 3000.0, 'ETH/BTC': 0.06}
        print(f"--- Starting Advanced Arbitrage Simulation ---")
        
        for i in range(iterations):
            # Market drift
            for k in base_prices: base_prices[k] *= random.uniform(0.999, 1.001)
            
            # Cross Exchange Simulation
            for ex in self.exchanges:
                drift = random.uniform(0.998, 1.002)
                self.update_price(ex, base_prices['BTC/USD']*drift*0.999, base_prices['BTC/USD']*drift*1.001)
            
            opps = self.find_cross_spreads()
            opps += self.find_triangular_spreads(base_prices)
            
            for o in opps:
                print(f"[{o['type']}] Route: {o['route']} | Profit: {o['net_profit_pct']:.4f}%")

if __name__ == "__main__":
    engine = ArbitrageEngine()
    engine.simulate_feed(iterations=100)
