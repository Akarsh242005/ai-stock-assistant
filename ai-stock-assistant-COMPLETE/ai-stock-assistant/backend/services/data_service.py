"""
============================================================
Stock Data Service
============================================================
Fetches historical & intraday stock data using yfinance.
Supports NSE (Indian) and global markets.
============================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


# Map common short names → yfinance tickers
TICKER_MAP = {
    "NIFTY":     "^NSEI",
    "NIFTY50":   "^NSEI",
    "SENSEX":    "^BSESN",
    "RELIANCE":  "RELIANCE.NS",
    "TCS":       "TCS.NS",
    "INFOSYS":   "INFY.NS",
    "HDFC":      "HDFCBANK.NS",
    "WIPRO":     "WIPRO.NS",
    "AAPL":      "AAPL",
    "MSFT":      "MSFT",
    "GOOGL":     "GOOGL",
    "TSLA":      "TSLA",
}


def resolve_ticker(symbol: str) -> str:
    """Convert friendly name to yfinance ticker symbol."""
    upper = symbol.upper()
    return TICKER_MAP.get(upper, upper)


def fetch_stock_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance.

    Args:
        symbol:   Stock ticker or friendly name (e.g. 'NIFTY', 'RELIANCE')
        period:   yfinance period string ('1y', '2y', '5y', 'max')
        interval: Data interval ('1d', '1h', '5m')

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    ticker = resolve_ticker(symbol)
    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        raise ValueError(f"No data found for symbol: {symbol} (ticker: {ticker})")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    return df


def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata / stock info."""
    ticker = resolve_ticker(symbol)
    info = yf.Ticker(ticker).info
    return {
        "name":        info.get("longName", symbol),
        "sector":      info.get("sector", "N/A"),
        "industry":    info.get("industry", "N/A"),
        "market_cap":  info.get("marketCap", None),
        "currency":    info.get("currency", "INR"),
        "description": info.get("longBusinessSummary", "")[:300],
        "52w_high":    info.get("fiftyTwoWeekHigh", None),
        "52w_low":     info.get("fiftyTwoWeekLow", None),
        "pe_ratio":    info.get("trailingPE", None),
    }


def df_to_json_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-serializable list of records."""
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
