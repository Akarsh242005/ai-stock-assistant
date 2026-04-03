from fastapi import APIRouter, HTTPException
from services.sentiment_service import analyze_sentiment
from utils import sanitize_for_json
import traceback

router = APIRouter()

@router.get("/{symbol}")
def get_sentiment(symbol: str):
    """Returns NLP-based market sentiment for the given ticker."""
    try:
        sentiment = analyze_sentiment(symbol)
        return sanitize_for_json(sentiment)
    except Exception as e:
        print(f"Error in sentiment pulse: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Sentiment analyzer failed")
