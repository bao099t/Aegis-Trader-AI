import yfinance as yf
import pandas as pd
import time

class InstitutionalAnalyst:
    def __init__(self):
        self.cache = {}
        self.CACHE_DURATION = 3600 # 1 hour
        # Sector Mapping (Top US tickers to ETFs)
        self.SECTOR_MAP = {
            "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AMD": "XLK", "GOOGL": "XLC", "META": "XLC", "NFLX": "XLC",
            "JPM": "XLF", "GS": "XLF", "BAC": "XLF", "V": "XLF", "MA": "XLF",
            "TSLA": "XLY", "AMZN": "XLY", "NKE": "XLY", "SBUX": "XLY",
            "PFE": "XLV", "MRNA": "XLV", "UNH": "XLV", "JNJ": "XLV",
            "XOM": "XLE", "CVX": "XLE",
            "WMT": "XLP", "KO": "XLP", "PEP": "XLP", "COST": "XLP"
        }

    def get_market_data(self, tickers):
        """Helper to fetch bulk data."""
        try:
             return yf.download(tickers, period="3mo", interval="1d", progress=False)
        except:
             return None

    def analyze(self, ticker):
        now = time.time()
        if ticker in self.cache:
            if now - self.cache[ticker]['timestamp'] < self.CACHE_DURATION:
                return self.cache[ticker]['data']

        try:
            print(f"  [Inst] Auditing Institutional Edge for {ticker}...")
            # 1. Ticker Data & SPY for Relative Strength
            sector_etf = self.SECTOR_MAP.get(ticker.upper())
            fetch_list = [ticker, "SPY"]
            if sector_etf: fetch_list.append(sector_etf)
            
            data = self.get_market_data(fetch_list)
            if data is None or 'Close' not in data:
                return None
            
            # Extract Closes & Volumes
            closes = data['Close']
            volumes = data['Volume'] if 'Volume' in data else None
            
            # --- VOLUME DELTA ---
            vol_score = "NORMAL"
            vol_msg = "Volume is steady."
            if volumes is not None and ticker in volumes:
                avg_vol = volumes[ticker].tail(10).mean()
                last_vol = volumes[ticker].iloc[-1]
                delta = last_vol / avg_vol if avg_vol > 0 else 1
                if delta > 2.0:
                    vol_score = "HIGH"
                    vol_msg = f"⚡ VOLUME SPIKE: {delta:.1f}x (Smart Money detected)."
                elif delta < 0.5:
                    vol_score = "LOW"
                    vol_msg = "Low interest/Volume."

            # --- RELATIVE STRENGTH (vs SPY) ---
            rs_score = "NEUTRAL"
            rs_msg = "Moving with the market."
            perf_30d_ticker = (closes[ticker].iloc[-1] / closes[ticker].iloc[-20]) - 1
            perf_30d_spy = (closes["SPY"].iloc[-1] / closes["SPY"].iloc[-20]) - 1
            alpha = perf_30d_ticker - perf_30d_spy
            
            if alpha > 0.05:
                rs_score = "LEADER"
                rs_msg = f"🏆 LEADER: Outperforming SPY by {alpha*100:.1f}%."
            elif alpha < -0.05:
                rs_score = "LAGGARD"
                rs_msg = f"🐢 LAGGARD: Underperforming SPY by {abs(alpha)*100:.1f}%."

            # --- SECTOR CONVERGENCE ---
            sector_status = "UNKNOWN"
            sector_msg = "No sector data."
            if sector_etf and sector_etf in closes:
                sector_perf_5d = (closes[sector_etf].iloc[-1] / closes[sector_etf].iloc[-5]) - 1
                if sector_perf_5d > 0.01:
                    sector_status = "BULLISH"
                    sector_msg = f"Sector ({sector_etf}) is Strong."
                elif sector_perf_5d < -0.01:
                    sector_status = "BEARISH"
                    sector_msg = f"⚠️ Sector ({sector_etf}) is Weak."
                else:
                    sector_status = "NEUTRAL"
                    sector_msg = f"Sector ({sector_etf}) is Sideways."

            result = {
                "volume": {"score": vol_score, "msg": vol_msg},
                "relative_strength": {"score": rs_score, "msg": rs_msg},
                "sector": {"status": sector_status, "msg": sector_msg},
                "ticker": ticker
            }
            
            self.cache[ticker] = {'data': result, 'timestamp': now}
            return result

        except Exception as e:
            print(f"  [Inst] Audit Error: {e}")
            return None

if __name__ == "__main__":
    ia = InstitutionalAnalyst()
    print(ia.analyze("NVDA"))
