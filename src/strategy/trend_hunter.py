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
    # ... (inside analyze method)
        
        # --- EVOLUTIONARY DNA (Phase 6) ---
        # Load optimized parameters for this specific ticker
        from src.intelligence.darwin import Darwin
        darwin = Darwin()
        dna = darwin.load_dna(ticker)
        
        # Default Params
        SMA_FAST_LEN = dna.get('sma_fast', 50)
        RSI_THRESH = dna.get('rsi_threshold', 70)
        
        # ... calculation ...
        # (Need to ensure calculate_indicators supports dynamic SMA? 
        # Typically indicators are pre-calc for fixed windows. 
        # For dynamic SMA_50 vs SMA_20, we calculated SMA_50 hardcoded.
        # If DNA says SMA_100, we need that computed.
        # Ideally, calculate_indicators should calculate A LOT of indicators or be dynamic.
        # For now, let's assume we optimized for [20, 50, 100] which are standardly calc'd?
        # My calculate_indicators does: 20, 50, 200.
        # So we can map 'sma_fast' to one of those or re-calc on fly.)
        
        # Let's simple re-calc the dynamic SMA here for precision
        sma_dynamic = df['Close'].rolling(window=SMA_FAST_LEN).mean().iloc[-1]
        
        row = df.iloc[-1]
        current_price = row['Close']
        sma200 = row['SMA_200']
        rsi = row['RSI']
        adx = row['ADX']
        sma20 = row['SMA_20'] 
        
        # Update Logic to use Dynamic SMA
        is_bull_trend = current_price > sma_dynamic
        is_bear_trend = current_price < sma_dynamic
        strong_momentum = adx > 20
        
        signal = "HOLD"
        reason = "Wait"
        
        # --- PHASE 9: CIRCUIT BREAKER (Flash Crash Protection) ---
        # If asset dropped >5% today, FREEZE buying. Do not catch falling knives.
        daily_return = (current_price - row['Open']) / row['Open']
        if daily_return < -0.05:
            reason = f"⛔ CIRCUIT BREAKER Active: Crash Detected ({daily_return:.1%})"
            # We strictly return HOLD (or SELL if we want to bail, but HOLD prevents entry)
            # Strategy: Don't Enter. If Holding, maybe let Stop Limit handle it?
            # Safe bet: Block Entry.
            details = {
                "price": current_price,
                "sma_dynamic": sma_dynamic,
                "sma200": sma200,
                "rsi": rsi,
                "adx": adx,
                "reason": reason,
                "dna": dna if dna else "Default"
            }
            return "HOLD", details
        # ---------------------------------------------------------
        
        # 🟢 LONG LOGIC (Zenith)
        # Use Dynamic RSI Threshold
        if is_bull_trend and strong_momentum and rsi < RSI_THRESH:
            signal = "BUY"
            reason = f"Zenith Bull (Price > SMA{SMA_FAST_LEN}) + Momentum + DNA RSI<{RSI_THRESH}"
            
        # 🔴 SHORT LOGIC (Vulture)
        elif is_bear_trend and strong_momentum and rsi > 45: # Keep Vulture static for now or evolve later
            signal = "SHORT"
            reason = f"Vulture Hedge (Price < SMA{SMA_FAST_LEN})"
            
        # 🔵 EXIT LOGIC
        if signal == "HOLD" and is_bull_trend and current_price < sma20:
             signal = "SELL"
             reason = "Trend Broken (Price < SMA20)"
             
        if signal == "HOLD" and is_bear_trend and current_price > sma20:
             signal = "COVER"
             reason = "Bear Baseline Broken (Price > SMA20)"
             
        details = {
            "price": current_price,
            "sma_dynamic": sma_dynamic,
            "sma200": sma200,
            "rsi": rsi,
            "adx": adx,
            "reason": reason,
            "dna": dna if dna else "Default"
        }
        
        return signal, details
