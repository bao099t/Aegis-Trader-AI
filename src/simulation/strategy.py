import pandas as pd
import numpy as np

class DailySurferStrategy:
    def __init__(self):
        pass

    def prepare_data(self, df):
        """
        Pre-calculates technical indicators for the entire dataframe.
        """
        df = df.copy()
        
        # Ensure we have required columns
        # yfinance columns are usually: Open, High, Low, Close, Volume
        # Check if columns are MultiIndex (if loaded from some sources), flatten if needed.
        # But DataLoader returns single text columns usually.
        
        # Ensure numeric
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with NaN in critical columns
        df.dropna(subset=['Close'], inplace=True)

        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # 1. EMAs / SMAs
        df['SMA_20'] = close.rolling(window=20).mean()
        df['SMA_50'] = close.rolling(window=50).mean()
        df['SMA_100'] = close.rolling(window=100).mean()
        df['SMA_200'] = close.rolling(window=200).mean()
        
        # 2. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. ATR (14)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        
        # 4. ADX (14)
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = minus_dm.abs()
        
        tr_smooth = tr.rolling(window=14).mean()
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr_smooth)
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
        df['ADX'] = dx.rolling(window=14).mean()
        
        # 5. Bollinger Bands (20, 2)
        df['BB_Mid'] = close.rolling(window=20).mean()
        df['BB_Std'] = close.rolling(window=20).std()
        df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
        
        return df

    def generate_signal(self, row):
        """
        Hyper-Alpha Mode: Dynamic Long/Short Trend Surfing.
        - Long Entry: Price > SMA50 + ADX > 20
        - Short Entry: Price < SMA50 + ADX > 20
        """
        if pd.isna(row['SMA_50']) or pd.isna(row['SMA_20']):
            return "HOLD"
            
        current_price = row['Close']
        sma20 = row['SMA_20']
        sma50 = row['SMA_50']
        adx = row['ADX']
        rsi = row['RSI']
        
        strong_momentum = adx > 20
        
        # 🟢 LONG LOGIC
        if current_price > sma50 and strong_momentum and rsi < 70:
            return "BUY"
        if current_price < sma20:
             return "SELL" # Close Longs
             
        # 🔴 SHORT LOGIC (Phase 43.2)
        if current_price < sma50 and strong_momentum and rsi > 30:
            return "SHORT"
        if current_price > sma20:
            return "COVER" # Close Shorts
            
        return "HOLD"
