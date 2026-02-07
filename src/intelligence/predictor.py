import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

class PricePredictor:
    """
    AI Module that predicts next-day price direction using Random Forest.
    Features: RSI, ADX, SMA_Diff, Volume_Change, Pct_Change.
    Target: 1 if Next_Close > Current_Close else 0.
    """
    
    def __init__(self, model_path="data/models/price_predictor.pkl"):
        self.model_path = model_path
        self.model = None
        self.tickers = ['BTC-USD', 'ETH-USD', 'NVDA', 'TSLA', 'AAPL', 'GC=F']
        
        # Create dir if not exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Load existing model if available
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"  [AI] Loaded existing model from {self.model_path}")
            except:
                print("  [AI] Model file corrupt or incompatible. Will retrain.")

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
        """Trains the Random Forest model on all tracked tickers."""
        print("  [AI] Starting training protocol...")
        
        all_data = []
        
        for ticker in self.tickers:
            print(f"    - Fetching training data for {ticker}...")
            df = self.fetch_data(ticker)
            df = self.prepare_features(df)
            
            if df is not None:
                # Add Ticker ID via One-Hot or just ignore (general model)
                # For simplicity, we train a General Market Model
                all_data.append(df)
        
        if not all_data:
            print("  [AI] No data collected. Training aborted.")
            return
            
        full_df = pd.concat(all_data)
        
        # Select Features
        features = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
        X = full_df[features]
        y = full_df['Target']
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
        
        # Train
        self.model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        
        print(f"  [AI] Training Complete. Accuracy: {acc:.2%}")
        # print(classification_report(y_test, preds))
        
        # Save
        joblib.dump(self.model, self.model_path)
        print(f"  [AI] Model saved to {self.model_path}")

    def predict(self, ticker):
        """Predicts tomorrow's movement for a specific ticker."""
        if self.model is None:
            # Try load if not loaded
            if os.path.exists(self.model_path):
                 try:
                     self.model = joblib.load(self.model_path)
                 except:
                     print(f"  [AI Debug] Failed to load model for {ticker}")
                     return "ERROR", 0.0
            else:
                 print(f"  [AI Debug] Model path not found for {ticker}")
                 return "ERROR", 0.0
                 
        # print(f"  [AI Debug] Fetching data for {ticker}...")
        df = self.fetch_data(ticker, days=400) # Need enough for SMA200
        
        if df is None:
             print(f"  [AI Debug] Data fetch returned None for {ticker}")
             return "ERROR", 0.0
             
        # print(f"  [AI Debug] Preparing features for {ticker} (Rows: {len(df)})...")
        df = self.prepare_features(df)
        
        if df is None or df.empty:
            print(f"  [AI Debug] Features prep returned empty for {ticker}")
            return "ERROR", 0.0
            
        # Get last row features
        features = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
        try:
            # Check if features exist
            missing = [f for f in features if f not in df.columns]
            if missing:
                print(f"  [AI Debug] Missing columns: {missing}")
                return "ERROR", 0.0
                
            last_row = df.iloc[[-1]][features]
            # print(f"  [AI Debug] Last row features: {last_row.values}")
            
            prediction = self.model.predict(last_row)[0]
            prob = self.model.predict_proba(last_row)[0]
            
            # prob[1] is probability of class 1 (UP)
            confidence = prob[1]
            
            direction = "UP" if prediction == 1 else "DOWN"
            
            return direction, confidence
        except Exception as e:
            print(f"Prediction error for {ticker}: {e}")
            return "ERROR", 0.0

if __name__ == "__main__":
    # Test Run
    predictor = PricePredictor()
    predictor.train_model()
    
    print("\n--- Predictions ---")
    for t in ['BTC-USD', 'NVDA', 'ETH-USD', 'GC=F']:
        d, c = predictor.predict(t)
        print(f"{t}: {d} (Confidence: {c:.2%})")
