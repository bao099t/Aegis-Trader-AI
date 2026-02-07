from transformers import BertTokenizer, BertForSequenceClassification
from torch.nn.functional import softmax
import torch
import traceback

class FinanceAI:
    def __init__(self):
        print("  [AI] Loading FinBERT (yiyanghkust) model...")
        # Switching to yiyanghkust/finbert-tone (Known for stability)
        self.model_name = "yiyanghkust/finbert-tone"
        try:
            self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
            self.model = BertForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval()
            print("  [AI] FinBERT loaded successfully.")
        except Exception:
            print("  [AI] Error loading FinBERT:")
            traceback.print_exc()
            self.model = None

    def predict(self, text):
        if not self.model:
            return {"sentiment": "neutral", "score": 0.0}

        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            outputs = self.model(**inputs)
            probs = softmax(outputs.logits, dim=1)
            
            # yiyanghkust/finbert-tone mapping: 0: Neutral, 1: Positive, 2: Negative
            score_neu = probs[0][0].item()
            score_pos = probs[0][1].item()
            score_neg = probs[0][2].item()
            
            if score_pos > score_neg and score_pos > score_neu:
                return {"sentiment": "positive", "score": score_pos}
            elif score_neg > score_pos and score_neg > score_neu:
                return {"sentiment": "negative", "score": score_neg}
            else:
                return {"sentiment": "neutral", "score": score_neu}
                
        except Exception as e:
            print(f"  [AI] Prediction Error: {e}")
            return {"sentiment": "neutral", "score": 0.0}

if __name__ == "__main__":
    ai = FinanceAI()
    tests = [
        "Apple reports record earnings beat.",
        "Tesla faces lawsuit over autopilot.",
        "Market is closed today."
    ]
    for t in tests:
        print(f"'{t}' -> {ai.predict(t)}")
