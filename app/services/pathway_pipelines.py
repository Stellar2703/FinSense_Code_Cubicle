# Optional: Pathway streaming pipelines placeholder.
# This demo runs on asyncio producers by default. If you install `pathway`,
# you can extend this to use real streaming connectors (Kafka, HTTP, files).

try:
    import pathway as pw  # type: ignore
    PATHWAY_AVAILABLE = True
except Exception:
    PATHWAY_AVAILABLE = False


def is_available() -> bool:
    return PATHWAY_AVAILABLE


def create_market_pipeline(state, alerts):
    """Create Pathway pipeline for market data ingestion"""
    if not PATHWAY_AVAILABLE:
        return None
    
    # Sample Pathway pipeline for market data
    # This would connect to real data sources like Kafka, REST APIs, etc.
    
    # Example: HTTP connector for market data
    market_table = pw.io.http.read(
        url="https://api.example.com/market",
        format="json",
        with_metadata=True
    )
    
    # Process market data
    processed = market_table.select(
        symbol=pw.this.symbol,
        price=pw.this.price,
        timestamp=pw.this.timestamp
    )
    
    # Output to application state
    pw.io.jsonlines.write(processed, "./data/market_output.jsonl")
    
    return processed


def create_news_pipeline(state, alerts):
    """Create Pathway pipeline for news data ingestion"""
    if not PATHWAY_AVAILABLE:
        return None
    
    # Sample Pathway pipeline for news data
    news_table = pw.io.http.read(
        url="https://api.example.com/news",
        format="json",
        with_metadata=True
    )
    
    # Process news data with sentiment analysis
    processed = news_table.select(
        symbol=pw.this.symbol,
        headline=pw.this.headline,
        sentiment=pw.apply(classify_sentiment, pw.this.headline),
        timestamp=pw.this.timestamp
    )
    
    # Output to application state
    pw.io.jsonlines.write(processed, "./data/news_output.jsonl")
    
    return processed


def run_pathway_pipelines(state, alerts):
    """Run Pathway pipelines if available"""
    if not PATHWAY_AVAILABLE:
        print("Pathway not available, using asyncio fallback")
        return False
    
    try:
        # Create and run pipelines
        market_pipeline = create_market_pipeline(state, alerts)
        news_pipeline = create_news_pipeline(state, alerts)
        
        if market_pipeline or news_pipeline:
            pw.run()
            return True
    except Exception as e:
        print(f"Pathway pipeline error: {e}")
        return False
    
    return False


# Helper function for sentiment analysis in Pathway
def classify_sentiment(headline: str) -> str:
    """Classify sentiment for use in Pathway pipelines"""
    from .utils import classify_sentiment as cs
    return cs(headline)
