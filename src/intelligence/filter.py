from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

class NewsFilter:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.KEYWORDS = [
            "acquisition", "merger", "agrees to buy", "to acquire", "takeover",
            "earnings beat", "earnings miss", "revenue beat", "revenue miss",
            "guidance raise", "guidance cut",
            "fda approval", "fda approved", "fda rejects",
            "lawsuit", "sued", "settlement",
            "bankruptcy", "chapter 11",
            "investigation", "sec probe", "subpoena",
            "recall", "halying", "suspends"
        ]

    def check_relevance(self, text):
        """
        Check if text contains any critical keywords.
        Returns the matched keyword or None.
        """
        text_lower = text.lower()
        for kw in self.KEYWORDS:
            if kw in text_lower:
                return kw
        return None

    def evaluate(self, title, summary=""):
        full_text = f"{title}. {summary}"
        
        # 1. VADER Sentiment
        vader_score = self.analyzer.polarity_scores(full_text)['compound']
        
        # 2. TextBlob Sentiment (Second Opinion)
        blob_score = TextBlob(full_text).sentiment.polarity
        
        # Combined Score (Average)
        avg_score = (vader_score + blob_score) / 2
        
        # 3. Keyword
        kw = self.check_relevance(full_text)
        
        is_important = False
        reason = []
        
        if kw:
            is_important = True
            reason.append(f"Keyword: {kw}")
        
        # Trigger on High Sentiment (Agreement between VADER and Blob)
        if abs(avg_score) > 0.4:
             if not is_important:
                 is_important = True # Flag highly sentimental news
             
             sentiment_label = "POSITIVE" if avg_score > 0 else "NEGATIVE"
             reason.append(f"Sentiment: {sentiment_label} ({avg_score:.2f})")
             
        return {
            "is_important": is_important,
            "keyword": kw,
            "sentiment": avg_score,
            "reason": ", ".join(reason)
        }

if __name__ == "__main__":
    # Quick Test
    nf = NewsFilter()
    examples = [
        "Apple releases new iPhone case in varied colors.",
        "Pfizer wins FDA approval for new cancer drug.",
        "Tesla stock plunges 10% after recall announcement."
    ]
    
    print("--- Testing Filter ---")
    for ex in examples:
        res = nf.evaluate(ex)
        print(f"Text: {ex}")
        print(f"Result: {res}\n")
