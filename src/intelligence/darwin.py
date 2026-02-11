import pandas as pd
import numpy as np
import json
import os
import itertools

class Darwin:
    """
    The Evolutionary Engine (Phase 6).
    
    Responsibility:
    - Periodically (e.g., weekly) backtest strategies on recent data (e.g., last 60 days).
    - Find the 'Fittest' parameters for the CURRENT market regime.
    - Example: In a strong bull run, RSI 80 might be better than RSI 70.
    """
    
    def __init__(self, cache_dir="data/dna"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def evolve(self, ticker, df, strategy_class):
        """
        Runs a grid search / genetic evolution to find best params.
        For TrendHunter, we optimize:
        - SMA_FAST (default 50)
        - RSI_THRESHOLD (default 70)
        """
        if df is None or len(df) < 100:
            return None
            
        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.droplevel(1)
            except:
                pass
                
        print(f"  🧬 [Darwin] Evolving DNA for {ticker}...")
        
        # Define Gene Pool
        param_grid = {
            'sma_fast': [20, 50, 100],
            'rsi_threshold': [65, 70, 75, 80]
        }
        
        best_score = -999
        best_dna = None
        
        # Grid Search (Simple Evolution)
        keys = list(param_grid.keys())
        combinations = list(itertools.product(*param_grid.values()))
        
        for combo in combinations:
            params = dict(zip(keys, combo))
            
            # Fast Backtest Simulation
            score = self.simulate(df, params)
            
            if score > best_score:
                best_score = score
                best_dna = params
                
        print(f"    -> Best DNA Found: {best_dna} (Score: {best_score:.2f})")
        
        # Save DNA
        self.save_dna(ticker, best_dna)
        return best_dna

    def simulate(self, df, params):
        """
        Simplified Vectorized Backtest for TrendHunter Logic.
        """
        # Logic: Buy if Price > SMA_FAST and RSI < RSI_THRESHOLD
        # Sell if Price < SMA_FAST
        
        close = df['Close']
        sma = close.rolling(window=params['sma_fast']).mean()
        
        # RSI calc (approximate for speed)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Signals
        # 1 = Long, 0 = Flat
        # We use a simple regime filter: Price > SMA
        regime = (close > sma).astype(int)
        
        # Entry filter: RSI not overbought
        # If Price > SMA and RSI < Threshold -> Hold Long
        # Actually logic is: Enter if Price > SMA & RSI < Thresh. Exit if Price < SMA.
        # Vectorized: 
        # Position = 1 if Price > SMA. (Simplification of Trend Following)
        # But we filter entries where RSI > Threshold (Don't buy top).
        
        # Let's approximate Return:
        # If Price > SMA: Capture Daily Return.
        # But if we entered when RSI > Threshold, we wouldn't have entered. 
        # This is hard to vectorize perfectly without loop.
        
        # Simple Proxy Metric: "Trend Strength"
        # Sum of returns where Price > SMA and RSI < Threshold (Ideal Buy Zones)
        # Minus returns where Price < SMA (Drawdown zones)
        
        daily_ret = close.pct_change()
        
        # Ideal Trend Capture
        signal = (close > sma) & (rsi < params['rsi_threshold'])
        strategy_ret = daily_ret * signal.shift(1) # Lag 1 day
        
        total_return = strategy_ret.sum()
        
        # Penalize volatility/drawdown
        # Sharpesque: Return / StdDev
        std = strategy_ret.std()
        if std == 0: return 0
        
        score = total_return / std
        return score

    def save_dna(self, ticker, dna):
        path = os.path.join(self.cache_dir, f"{ticker}.json")
        with open(path, "w") as f:
            json.dump(dna, f)
            
    def load_dna(self, ticker):
        path = os.path.join(self.cache_dir, f"{ticker}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {} # Return empty to use defaults

if __name__ == "__main__":
    # Test
    d = Darwin()
    # Mock DF
    import yfinance as yf
    df = yf.download("NVDA", period="1y", interval="1d", progress=False)
    if 'Close' in df:
        d.evolve("NVDA", df, None)
