import yfinance as yf
import pandas as pd
import datetime
import os
import json

class UniverseDiscoverer:
    """
    AEGIS UNIVERSE DISCOVERER (Autonomous Scout)
    
    Logic:
    1. Scan Sector ETFs (XLK, XLE, etc.) for Momentum.
    2. Identify the 'Leading Sector' of the current regime.
    3. Extract the 'Top Holdings' of that Sector ETF (Future-Proof).
    4. Update 'watchlist.txt' with these assets (Broad Universe).
    """
    
    def __init__(self, watchlist_path="watchlist.txt"):
        self.watchlist_path = watchlist_path
        
        # Sector Map: ETF -> Name
        self.SECTORS = {
            "XLK": "Technology",
            "XLE": "Energy",
            "XLF": "Finance",
            "XLV": "Healthcare",
            "XLY": "Consumer Discret.",
            "XLP": "Consumer Staples",
            "GLD": "Gold",
            "SOXX": "Semiconductors"
        }
        
        # Fallback Leaders (If ETF scraping fails)
        # This ensures we aren't left empty-handed if yfinance struct changes
        self.FALLBACK_LEADERS = {
            "XLK": ["NVDA", "MSFT", "AAPL", "AVGO", "ORCL", "CRM", "AMD"],
            "XLE": ["XOM", "CVX", "COP", "SLB", "EOG"],
            "XLF": ["JPM", "V", "MA", "BAC", "GS", "MS"],
            "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
            "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
            "XLP": ["PG", "COST", "PEP", "KO", "WMT"],
            "GLD": ["NEM", "GOLD", "AEM", "RGLD", "FNV"],
            "SOXX": ["NVDA", "AVGO", "AMD", "QCOM", "TXN"]
        }

        # Always include these Core Assets (The "Generals")
        self.CORE_ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "TSLA"]

    def get_leading_sectors(self, top_n=3):
        """Identifies top sectors by 5-day Relative Strength vs SPY."""
        print("  [Scout] Scanning Sector Momentum...")
        tickers = list(self.SECTORS.keys()) + ["SPY"]
        try:
            data = yf.download(tickers, period="10d", interval="1d", progress=False)['Close']
            
            # Helper to get latest price (handle formatting)
            def get_latest(ticker):
                if isinstance(data, pd.DataFrame):
                    # Check if MultiIndex columns
                    if isinstance(data.columns, pd.MultiIndex):
                        # Try to find the ticker in level 1
                        pass # yfinance structure varies, usually Close -> Ticker
                    return data[ticker].iloc[-1]
                return 0

            # Calculate 5-day Perf
            perf = {}
            for t in tickers:
                if t in data.columns:
                    series = data[t]
                    if len(series) >= 6:
                        p = (series.iloc[-1] / series.iloc[-6]) - 1
                        perf[t] = p
            
            if "SPY" not in perf: return ["XLK", "SOXX", "XLY"] # Default to Risk-On
            
            spy_perf = perf["SPY"]
            
            # Rank by Relative Strength
            rs = []
            for t in self.SECTORS:
                if t in perf:
                    rel = perf[t] - spy_perf
                    rs.append((t, rel))
            
            rs.sort(key=lambda x: x[1], reverse=True)
            leaders = [x[0] for x in rs[:top_n]]
            
            print(f"  [Scout] Leading Sectors: {leaders}")
            return leaders
            
        except Exception as e:
            print(f"  [Scout] Sector Scan Error: {e}. Defaulting to Tech.")
            return ["XLK", "SOXX", "XLY"]

    def get_etf_holdings(self, etf):
        """
        Attempts to fetch top holdings of an ETF (Future-Proof).
        Uses yfinance Ticker.funds_data (Live) or fallback.
        """
        try:
            print(f"  [Scout] Fetching Live Holdings for {etf}...")
            ticker = yf.Ticker(etf)
            if hasattr(ticker, 'funds_data') and ticker.funds_data:
                holdings_df = ticker.funds_data.top_holdings
                if holdings_df is not None and not holdings_df.empty:
                    # Convert index (Symbols) to list
                    symbols = holdings_df.index.tolist()
                    # Clean up symbols (sometimes they have suffixes like .DE)
                    # US tickers usually don't, but let's be safe.
                    clean_symbols = [s.replace('.', '-') for s in symbols]
                    print(f"    -> Found Live: {clean_symbols[:5]}...")
                    return clean_symbols
            
            # If we get here, no data found via API
            print(f"    -> API empty for {etf}. Using Fallback.")
            return self.FALLBACK_LEADERS.get(etf, [])
            
        except Exception as e:
             print(f"    -> API Error for {etf}: {e}. Using Fallback.")
             return self.FALLBACK_LEADERS.get(etf, [])

    def validate_ticker(self, ticker):
        """Sanity check to ensure ticker is tradeable."""
        if '.' in ticker: return False # Skip dot tickers (BRK.B) for now to avoid yf issues
        try:
            # Quick check
            t = yf.Ticker(ticker)
            # Just check if it has history
            hist = t.history(period="1d")
            if hist.empty: return False
            return True
        except:
            return False

    def refresh_universe(self):
        """Main execution method."""
        print("\n🔭 [Universe Discoverer] Starting Autonomous Scan...")
        
        # 1. Get Leaders
        leaders = self.get_leading_sectors(top_n=3)
        
        # 2. Gather Assets
        new_universe = set(self.CORE_ASSETS) # Start with Generals
        
        for sec in leaders:
            holdings = self.get_etf_holdings(sec)
            print(f"  > Expanding into {self.SECTORS[sec]} ({sec}): Found {len(holdings)} assets.")
            for h in holdings:
                # DATA VALIDATION (Fix 2)
                if self.validate_ticker(h):
                    new_universe.add(h)
                else:
                    print(f"    [Scout] Dropped Invalid/Risky Ticker: {h}")
                
        # 3. Save to watchlist.txt
        sorted_list = sorted(list(new_universe))
        
        print(f"  [Scout] Universe Updated: {len(sorted_list)} Assets.")
        print(f"  {sorted_list}")
        
        try:
            with open(self.watchlist_path, 'w') as f:
                for item in sorted_list:
                    f.write(f"{item}\n")
            return sorted_list
        except Exception as e:
            print(f"  [Scout] Critical Error saving watchlist: {e}")
            return []

if __name__ == "__main__":
    ud = UniverseDiscoverer()
    ud.refresh_universe()
