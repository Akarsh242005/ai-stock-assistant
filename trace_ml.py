import sys
import logging
import traceback
import asyncio

sys.path.append(r"c:\Users\Akarsh Sharma\Downloads\files\ai-stock-assistant-COMPLETE\ai-stock-assistant\backend")

from services.data_service import fetch_stock_data
from services.lstm_service import train_and_predict
from services.prophet_service import forecast_with_prophet
from services.arima_service import forecast_with_arima

def test():
    try:
        print("Fetching data...")
        df = fetch_stock_data("TATASTEEL.NS")
        
        print("Running ARIMA...")
        arima = forecast_with_arima(df, "TATASTEEL.NS")
        print("ARIMA success")
        
        print("Running Prophet...")
        prophet = forecast_with_prophet(df, "TATASTEEL.NS")
        print("Prophet success")
        
        print("Running LSTM...")
        lstm = train_and_predict(df, "TATASTEEL.NS", epochs=1)
        print("LSTM success")
        
    except Exception as e:
        print("EXCEPTION CAUGHT:")
        traceback.print_exc()

test()
