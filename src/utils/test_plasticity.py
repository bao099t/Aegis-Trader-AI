import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.intelligence.neural_predictor import NeuralPredictor
import yfinance as yf
import pandas as pd
import numpy as np

def calculate_features(df):
    df = df.copy()
    close = df['Close']
    
    # 1. Returns
    df['Returns'] = close.pct_change()
    
    # 2. Volatility (20-day rolling std of returns)
    df['Volatility'] = df['Returns'].rolling(window=20).std()
    
    # 3. SMAs
    df['SMA_10'] = close.rolling(window=10).mean()
    df['SMA_50'] = close.rolling(window=50).mean()
    df['SMA_200'] = close.rolling(window=200).mean()
    
    # 4. Distances to SMAs
    df['Dist_SMA10'] = (close - df['SMA_10']) / df['SMA_10']
    df['Dist_SMA50'] = (close - df['SMA_50']) / df['SMA_50']
    df['Dist_SMA200'] = (close - df['SMA_200']) / df['SMA_200']
    
    # 5. RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

def test_plasticity():
    print("Testing Neural Plasticity (Auto-Train)...")
    predictor = NeuralPredictor()
    
    ticker = "NVDA"
    print(f"Fetching training data for {ticker}...")
    df = yf.download(ticker, period="2y", interval="1d", progress=False) # Get 2y for enough history
    
    # Flatten if needed
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel(1)
        except:
            pass
            
    # Normalize columns (yfinance can be weird)
    # Ensure 'Close' exists
    if 'Close' not in df.columns and 'close' in df.columns:
        df.rename(columns={'close': 'Close'}, inplace=True)

    if len(df) > 0:
        print(f"  Downloaded {len(df)} rows. Calculating features...")
        
        # FEATURE ENGINEERING
        try:
            df = calculate_features(df)
        except Exception as e:
            print(f"Feature calculation error: {e}")
            return

        # Prepare Target
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        df.dropna(inplace=True)
        
        print(f"  Training Data Ready: {len(df)} rows. Columns: {df.columns.tolist()}")
        
        print("Starting Training (with Validation Split)...")
        try:
            # We use 10 epochs for quick test
            predictor.train([df], epochs=10, validation_split=0.2) 
            print("✅ Training Completed Successfully.")
        except Exception as e:
            print(f"❌ Training Failed: {e}")
            import traceback
            traceback.print_exc()
            
    else:
        print("❌ Data fetch failed.")

if __name__ == "__main__":
    test_plasticity()
