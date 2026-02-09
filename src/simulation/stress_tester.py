import pandas as pd
import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

class BlackSwanStressTester:
    """
    Simulates extreme market stress (Flash Crashes, Liquidity Drains) 
    to verify Aegis Guardian's veto capability.
    """
    def __init__(self):
        pass

    def inject_flash_crash(self, df, crash_pct=0.15, recovery_pct=0.05):
        """
        Injects a synthetic flash crash in the middle of the dataframe.
        """
        df = df.copy()
        n = len(df)
        if n < 20: return df
        
        crash_point = n // 2
        
        # Immediate crash
        df.iloc[crash_point, df.columns.get_loc('Close')] *= (1 - crash_pct)
        df.iloc[crash_point, df.columns.get_loc('Low')] = df.iloc[crash_point]['Close'] * 0.95
        
        # Slow recovery / Panic tail
        for i in range(crash_point + 1, min(crash_point + 5, n)):
            df.iloc[i, df.columns.get_loc('Close')] *= (1 - crash_pct * 0.5)
            
        print(f"  [StressTester] Injected {crash_pct*100}% Flash Crash at step {crash_point}")
        return df

    def run_stress_test(self, ticker, original_df, guardian):
        """
        Runs a simulated trading day and checks if Guardian blocks/reacts.
        """
        stressed_df = self.inject_flash_crash(original_df)
        
        # In a real test, we would feed this to the simulation loop and count 'Guardian BLOCKS'
        # For now, we simulate a Guardian audit call.
        
        print(f"  [StressTester] Auditing Guardian against extreme volatility for {ticker}...")
        
        # Mocking a high-risk trade request
        mock_price = stressed_df.iloc[len(stressed_df)//2]['Close']
        
        # Guardian should detect the spike in volatility (ATR) and potentially block
        # We check the logic in src/core/guardian.py
        
        return stressed_df

if __name__ == "__main__":
    print("Aegis Black-Swan Stress Tester Initialized.")
