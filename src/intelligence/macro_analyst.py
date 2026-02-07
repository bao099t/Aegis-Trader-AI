import yfinance as yf
import time

class MacroAnalyst:
    def __init__(self):
        self.cache = {}
        self.CACHE_DURATION = 1800 # 30 minutes cache (VIX changes fast but trend is slow)
        self.tickers = ["^VIX", "^GSPC"] # VIX and S&P 500

    def analyze(self):
        now = time.time()
        if 'macro' in self.cache:
            if now - self.cache['macro']['timestamp'] < self.CACHE_DURATION:
                return self.cache['macro']['data']

        try:
            print("  [Macro] Assessing Market Climate (VIX & SPY)...")
            data = yf.download(self.tickers, period="1y", interval="1d", progress=False)
            
            # Extract most recent data
            # Handle MultiIndex columns if present
            try:
                # Typical yfinance struct: Close -> [^GSPC, ^VIX]
                vix_close = data['Close']['^VIX'].iloc[-1]
                spy_close = data['Close']['^GSPC'].iloc[-1]
                spy_hist = data['Close']['^GSPC']
            except:
                # Fallback if structure flat
                return None

            # 1. VIX Analysis (Fear Gauge)
            vix_level = round(float(vix_close), 2)
            market_mood = "NORMAL"
            if vix_level > 30:
                market_mood = "EXTREME FEAR (CRASH RISK)"
            elif vix_level > 20:
                market_mood = "NERVOUS / VOLATILE"
            elif vix_level < 12:
                market_mood = "COMPLACENT (GREED)"

            # 2. S&P 500 Trend (SMA 200)
            sma200 = spy_hist.rolling(window=200).mean().iloc[-1]
            trend = "SIDEWAYS"
            if spy_close > sma200:
                trend = "BULL MARKET (Above MA200)"
            else:
                trend = "BEAR MARKET (Below MA200)"

            result = {
                "vix": vix_level,
                "mood": market_mood,
                "spy_trend": trend,
                "risk_status": "RISK-OFF" if vix_level > 25 or "BEAR" in trend else "RISK-ON"
            }
            
            self.cache['macro'] = {'data': result, 'timestamp': now}
            return result

        except Exception as e:
            print(f"  [Macro] Error: {e}")
            return None

if __name__ == "__main__":
    ma = MacroAnalyst()
    print(ma.analyze())
