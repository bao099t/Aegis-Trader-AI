import pandas as pd
import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.asset_selector import AssetSelector
from src.simulation.data_loader import DataLoader

def test_selector():
    print("--- ASSET SELECTOR SANITY CHECK ---")
    BROAD_UNIVERSE = ['BTC-USD', 'ETH-USD', 'NVDA', 'TSLA', 'AAPL', 'GC=F']
    loader = DataLoader()
    selector = AssetSelector(broad_universe=BROAD_UNIVERSE)
    
    data_map = {}
    test_date = "2024-01-01"
    
    print(f"Loading data for check up to {test_date}...")
    for t in BROAD_UNIVERSE:
        df = loader.fetch_data(t, "2023-01-01", test_date)
        if df is not None:
            data_map[t] = df
            
    top_assets = selector.get_top_alpha(data_map, pd.to_datetime(test_date), top_n=3)
    print(f"\nTop 3 Assets on {test_date}: {top_assets}")
    
    if len(top_assets) > 0:
        print("\nSUCCESS: Selector returned valid rankings.")
    else:
        print("\nFAILURE: Selector returned empty list.")

if __name__ == "__main__":
    test_selector()
