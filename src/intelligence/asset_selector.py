import pandas as pd
import numpy as np

class AssetSelector:
    """
    AEGIS DYNAMIC ALPHA DISCOVERY (Phase 9)
    Scans a broad universe and identifies high-alpha "Super Assets" for the Turbo Protocol.
    """
    def __init__(self, broad_universe=None):
        self.broad_universe = broad_universe or [
            'BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'LINK-USD',
            'NVDA', 'TSLA', 'AMZN', 'AAPL', 'MSFT', 'AMD', 'MSTR', 'GOOGL', 'META',
            'GC=F', 'CL=F'
        ]

    def rank_assets(self, all_data, current_date, lookback=30):
        """
        Ranks assets based on Alpha potential:
        1. Momentum (ADX/RSI)
        2. Volatility (High Beta potential)
        3. Trend Consistency (Price vs SMA)
        """
        rankings = []
        
        for ticker in self.broad_universe:
            if ticker not in all_data: continue
            
            df = all_data[ticker]
            # Ensure we have data up to current_date
            historical = df.loc[:current_date].tail(lookback)
            if len(historical) < lookback: continue
            
            # 1. Momentum Component (Dominant Factor for Hyper-Growth)
            last_row = historical.iloc[-1]
            adx = last_row.get('ADX', 0)
            rsi = last_row.get('RSI', 50)
            
            # Momentum Score: Heavy weight on strong trends (ADX > 25)
            momentum_score = (adx / 50) if adx > 25 else (adx / 100)
            
            # 2. Volatility Component (Alpha comes from volatility)
            returns = historical['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) 
            
            # Ultra-Growth Bias: Favor assets with high ATR/Price ratio (Beta)
            price = last_row['Close']
            atr_ratio = last_row.get('ATR', 0) / price if price > 0 else 0
            
            # 3. Trend Alignment
            sma50 = last_row.get('SMA_50', 0)
            sma200 = last_row.get('SMA_200', 0)
            trend_score = 1.0 if (price > sma50 and price > sma200) else 0.0
            
            # Final Alpha Score (Concentrated Hyper-Growth)
            # Weighting: 50% Momentum, 30% Volatility/Beta, 20% Trend
            alpha_score = (momentum_score * 0.5) + (atr_ratio * 30 * 0.3) + (trend_score * 0.2)
            
            rankings.append({
                'ticker': ticker,
                'alpha_score': alpha_score,
                'volatility': volatility,
                'adx': adx
            })
            
        # Sort by alpha_score descending
        rankings.sort(key=lambda x: x['alpha_score'], reverse=True)
        return rankings

    def get_top_alpha(self, all_data, current_date, top_n=5):
        """Returns the list of tickers for the top N super assets."""
        ranks = self.rank_assets(all_data, current_date)
        return [r['ticker'] for r in ranks[:top_n]]

if __name__ == "__main__":
    # Mock test
    selector = AssetSelector()
    print("Asset Selector initialized for universe:", selector.broad_universe)
