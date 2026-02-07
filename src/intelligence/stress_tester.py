import yfinance as yf
import pandas as pd
import datetime
from src.intelligence.market_analyst import MarketAnalyst
from unittest.mock import MagicMock

class StressTester:
    def __init__(self):
        self.analyst = MarketAnalyst()
        self.scenarios = {
            "COVID_CRASH_2020": ("2020-02-15", "2020-04-15"),
            "BEAR_MARKET_2022": ("2022-01-01", "2022-06-01"),
            "TECH_RECOVERY_2023": ("2023-01-01", "2023-05-01")
        }

    def run_scenario(self, ticker, scenario_name):
        start, end = self.scenarios.get(scenario_name)
        print(f"\n--- Running Stress Test: {scenario_name} on {ticker} ---")
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start, end=end)
            if hist.empty:
                print("  [Stress] No data found for this period.")
                return
            
            # Mock news at the start of scenario
            entry_price = hist['Open'].iloc[0]
            print(f"  [Scenario Start] Entry Price: ${entry_price:.2f}")
            
            # Use Analyst to get Dynamic SL
            # We mock the ATR calculation for that specific period
            tr = (hist['High'] - hist['Low']).rolling(14).mean()
            period_atr = tr.dropna().iloc[0] if not tr.dropna().empty else 2.0
            
            # Manually trigger the ATR stop calculation logic for simulation
            sl_dist = 2 * period_atr
            sl_price = entry_price - sl_dist
            
            print(f"  [Strategy] Period ATR: ${period_atr:.2f} | Dynamic SL: ${sl_price:.2f}")
            
            # Check for Stop-out
            stopped_out = False
            for date, row in hist.iterrows():
                if row['Low'] <= sl_price:
                    print(f"  [🛑 STOP-OUT] Hit SL on {date.date()} at Low ${row['Low']:.2f}")
                    stopped_out = True
                    break
            
            if not stopped_out:
                final_price = hist['Close'].iloc[-1]
                pnl = ((final_price - entry_price) / entry_price) * 100
                print(f"  [✅ SURVIVED] Final Price: ${final_price:.2f} | Net PnL: {pnl:.2f}%")
                
        except Exception as e:
            print(f"  [Error] Stress test failed: {e}")

if __name__ == "__main__":
    tester = StressTester()
    tester.run_scenario("AAPL", "COVID_CRASH_2020")
    tester.run_scenario("NVDA", "BEAR_MARKET_2022")
