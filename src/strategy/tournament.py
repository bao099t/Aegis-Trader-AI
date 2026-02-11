import json
import os

class StrategyTournament:
    """
    The Arena (Phase 7).
    Responsibility: Dynamic Capital Allocation.
    
    If 'TrendHunter' is losing money (e.g., market is chopping),
    and 'MeanReversion' is making money,
    -> Shift capital from TrendHunter to MeanReversion.
    """
    
    def __init__(self, storage_path="data/tournament_scores.json"):
        self.storage_path = storage_path
        self.scores = self.load_scores()
        
    def load_scores(self):
        if os.path.exists(self.storage_path):
            try:
                return json.load(open(self.storage_path))
            except:
                pass
        return {
            "TrendHunter": {"pnl": 0.0, "allocation": 0.5},
            "MeanReversion": {"pnl": 0.0, "allocation": 0.5}
        }
        
    def save_scores(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self.scores, f, indent=4)
            
    def update_pnl(self, strategy_name, pnl_amount):
        if strategy_name not in self.scores:
            self.scores[strategy_name] = {"pnl": 0.0, "allocation": 0.0}
            
        self.scores[strategy_name]['pnl'] += pnl_amount
        self.rebalance()
        self.save_scores()
        
    def rebalance(self):
        """
        Calculates new allocation based on PnL.
        Simple logic: Allocation pro-rated by positive PnL? 
        Or sigmoid of PnL?
        Let's use a simple winner-take-more approach.
        """
        keys = list(self.scores.keys())
        # Base score = 1.0. Add normalized PnL.
        
        # Calculate raw scores
        raw_scores = {}
        min_score = 0
        for k, v in self.scores.items():
            # Dampened PnL impact
            s = 1000.0 + v['pnl'] # Start with 1000 virtual credits
            if s < 100: s = 100 # Floor
            raw_scores[k] = s
            
        total_score = sum(raw_scores.values())
        if total_score == 0: total_score = 1
        
        for k in keys:
            self.scores[k]['allocation'] = raw_scores[k] / total_score
            
    def get_allocation(self, strategy_name):
        return self.scores.get(strategy_name, {}).get('allocation', 0.0)

if __name__ == "__main__":
    t = StrategyTournament()
    t.update_pnl("TrendHunter", -50)
    t.update_pnl("MeanReversion", 100)
    print(t.scores)
