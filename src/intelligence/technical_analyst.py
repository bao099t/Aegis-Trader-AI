import yfinance as yf
import pandas as pd
import numpy as np
import time

class TechnicalAnalyst:
    def __init__(self):
        self.cache = {}
        self.CACHE_DURATION = 3600 # 1 hour cache for charts is enough

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_adx(self, high, low, close, period=14):
        """Calculates Average Directional Index (ADX) to detect market strength."""
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = minus_dm.abs()
        
        tr = pd.concat([high - low, 
                        (high - close.shift()).abs(), 
                        (low - close.shift()).abs()], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
        adx = dx.rolling(window=period).mean()
        return adx

    def analyze(self, ticker):
        now = time.time()
        # Check cache
        if ticker in self.cache:
            if now - self.cache[ticker]['timestamp'] < self.CACHE_DURATION:
                return self.cache[ticker]['data']

        try:
            print(f"  [Tech] Pulling charts for {ticker}...")
            # Download 6 months of data
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            
            if len(df) < 50:
                return None
                
            # Flatten indices if needed (yfinance sometimes uses MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            close = df['Close']
            
            # Calculate Indicators
            # 1. RSI (14)
            # Using simple rolling mean for approximation to keep it fast/dependency-free (or use EMA if preferred, simple is fine for MVP)
            # Actually standard RSI uses Wilder's Smoothing, but Simple Rolling is often used in basic scripts.
            # Let's stick to simple rolling for stability unless user complains.
            rsi_series = self.calculate_rsi(close, 14)
            current_rsi = rsi_series.iloc[-1]
            
            # 2. SMA 50 & 200
            sma50 = close.rolling(window=50).mean().iloc[-1]
            sma200 = close.rolling(window=200).mean().iloc[-1] if len(df) > 200 else None
            
            # 3. ADX (Regime Detection - Phase 26)
            adx_series = self.calculate_adx(df['High'], df['Low'], close, 14)
            current_adx = adx_series.iloc[-1]
            
            regime = "NORMAL"
            if current_adx > 25:
                regime = "TRENDING"
            elif current_adx < 20:
                regime = "CHOPPY / SIDEWAY"
            
            current_price = close.iloc[-1]
            
            # 3. Verdict
            signals = []
            trend = "NEUTRAL"
            
            # Trend Logic
            if sma200:
                if current_price > sma200:
                    trend = "UPTREND"
                else:
                    trend = "DOWNTREND"
            
            # RSI Logic
            rsi_state = "NEUTRAL"
            if current_rsi > 70:
                rsi_state = "OVERBOUGHT"
                signals.append("RSI > 70 (Overheated)")
            elif current_rsi < 30:
                rsi_state = "OVERSOLD"
                signals.append("RSI < 30 (Bounce likely)")
                
            # Cross Logic
            if sma50 and sma200 and sma50 > sma200:
                signals.append("Golden Cross (Bullish)")
            
            result = {
                "rsi": round(float(current_rsi), 2),
                "rsi_state": rsi_state,
                "sma50": round(float(sma50), 2) if sma50 else 0,
                "sma200": round(float(sma200), 2) if sma200 else 0,
                "adx": round(float(current_adx), 2) if not np.isnan(current_adx) else 0,
                "regime": regime,
                "trend": trend,
                "signals": signals
            }
            
            self.cache[ticker] = {'data': result, 'timestamp': now}
            return result

        except Exception as e:
            print(f"  [Tech] Error analyzing {ticker}: {e}")
            return None

if __name__ == "__main__":
    ta = TechnicalAnalyst()
    print(ta.analyze("NVDA"))
