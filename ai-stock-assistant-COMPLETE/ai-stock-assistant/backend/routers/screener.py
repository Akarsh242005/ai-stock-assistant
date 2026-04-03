from fastapi import APIRouter, HTTPException
from services.screener_service import get_top_picks
from utils import sanitize_for_json
import traceback

router = APIRouter()

@router.get("/")
def get_top_stocks():
    """Returns the top algorithmic picks from our hot watchlist."""
    try:
        picks = get_top_picks()
        return sanitize_for_json({"picks": picks})
    except Exception as e:
        print(f"Error in screener: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Screener failed")
