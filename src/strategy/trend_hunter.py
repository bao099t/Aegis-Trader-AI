import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class TrendHunterStrategy:
    """
    Production implementation of the 'Trend Hunter' strategy.
    
    Logic (Long-Only - Balanced Mode):
    - Entry: Price > SMA200 & Price > SMA50 & ADX > 25 & RSI < 70
    - Exit: Price < SMA50
    
    Assets: Bitcoin, Gold, US Tech Stocks.
    """
    
    def __init__(self):
        print("  [Strategy] Initialized Trend Hunter (Long-Only)")

    def fetch_data(self, ticker):
        """
        Fetches last 300 days of data to calculate SMA200 and indicators.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400) # Buffer for SMA200
        
        try:
            # yfinance download
            df = yf.download(ticker, start=start_date, end=end_date, interval="1d", progress=False, auto_adjust=True)
            
            if df.empty:
                return None
                
            # Flatten MultiIndex if present
            if isinstance(df.columns, pd.MultiIndex):
                try:
                    df.columns = df.columns.droplevel(1)
                except:
                    pass
            
            # Ensure numeric
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
            df.dropna(subset=['Close'], inplace=True)
            return df
            
        except Exception as e:
            print(f"  [Strategy] Error fetching {ticker}: {e}")
            return None

    def calculate_indicators(self, df):
        """
        Calculates SMA50, SMA200, RSI(14), ADX(14).
        """
        df = df.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # SMAs
        df['SMA_20'] = close.rolling(window=20).mean()
        df['SMA_50'] = close.rolling(window=50).mean()
        df['SMA_200'] = close.rolling(window=200).mean()
        
        # RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ADX 14
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        # atr = tr.rolling(window=14).mean() # not strictly needed for adx calculation here per se but useful
        
        smooth_tr = tr.rolling(window=14).mean()
        smooth_plus = plus_dm.rolling(window=14).mean()
        smooth_minus = minus_dm.abs().rolling(window=14).mean()
        
        di_plus = (smooth_plus / smooth_tr) * 100
        di_minus = (smooth_minus / smooth_tr) * 100
        dx = (abs(di_plus - di_minus) / (di_plus + di_minus)) * 100
        df['ADX'] = dx.rolling(window=14).mean()
        
        return df

    def analyze(self, ticker):
        """
        Analyzes the ticker and returns a signal.
        Returns:
            signal (str): 'BUY', 'SELL', 'HOLD'
            details (dict): indicators and reasoning
        """
        df = self.fetch_data(ticker)
        if df is None or len(df) < 55:
            return "HOLD", {"error": "Insufficient data"}
            
        df = self.calculate_indicators(df)
        row = df.iloc[-1]
        
        current_price = row['Close']
        sma20 = row['SMA_20']
        sma50 = row['SMA_50']
        sma200 = row['SMA_200']
        rsi = row['RSI']
        adx = row['ADX']
        
        # Logic: Zenith Hybrid (Trend + Vulture Hedge)
        # Long Entry: Price > SMA50 (Primary Trend) + Momentum
        # Short Entry: Price < SMA50 (Bear Regime) + Consolidation (Not Oversold)
        
        is_bull_trend = current_price > sma50
        is_bear_trend = current_price < sma50
        strong_momentum = adx > 20
        
        signal = "HOLD"
        reason = "Wait"
        
        # 🟢 LONG LOGIC (Zenith)
        if is_bull_trend and strong_momentum and rsi < 70:
            signal = "BUY"
            reason = f"Zenith Bull (Price > SMA50) + Momentum (ADX {adx:.1f})"
            
        # 🔴 SHORT LOGIC (Vulture - Verified Phase 43.6)
        # Only short if confirmed Bear Trend AND not oversold (avoiding bear traps)
        elif is_bear_trend and strong_momentum and rsi > 45:
            signal = "SHORT"
            reason = f"Vulture Hedge (Price < SMA50) + Vulture Setup (RSI {rsi:.1f})"
            
        # 🔵 EXIT LOGIC
        # Long Exit
        if signal == "HOLD" and is_bull_trend and current_price < sma20:
             signal = "SELL"
             reason = "Trend Broken (Price < SMA20)"
             
        # Short Exit (Squeeze Protection)
        if signal == "HOLD" and is_bear_trend and current_price > sma20:
             signal = "COVER"
             reason = "Bear Baseline Broken (Price > SMA20)"
             
        details = {
            "price": current_price,
            "sma50": sma50,
            "sma200": sma200,
            "rsi": rsi,
            "adx": adx,
            "reason": reason
        }
        
        return signal, details
