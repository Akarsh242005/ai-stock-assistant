from utils import sanitize_for_json
'\n============================================================\nForecast Router — /api/forecast\n============================================================\nEndpoints:\n  GET  /api/forecast/{symbol}         — all 3 model forecasts\n  GET  /api/forecast/{symbol}/lstm    — LSTM only\n  GET  /api/forecast/{symbol}/prophet — Prophet only\n  GET  /api/forecast/{symbol}/arima   — ARIMA only\n  GET  /api/forecast/{symbol}/compare — side-by-side metrics\n============================================================\n'
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import traceback
from services.data_service import fetch_stock_data, fetch_stock_info
from services.lstm_service import train_and_predict
from services.prophet_service import forecast_with_prophet
from services.arima_service import forecast_with_arima
router = APIRouter()

@router.get('/{symbol}')
def get_all_forecasts(symbol: str, period: str=Query('2y', description='Historical data period')):
    """
    Run all 3 forecasting models and return combined results.
    Useful for the main dashboard view.
    """
    try:
        df = fetch_stock_data(symbol, period=period)
        info = fetch_stock_info(symbol)
        lstm_result = train_and_predict(df, symbol, epochs=15)
        prophet_result = forecast_with_prophet(df, symbol)
        arima_result = forecast_with_arima(df, symbol)
        return sanitize_for_json({'symbol': symbol.upper(), 'info': info, 'lstm': lstm_result, 'prophet': prophet_result, 'arima': arima_result})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Forecast error: {str(e)}')

@router.get('/{symbol}/lstm')
def get_lstm_forecast(symbol: str, period: str=Query('2y')):
    """LSTM deep learning forecast."""
    try:
        df = fetch_stock_data(symbol, period=period)
        return sanitize_for_json({'symbol': symbol.upper(), **train_and_predict(df, symbol)})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get('/{symbol}/prophet')
def get_prophet_forecast(symbol: str, period: str=Query('2y')):
    """Facebook Prophet forecast."""
    try:
        df = fetch_stock_data(symbol, period=period)
        return sanitize_for_json({'symbol': symbol.upper(), **forecast_with_prophet(df, symbol)})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get('/{symbol}/arima')
def get_arima_forecast(symbol: str, period: str=Query('2y')):
    """ARIMA statistical forecast."""
    try:
        df = fetch_stock_data(symbol, period=period)
        return sanitize_for_json({'symbol': symbol.upper(), **forecast_with_arima(df, symbol)})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get('/{symbol}/compare')
def compare_models(symbol: str, period: str=Query('2y')):
    """Side-by-side model comparison with metrics table."""
    try:
        df = fetch_stock_data(symbol, period=period)
        lstm_r = train_and_predict(df, symbol)
        prophet_r = forecast_with_prophet(df, symbol)
        arima_r = forecast_with_arima(df, symbol)
        comparison = [{'model': lstm_r['model'], 'rmse': lstm_r['metrics']['rmse'], 'mae': lstm_r['metrics']['mae'], 'mape': lstm_r['metrics'].get('mape', 0), 'direction': lstm_r['direction'], 'pct_change': lstm_r['pct_change']}, {'model': prophet_r['model'], 'rmse': prophet_r['metrics']['rmse'], 'mae': prophet_r['metrics']['mae'], 'mape': prophet_r['metrics'].get('mape', 0), 'direction': prophet_r['direction'], 'pct_change': prophet_r['pct_change']}, {'model': arima_r['model'], 'rmse': arima_r['metrics']['rmse'], 'mae': arima_r['metrics']['mae'], 'mape': arima_r['metrics'].get('mape', 0), 'direction': arima_r['direction'], 'pct_change': arima_r['pct_change']}]
        best_model = min(comparison, key=lambda x: x['rmse'])
        return sanitize_for_json({'symbol': symbol.upper(), 'comparison': comparison, 'best_model': best_model, 'consensus': _get_consensus(comparison)})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

def _get_consensus(models: list) -> str:
    up_count = sum((1 for m in models if m['direction'] == 'UP'))
    down_count = len(models) - up_count
    if up_count > down_count:
        return sanitize_for_json(f'BULLISH ({up_count}/{len(models)} models predict UP)')
    elif down_count > up_count:
        return sanitize_for_json(f'BEARISH ({down_count}/{len(models)} models predict DOWN)')
    else:
        return sanitize_for_json('NEUTRAL (models disagree)')