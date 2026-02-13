import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import os
import joblib
from sklearn.preprocessing import StandardScaler

class TimeSeriesTransformer(nn.Module):
    def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.1):
        super(TimeSeriesTransformer, self).__init__()
        self.d_model = d_model
        
        # Linear embedding
        self.encoder_input = nn.Linear(input_dim, d_model)
        
        # Positional Encoding (Simple learned version for time-series)
        self.pos_embedding = nn.Parameter(torch.zeros(1, 100, d_model)) # Max seq len 100
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=d_model*4, 
            dropout=0.3, # Phase 59: Increased Dropout for Regularization (Was 0.1)
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output layers
        self.fc = nn.Linear(d_model, 1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        batch_size, seq_len, _ = x.size()
        
        # Embedding
        x = self.encoder_input(x) # (batch_size, seq_len, d_model)
        
        # Add Positional Encoding
        x = x + self.pos_embedding[:, :seq_len, :]
        
        # Transformer Encoder
        x = self.transformer_encoder(x) # (batch_size, seq_len, d_model)
        
        # Take the output of the last time step
        x = x[:, -1, :] # (batch_size, d_model)
        
        # Result
        x = self.fc(x)
        return self.sigmoid(x)

class NeuralPredictor:
    def __init__(self, model_path="data/models/neural_predictor.pt", scaler_path="data/models/scaler.pkl"):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.scaler = None
        self.lookback = 20
        self.input_dim = 6 # RSI, Dist_SMA10, Dist_SMA50, Dist_SMA200, Volatility, Returns
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        if os.path.exists(self.model_path):
            try:
                self.model = TimeSeriesTransformer(self.input_dim).to(self.device)
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.model.eval()
                if os.path.exists(self.scaler_path):
                    self.scaler = joblib.load(self.scaler_path)
                print(f"  [Neural] Loaded Transformer Model from {self.model_path}")
            except Exception as e:
                print(f"  [Neural] Load error: {e}. Need training.")
                self.model = None

    def create_sequences(self, data, target, lookback):
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i : i + lookback])
            y.append(target[i + lookback])
        return np.array(X), np.array(y)

    def train(self, df_list, epochs=50, batch_size=32, validation_split=0.2):
        print("  [Neural] Preparing datasets for training...")
        self.scaler = StandardScaler()
        
        all_features = []
        all_targets = []
        
        features_cols = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
        
        # Fit scaler on all data first
        combined_raw = pd.concat(df_list)
        self.scaler.fit(combined_raw[features_cols])
        joblib.dump(self.scaler, self.scaler_path)
        
        for df in df_list:
            scaled_data = self.scaler.transform(df[features_cols])
            
            # Phase 59: Data Augmentation (Noise Injection)
            noise_factor = 0.01
            noise = np.random.normal(0, noise_factor, scaled_data.shape)
            scaled_data = scaled_data + noise
            
            targets = df['Target'].values
            X_seq, y_seq = self.create_sequences(scaled_data, targets, self.lookback)
            if len(X_seq) > 0:
                all_features.append(X_seq)
                all_targets.append(y_seq)
        
        X = np.concatenate(all_features)
        y = np.concatenate(all_targets)
        
        # --- TRAIN / VALIDATION SPLIT (Fix Overfitting) ---
        # We split by time (not random shuffle) to respect time series nature
        split_idx = int(len(X) * (1 - validation_split))
        
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Convert to Tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        
        X_val_tensor = torch.FloatTensor(X_val).to(self.device)
        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)
        
        # Initialize Model
        self.model = TimeSeriesTransformer(self.input_dim).to(self.device)
        # Phase 59: Weight Decay for Regularization
        optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.BCELoss()
        
        print(f"  [Neural] Training on {len(X_train)} sequences | Validating on {len(X_val)} sequences")
        
        best_val_loss = float('inf')
        patience = 5
        no_improve_epoch = 0
        
        self.model.train()
        for epoch in range(epochs):
            # Training Loop
            permutation = torch.randperm(X_train_tensor.size()[0])
            train_loss = 0
            
            for i in range(0, X_train_tensor.size()[0], batch_size):
                indices = permutation[i : i + batch_size]
                batch_x, batch_y = X_train_tensor[indices], y_train_tensor[indices]
                
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            avg_train_loss = train_loss / (len(X_train_tensor) / batch_size)
            
            # Validation Loop
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor)
                val_loss = criterion(val_outputs, y_val_tensor).item()
            self.model.train()
            
            # Logging & Early Stopping
            if (epoch + 1) % 5 == 0:
                print(f"    Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f}")
            
            # Save Checkpoint if improved
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(self.model.state_dict(), self.model_path)
                no_improve_epoch = 0
            else:
                no_improve_epoch += 1
                
            if no_improve_epoch >= patience:
                print(f"    [Early Stopping] No improvement for {patience} epochs. Best Val Loss: {best_val_loss:.4f}")
                break
                
        # Reload best model
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        print(f"  [Neural] Best Model saved to {self.model_path}")

    def predict(self, df):
        if self.model is None or self.scaler is None:
            return "ERROR", 0.0
        
        self.model.eval()
        features_cols = ['RSI', 'Dist_SMA10', 'Dist_SMA50', 'Dist_SMA200', 'Volatility', 'Returns']
        
        # Need enough history
        if len(df) < self.lookback:
            return "ERROR", 0.0
            
        # Transform and predict
        scaled_data = self.scaler.transform(df[features_cols])
        last_seq = scaled_data[-self.lookback:]
        last_seq_tensor = torch.FloatTensor(last_seq).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            prob = self.model(last_seq_tensor).item()
            
        # Tuned for Hybrid: More sensitive detection
        direction = "UP" if prob > 0.51 else ("DOWN" if prob < 0.49 else "NEUTRAL")
        return direction, prob

if __name__ == "__main__":
    print("Neural Predictor Logic Ready.")
