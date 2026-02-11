import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.intelligence.neural_predictor import NeuralPredictor
import yfinance as yf
import pandas as pd
import datetime

def test_plasticity():
    print("Testing Neural Plasticity (Auto-Train)...")
    predictor = NeuralPredictor()
    
    ticker = "NVDA"
    print(f"Fetching training data for {ticker}...")
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    
    # Flatten if needed
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel(1)
        except:
            pass

    if len(df) > 0:
        # Prepare Target
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        df.dropna(inplace=True)
        
        print("Starting Training...")
        try:
            predictor.train([df], epochs=5) # Short run
            print("✅ Training Completed Successfully.")
        except Exception as e:
            print(f"❌ Training Failed: {e}")
            
    else:
        print("❌ Data fetch failed.")

if __name__ == "__main__":
    test_plasticity()
