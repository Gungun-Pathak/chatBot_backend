from textblob import TextBlob

# Custom negative patterns for better detection
NEGATIVE_PHRASES = [
    "i can't", "i cannot", "i'm not good enough", "i give up", "i won't make it",
    "i am worthless", "i feel hopeless", "i hate myself", "i'm done", "what's the point",
    "i'm tired of this", "nothing works", "i failed", "i always mess up"
]

def detect_sentiment(text):
    text_lower = text.lower()

    # Check for custom negative cues
    for phrase in NEGATIVE_PHRASES:
        if phrase in text_lower:
            return "negative"

    # Fallback to TextBlob
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if polarity < -0.2:
        return "negative"
    elif polarity > 0.2:
        return "positive"
    else:
        return "neutral"

# Example usage
print(detect_sentiment("i cannot do this work"))  # Will now return 'negative'
