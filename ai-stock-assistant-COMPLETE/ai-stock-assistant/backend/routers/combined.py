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
        df, source = fetch_stock_data(symbol, period=period)
        info = fetch_stock_info(symbol)
        
        # Ensure info has the source if it wasn't already set
        if "source" not in info:
            info["source"] = source

        # 1. Technical Analysis (Fastest, run first)
        analysis = generate_signal(df)
        
        # 2. Forecasts (Run in Parallel to save time)
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all 3 models to the thread pool
            lstm_future = executor.submit(train_and_predict, df, symbol, epochs=10)
            prophet_future = executor.submit(forecast_with_prophet, df, symbol)
            arima_future = executor.submit(forecast_with_arima, df, symbol)
            
            # Wait for all to complete with error isolation
            try: lstm_result = lstm_future.result()
            except Exception as e: 
                print(f"LSTM Error: {e}")
                from services.lstm_service import _fallback_prediction
                lstm_result = _fallback_prediction(df, symbol)
                
            try: prophet_result = prophet_future.result()
            except Exception as e: 
                print(f"Prophet Error: {e}")
                from services.prophet_service import _fallback_forecast
                prophet_result = _fallback_forecast(df, symbol)
                
            try: arima_result = arima_future.result()
            except Exception as e: 
                print(f"ARIMA Error: {e}")
                from services.arima_service import _fallback_arima
                arima_result = _fallback_arima(df, symbol)
            
        # --- EXPERT FEATURE: Backtest Scoring & Ensemble Verdict ---
        def calc_accuracy(mape):
            return max(0, min(100, 100 - float(mape)))

        if "metrics" in lstm_result and "mape" in lstm_result["metrics"]:
            lstm_result["accuracy_score"] = round(calc_accuracy(lstm_result["metrics"]["mape"]), 2)
        if "metrics" in prophet_result and "mape" in prophet_result["metrics"]:
            prophet_result["accuracy_score"] = round(calc_accuracy(prophet_result["metrics"]["mape"]), 2)
        if "metrics" in arima_result and "mape" in arima_result["metrics"]:
            arima_result["accuracy_score"] = round(calc_accuracy(arima_result["metrics"]["mape"]), 2)

        directions = [
            lstm_result.get("direction", "HOLD"), 
            prophet_result.get("direction", "HOLD"), 
            arima_result.get("direction", "HOLD")
        ]
        up_count = directions.count("UP")
        
        ensemble_direction = "HOLD"
        ensemble_confidence = 50
        if up_count == 3:
            ensemble_direction = "STRONG UP"
            ensemble_confidence = 90
        elif up_count == 2:
            ensemble_direction = "BULLISH"
            ensemble_confidence = 66
        elif up_count == 1:
            ensemble_direction = "BEARISH"
            ensemble_confidence = 66
        elif up_count == 0:
            ensemble_direction = "STRONG DOWN"
            ensemble_confidence = 90

        ensemble = {
            "verdict": ensemble_direction,
            "confidence": ensemble_confidence,
            "up_votes": up_count,
            "down_votes": 3 - up_count
        }
        
        return sanitize_for_json({
            "symbol": symbol.upper(),
            "source": source,
            "info": info,
            "analysis": analysis,
            "ensemble": ensemble,
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
