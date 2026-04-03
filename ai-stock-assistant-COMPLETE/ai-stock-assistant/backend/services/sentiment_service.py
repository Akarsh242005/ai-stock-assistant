import yfinance as yf
from typing import Dict, Any

def analyze_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Expert Feature: Sentiment Pulse.
    Fetches the latest news headlines from Yahoo Finance and performs a keyword-based
    sentiment analysis to gauge the 'street' sentiment.
    """
    try:
        t = yf.Ticker(symbol)
        news = t.news
        
        bullish_keywords = ["surge", "jump", "rise", "soar", "gain", "up", "beat", "positive", "buy", "growth", "bull", "upgrade", "outperform"]
        bearish_keywords = ["drop", "fall", "plunge", "decline", "down", "miss", "negative", "sell", "loss", "bear", "downgrade", "underperform"]
        
        total_score = 0
        analyzed_articles = []
        
        for article in news[:5]:
            title = article.get("title", "")
            title_lower = title.lower()
            
            article_score = 0
            for b in bullish_keywords:
                if b in title_lower: article_score += 1
            for b in bearish_keywords:
                if b in title_lower: article_score -= 1
                
            total_score += article_score
            analyzed_articles.append({
                "title": title,
                "publisher": article.get("publisher", "Unknown"),
                "link": article.get("link", "#"),
                "sentiment": "BULLISH" if article_score > 0 else "BEARISH" if article_score < 0 else "NEUTRAL"
            })
            
        overall = "NEUTRAL"
        if total_score > 1: overall = "BULLISH"
        elif total_score < -1: overall = "BEARISH"
        
        return {
            "verdict": overall,
            "score": total_score,
            "articles": analyzed_articles
        }
    except Exception as e:
        print(f"Failed to fetch sentiment for {symbol}: {e}")
        return {
            "verdict": "NEUTRAL",
            "score": 0,
            "articles": [],
            "error": str(e)
        }
