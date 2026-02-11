import yfinance as yf
import pandas as pd

def test_holdings():
    print("Testing yfinance ETF holdings...")
    etf = yf.Ticker("XLK")
    try:
        # Method 1: funds_data (New API)
        print("Attempt 1: funds_data.top_holdings")
        if hasattr(etf, 'funds_data') and etf.funds_data:
             print(etf.funds_data.top_holdings)
        else:
             print("funds_data not available.")

        # Method 2: holdings (Old API)
        print("Attempt 2: .holdings")
        # print(etf.holdings) # This property is often deprecated/broken

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_holdings()
