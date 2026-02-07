import os

class TargetingManager:
    def __init__(self, watchlist_path="watchlist.txt"):
        self.watchlist = set()
        self.watchlist_path = watchlist_path
        self.reload()

    def reload(self):
        """Reloads watchlist from file."""
        if not os.path.exists(self.watchlist_path):
            print(f"  [Targeting] Watchlist not found at {self.watchlist_path}. Creating empty.")
            open(self.watchlist_path, 'w').close()
            return

        with open(self.watchlist_path, 'r') as f:
            lines = f.readlines()
            self.watchlist = {line.strip().upper() for line in lines if line.strip()}
        print(f"  [Targeting] Loaded {len(self.watchlist)} tickers: {self.watchlist}")

    def check_priority(self, ticker):
        """
        Returns priority level:
        - 'CRITICAL': In Watchlist.
        - 'NORMAL': Not in Watchlist but Major Company (S&P 500 equivalent logic - implemented broadly).
        """
        if not ticker:
            return 'NORMAL'
            
        if ticker.upper() in self.watchlist:
            return 'CRITICAL'
            
        return 'NORMAL'
        
    def should_alert(self, ticker, impact_level, priority_level):
        """
        Decides if we should alert.
        
        Logic:
        1. If Priority is CRITICAL (Watchlist):
           -> Alert on EVERYTHING (even Low impact).
           
        2. If Priority is NORMAL (Non-Watchlist):
           -> Alert ONLY on HIGH impact (Bullish/Bearish Direction).
           -> Ignore "Neutral" or "Info" news.
        """
        if priority_level == 'CRITICAL':
            return True
        
        # Non-watchlist: Only alert if Impact is significant
        if impact_level in ['BULLISH', 'BEARISH', 'VOLATILE']:
            return True
            
        return False

if __name__ == "__main__":
    tm = TargetingManager()
    print(f"AAPL Priority: {tm.check_priority('AAPL')}")
    print(f"XYZ Priority: {tm.check_priority('XYZ')}")
