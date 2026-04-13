from utils import sanitize_for_json
'\n============================================================\nTechnical Analysis Router — /api/analysis\n============================================================\nEndpoints:\n  GET  /api/analysis/{symbol}       — full technical analysis\n  GET  /api/analysis/{symbol}/signal — just the signal\n  GET  /api/analysis/{symbol}/ohlcv  — raw price data\n============================================================\n'
from fastapi import APIRouter, HTTPException, Query
from services.data_service import fetch_stock_data, fetch_stock_info, df_to_json_records
from services.technical_analysis import generate_signal
router = APIRouter()

@router.get('/{symbol}')
def get_technical_analysis(symbol: str, period: str=Query('6mo', description='Data period (e.g. 3mo, 6mo, 1y, 2y)')):
    """
    Compute all technical indicators + trading signal.
    """
    try:
        df, _ = fetch_stock_data(symbol, period=period)
        info = fetch_stock_info(symbol)
        result = generate_signal(df)
        return sanitize_for_json({'symbol': symbol.upper(), 'info': info, **result})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{symbol}/signal')
def get_signal_only(symbol: str, period: str=Query('6mo')):
    """Quick signal endpoint — returns BUY/SELL/HOLD + reasons."""
    try:
        df, _ = fetch_stock_data(symbol, period=period)
        result = generate_signal(df)
        return sanitize_for_json({'symbol': symbol.upper(), 'signal': result['signal'], 'confidence': result['confidence'], 'score': result['score'], 'reasons': result['reasons'], 'indicators': result['indicators']})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get('/{symbol}/ohlcv')
def get_ohlcv(symbol: str, period: str=Query('6mo'), interval: str=Query('1d')):
    """
    Raw OHLCV data for charting.
    Supports interval: 1d, 1h, 5m (5m limited to 60 days)
    """
    try:
        df, _ = fetch_stock_data(symbol, period=period, interval=interval)
        records = df_to_json_records(df)
        return sanitize_for_json({'symbol': symbol.upper(), 'interval': interval, 'count': len(records), 'data': records})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))