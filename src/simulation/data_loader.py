import yfinance as yf
import pandas as pd
import os
import datetime

class DataLoader:
    def __init__(self, cache_dir="data/simulation_cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
    def fetch_data(self, ticker, start_date, end_date, interval="1d"):
        """
        Fetches historical data for a given ticker.
        Checks cache first.
        """
        # ISO format to safe filename
        safe_start = start_date.split(" ")[0]
        safe_end = end_date.split(" ")[0]
        cache_file = os.path.join(self.cache_dir, f"{ticker}_{safe_start}_{safe_end}_{interval}.csv")
        
        if os.path.exists(cache_file):
            print(f"  [Loader] Loading {ticker} from cache...")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            df.index = pd.to_datetime(df.index)
            return df
            
        print(f"  [Loader] Downloading {ticker} ({start_date} to {end_date})...")
        try:
            df = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=True)
            
            if df.empty:
                print(f"  [Loader] ⚠️ No data found for {ticker}")
                return None
            
            # Flatten MultiIndex columns if present
            # yfinance often returns (Price, Ticker) or (Ticker, Price)
            if isinstance(df.columns, pd.MultiIndex):
                # Check if Ticker is in levels
                # Usually level 1 is ticker if we downloaded one ticker?
                # Or sometimes just droplevel(1) works.
                try:
                    df.columns = df.columns.droplevel(1) 
                except:
                    pass
            
            # Save to cache
            df.to_csv(cache_file)
            # Ensure index is datetime for immediate use
            df.index = pd.to_datetime(df.index)
            return df
            
        except Exception as e:
            print(f"  [Loader] Error downloading {ticker}: {e}")
            return None

if __name__ == "__main__":
    # Test
    loader = DataLoader()
    df = loader.fetch_data("GC=F", "2023-01-01", "2023-12-31")
    print(df.head())
