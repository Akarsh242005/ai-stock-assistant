from utils import sanitize_for_json
from fastapi import APIRouter, HTTPException, Query
from services.data_service import fetch_stock_data, fetch_stock_info
from services.technical_analysis import generate_signal
from services.lstm_service import train_and_predict
from services.prophet_service import forecast_with_prophet
from services.arima_service import forecast_with_arima
import traceback

router = APIRouter()

@router.get("/{symbol}")
def get_combined_analysis(symbol: str, period: str = Query("2y")):
    """
    Combined endpoint for Dashboard: Returns Technical Analysis + All 3 Forecasts.
    This reduces the number of API calls from 2 to 1 and leverages backend caching.
    """
    try:
        # These will be cached after the first call inside data_service
        df = fetch_stock_data(symbol, period=period)
        info = fetch_stock_info(symbol)
        
        # 1. Technical Analysis
        analysis = generate_signal(df)
        
        # 2. Forecasts
        lstm_result = train_and_predict(df, symbol, epochs=10) # Lower epochs for faster live response
        prophet_result = forecast_with_prophet(df, symbol)
        arima_result = forecast_with_arima(df, symbol)
        
        return sanitize_for_json({
            "symbol": symbol.upper(),
            "info": info,
            "analysis": analysis,
            "forecast": {
                "lstm": lstm_result,
                "prophet": prophet_result,
                "arima": arima_result
            }
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error in combined analysis: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
