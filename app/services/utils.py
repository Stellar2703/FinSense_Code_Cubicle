from typing import Tuple

NEGATIVE_WORDS = {"delay", "halts", "probe", "lawsuit", "cuts", "miss", "shortage", "breach", "recall"}
POSITIVE_WORDS = {"beats", "surge", "record", "approval", "subsidy", "upgrade", "launch"}


def classify_sentiment(text: str) -> str:
    t = text.lower()
    pos = any(w in t for w in POSITIVE_WORDS)
    neg = any(w in t for w in NEGATIVE_WORDS)
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return "neutral"


def estimate_news_impact(sentiment: str) -> float:
    # naive mapping to percent impact
    return {"positive": 2.0, "negative": -2.0, "neutral": 0.0}.get(sentiment, 0.0)


def anomaly_ratio(amount: float, avg: float, min_count: int = 5) -> Tuple[bool, float]:
    if avg <= 0 or min_count < 1:
        return (False, 0.0)
    ratio = amount / avg
    return (ratio >= 10.0, ratio)
