import pandas as pd
import numpy as np

class MeanReversionStrategy:
    """
    Sniper Strategy for Sideways/Choppy Markets.
    
    Philosophy: 
    When the market has no trend (ADX < 20), prices tend to revert to the mean.
    We buy fear (Oversold) and sell greed (Overbought).
    
    Logic:
    - Entry: RSI < 30 AND ADX < 25 (Ensure we are NOT in a strong downtrend)
    - Exit: RSI > 70 OR Price > Bollinger Upper Band
    """
    
    def __init__(self):
        self.name = "Mean Reversion (RSI Sniper)"
        from src.intelligence.predictor import PricePredictor
        self.predictor = PricePredictor()
        from src.simulation.data_loader import DataLoader
        self.loader = DataLoader()
        
    def prepare_data(self, df):
        """Calculates indicators needed for Mean Reversion."""
        df = df.copy()
        
        # Ensure numeric
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
            
        # 1. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 2. ADX (14) - True Calculation
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        # Fill NaNs with 0 to prevent propagation in recursive EWM
        up_move = up_move.fillna(0)
        down_move = down_move.fillna(0)
        tr = tr.fillna(0)
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        # Restore index to align with tr (pandas alignment is key)
        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)
        
        # Smooth using Wilder's Smoothing (alpha = 1/n)
        # Pandas ewm com = n - 1 matches standard EMA, but Wilder uses 1/n.
        # Wilder acc to Pandas: alpha=1/n. 
        # Using simple rolling for robustness/speed match with other parts (SMA) or use ewm.
        # Standard ADX uses 14 smoothed.
        
        tr_smooth = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean()
        plus_dm_smooth = pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean()
        minus_dm_smooth = pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean()
        
        # DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # DX
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        dx = dx.fillna(0) # Handle 0/0 case (Flat or Initial)
        
        # ADX
        df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
        
        # 3. Bollinger Bands (20, 2)
        df['BB_Mid'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
        
        # Clean NaNs created by windows
        df.dropna(inplace=True)
        return df

    def analyze(self, ticker):
        """
        Full analysis pipeline for Production.
        fetching data -> indicators -> signal -> AI Check.
        """
        # 1. Fetch Data
        df = self.loader.fetch_data(ticker, days=400) # Need 200 for SMA safe side
        if df is None or df.empty:
            return "HOLD", {"reason": "No Data"}
            
        # 2. Calculate Indicators
        df = self.prepare_data(df)
        
        # 3. Get Last Row
        row = df.iloc[-1]
        price = row['Close']
        rsi = row['RSI']
        adx = row.get('ADX', 0)
        sma50 = row.get('SMA_50', price) # Fallback
        bb_lower = row.get('BB_Lower', 0)
        bb_upper = row.get('BB_Upper', 999999)
        
        details = {
            "price": price,
            "rsi": rsi,
            "adx": adx,
            "bb_lower": bb_lower,
            "sma50": sma50,
            "reason": ""
        }
        
        # 4. Strategy Logic
        signal = "HOLD"
        
        # SAFETY: Don't trade if ADX > 25 (Trend is strong, don't revert)
        if adx > 25:
             details['reason'] = "Trend Active (ADX > 25)"
             return "HOLD", details
             
        # ENTRY LOGIC
        # Condition 1: RSI Oversold
        # Condition 2: Price below BB Lower (Extreme)
        if rsi < 30 and price < bb_lower:
            # Condition 3: AI Guardian
            ai_dir, ai_conf = self.predictor.predict(ticker)
            
            if ai_dir == "UP":
                signal = "BUY"
                details['reason'] = f"Sniper (RSI {rsi:.1f} + BB Break). AI Confirms UP ({ai_conf*100:.1f}%)"
            else:
                 signal = "HOLD"
                 details['reason'] = f"Sniper Signal BLOCKED by AI Guardian (Predicted DOWN: {ai_conf*100:.1f}%)"
                 
        # EXIT LOGIC
        elif rsi > 70 or price > bb_upper:
            signal = "SELL"
            details['reason'] = f"Overbought (RSI {rsi:.1f} or BB Break)"
            
        return signal, details

    def generate_signal(self, row):
        # Legacy method for simulation row-by-row if needed, 
        # but simulation now uses its own logic in run_simulation.py
        pass
