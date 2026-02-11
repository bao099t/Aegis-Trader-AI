import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.intelligence.darwin import Darwin
import yfinance as yf
import os

def test_evolution():
    print("Testing Darwinian Evolution...")
    d = Darwin()
    
    ticker = "NVDA"
    print(f"Fetching data for {ticker}...")
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    
    if len(df) > 0:
        dna = d.evolve(ticker, df, None)
        print(f"Evolved DNA: {dna}")
        
        # Check if file saved
        if os.path.exists(f"data/dna/{ticker}.json"):
             print("✅ DNA Saved Successfully.")
        else:
             print("❌ DNA Save Failed.")
    else:
        print("❌ Data fetch failed.")

if __name__ == "__main__":
    test_evolution()
