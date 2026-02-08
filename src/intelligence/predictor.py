import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import sys
import os

# Add project root to sys.path for standalone imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.intelligence.neural_predictor import NeuralPredictor

class PricePredictor:
    """
    AI Module that predicts next-day price direction.
    Supports Dual-Engine: 
    - Random Forest (Legacy Ensemble)
    - Transformer (Neural Intelligence)
    """
    
    def __init__(self, mode="neural", model_path="data/models/price_predictor.pkl"):
        self.mode = mode # "neural" or "rf"
        self.model_path = model_path
        self.model = None
        self.neural_engine = NeuralPredictor()
        self.tickers = ['BTC-USD', 'ETH-USD', 'NVDA', 'TSLA', 'AAPL', 'GC=F']
        
        # Create dir if not exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Load legacy model if in RF mode
        if self.mode == "rf" and os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"  [AI] Loaded Legacy RF model from {self.model_path}")
            except:
                print("  [AI] RF model file corrupt. Will need retrain.")

    def fetch_data(self, ticker, days=2000):
        """Fetches historical data for training."""
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten
                try:
                    df.columns = df.columns.droplevel(1)
                except:
                    pass
            return df
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def prepare_features(self, df):
        """Generates technical indicators as features for the AI."""
        if df is None or len(df) < 50: return None
        df = df.copy()
        
        # Ensure numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. Price Changes
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # 2. SMAs
        df['SMA_10'] = df['Close'].rolling(window=10).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        df['Dist_SMA10'] = (df['Close'] - df['SMA_10']) / df['SMA_10']
        df['Dist_SMA50'] = (df['Close'] - df['SMA_50']) / df['SMA_50']
        df['Dist_SMA200'] = (df['Close'] - df['SMA_200']) / df['SMA_200']
        
        # 3. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 4. Volatility
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        
        # 5. Target: Next Day Direction (1 = Up, 0 = Down)
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        
        # Clean NaNs
        df.dropna(inplace=True)
        return df

    def train_model(self):
        """Trains either RF or Neural model depending on mode."""
        print(f"  [AI] Starting training protocol in {self.mode.upper()} mode...")
        
        all_data = []
        for ticker in self.tickers:
            df = self.fetch_data(ticker)
            df = self.prepare_features(df)
            if df is not None:
                all_data.append(df)
        
        if not all_data:
            print("  [AI] No data. Training aborted.")
            return

        if self.mode == "neural":
            self.neural_engine.train(all_data)
        else:
            # Legacy RF training
            full_df = pd.concat(all_data)
            features = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
            X = full_df[features]
            y = full_df['Target']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
            self.model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=42)
            self.model.fit(X_train, y_train)
            joblib.dump(self.model, self.model_path)
            print("  [AI] Legacy RF training complete.")

    def predict(self, ticker):
        """Predicts tomorrow's movement for a specific ticker (Fetches data)."""
        df = self.fetch_data(ticker, days=400)
        df_feats = self.prepare_features(df)
        return self.predict_from_df(df_feats)

    def predict_from_df(self, df_raw):
        """Predicts tomorrow's movement using a raw DataFrame slice."""
        df_feats = self.prepare_features(df_raw)
        
        if df_feats is None or df_feats.empty:
            return "ERROR", 0.0

        if self.mode == "hybrid":
            return self.predict_hybrid(df_feats)
        elif self.mode == "neural":
            return self.neural_engine.predict(df_feats)
        else:
            # Legacy RF prediction logic
            if self.model is None: return "ERROR", 0.0
            features = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
            last_row = df_feats.iloc[[-1]][features]
            prediction = self.model.predict(last_row)[0]
            prob = self.model.predict_proba(last_row)[0]
            return ("UP" if prediction == 1 else "DOWN"), prob[1]

    def predict_hybrid(self, df_feats):
        """Synthesizes signals from both RF and Neural engines (WIS Protocol)."""
        # 1. Neural Signal
        neural_dir, neural_prob = self.neural_engine.predict(df_feats)
        
        # 2. RF Signal
        if self.model is None:
             # Try load 
             if os.path.exists(self.model_path): self.model = joblib.load(self.model_path)
        
        if self.model is None: return neural_dir, neural_prob
        
        features = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
        last_row = df_feats.iloc[[-1]][features]
        rf_prediction = self.model.predict(last_row)[0]
        rf_prob = self.model.predict_proba(last_row)[0][1]
        rf_dir = "UP" if rf_prediction == 1 else "DOWN"
        
        return {
            'rf_dir': rf_dir,
            'rf_prob': rf_prob,
            'neural_dir': neural_dir,
            'neural_prob': neural_prob
        }, 1.0 # Return dict in signal slot

if __name__ == "__main__":
    # Test Run
    predictor = PricePredictor()
    predictor.train_model()
    
    print("\n--- Predictions ---")
    for t in ['BTC-USD', 'NVDA', 'ETH-USD', 'GC=F']:
        d, c = predictor.predict(t)
        print(f"{t}: {d} (Confidence: {c:.2%})")
