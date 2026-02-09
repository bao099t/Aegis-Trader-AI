import numpy as np

class RLOptimizer:
    """
    Simulates a Reinforcement Learning (RL) agent that optimizes 
    the weights of the AssetSelector based on historical PnL feedback.
    """
    def __init__(self, initial_weights=None):
        # Default weights: 50% Momentum, 30% Volatility, 20% Trend
        self.weights = initial_weights or np.array([0.5, 0.3, 0.2])
        self.learning_rate = 0.05

    def optimize(self, trades_history):
        """
        Adjusts weights based on the 'reward' (profit) of recent trades.
        """
        if not trades_history:
            return self.weights

        recent_trades = trades_history[-10:]
        total_pnl = sum([t.get('profit', 0) for t in recent_trades])
        
        # Reward function: PnL normalized
        reward = 1.0 if total_pnl > 0 else -1.0
        
        # In a real RL system, we would calculate the gradient of the weights 
        # relative to the factors that led to these trades.
        # Here we simulate an 'Explore-Exploit' shift:
        
        # If profit is high, reinforce the dominant weight
        if reward > 0:
            dominant_idx = np.argmax(self.weights)
            self.weights[dominant_idx] += self.learning_rate
        else:
            # If loss, rotate weights to 'Explore' other factors
            self.weights = np.roll(self.weights, 1)
            
        # Normalize weights to sum to 1.0
        self.weights = self.weights / np.sum(self.weights)
        
        print(f"  [RL-Optimizer] New DAD Weights: Momentum={self.weights[0]:.2f}, Vol={self.weights[1]:.2f}, Trend={self.weights[2]:.2f}")
        return self.weights

if __name__ == "__main__":
    optimizer = RLOptimizer()
    mock_trades = [{'profit': 100}, {'profit': 200}]
    optimizer.optimize(mock_trades)
