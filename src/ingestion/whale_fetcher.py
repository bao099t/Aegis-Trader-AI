import random
import datetime

class WhaleFetcher:
    """
    Simulates fetching high-value on-chain transaction data (Whale Alerts).
    In a real scenario, this would connect to Whale-Alert.io API or indexed blockchain data.
    """
    def __init__(self):
        self.threshold = 5000000 # $5M threshold

    def fetch_recent_moves(self, ticker):
        """
        Returns a mock list of recent whale transactions for a ticker.
        """
        if "-USD" not in ticker: 
            return [] # Non-crypto assets usually don't have public on-chain data

        moves = []
        # Simulate 1-3 random large moves
        for _ in range(random.randint(0, 3)):
            amount = random.uniform(5000000, 50000000)
            direction = random.choice(["EXCHANGE_TO_WALLET", "WALLET_TO_EXCHANGE", "WALLET_TO_WALLET"])
            
            moves.append({
                'ticker': ticker,
                'amount_usd': amount,
                'direction': direction,
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        return moves

    def get_whale_sentiment(self, ticker):
        """
        Synthesizes whale data into a sentiment score (-1 to 1).
        - WALLET_TO_EXCHANGE: Bearish (Potential Sell)
        - EXCHANGE_TO_WALLET: Bullish (Accumulation)
        """
        moves = self.fetch_recent_moves(ticker)
        if not moves: return 0.0
        
        score = 0
        for m in moves:
            if m['direction'] == "EXCHANGE_TO_WALLET":
                score += 0.5
            elif m['direction'] == "WALLET_TO_EXCHANGE":
                score -= 0.5
                
        return max(-1.0, min(1.0, score))

if __name__ == "__main__":
    fetcher = WhaleFetcher()
    print(f"Whale Sentiment for BTC-USD: {fetcher.get_whale_sentiment('BTC-USD')}")
