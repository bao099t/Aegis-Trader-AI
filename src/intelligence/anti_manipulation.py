import pandas as pd
import numpy as np

class AntiManipulationFilter:
    """
    Detects market manipulation patterns (Pump & Dump, Wash Trading) 
    to protect the bot from entering artificial parabolic moves.
    """
    def __init__(self, volume_threshold=5.0, price_spike_threshold=0.10):
        self.volume_threshold = volume_threshold # Multiplier of 20-day avg volume
        self.price_spike_threshold = price_spike_threshold # 10% move in very short time

    def analyze(self, ticker, df):
        """
        Analyzes recent candles for manipulation signatures.
        Returns (is_manipulated, score, reason).
        """
        if len(df) < 20:
            return False, 0.0, "Insufficient data"

        recent = df.tail(5)
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        last_vol = recent['Volume'].iloc[-1]
        
        # 1. Volume Spike Detection
        volume_anomaly = last_vol / avg_vol if avg_vol > 0 else 1.0
        
        # 2. Parabolic Price Spike (Decoupling)
        price_change = recent['Close'].iloc[-1] / recent['Close'].iloc[0] - 1
        
        # 3. Decision Logic
        is_manipulated = False
        reasons = []
        
        if volume_anomaly > self.volume_threshold:
            is_manipulated = True
            reasons.append(f"Abnormal Volume Spike ({volume_anomaly:.1f}x avg)")
            
        if price_change > self.price_spike_threshold and volume_anomaly > 3.0:
            is_manipulated = True
            reasons.append(f"Parabolic Decoupling detected (+{price_change*100:.1f}%)")
            
        if is_manipulated:
            print(f"  [AntiManipulation] ⚠️ WARNING: {ticker} flagged for manipulation: {', '.join(reasons)}")
            
        return is_manipulated, volume_anomaly, "; ".join(reasons)

if __name__ == "__main__":
    print("Anti-Manipulation Filter Loaded.")
