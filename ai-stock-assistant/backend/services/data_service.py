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
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Create a session with custom headers to prevent rate limits
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})

# In-memory cache to prevent rate limiting
_DATA_CACHE = {}
_INFO_CACHE = {}
CACHE_TTL = 600  # 10 minutes in seconds


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
    if upper in TICKER_MAP:
        return TICKER_MAP[upper]
    
    # Heuristics for common formats
    if upper.startswith("^") or "." in upper:
        return upper
    
    # Default to .NS for Indian stocks if it looks like one (no spaces, 3+ chars)
    if len(upper) >= 3 and " " not in upper:
        return f"{upper}.NS"
    
    return upper


def fetch_stock_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance with caching.
    """
    symbol = symbol.upper()
    cache_key = (symbol, period, interval)
    now = time.time()

    if cache_key in _DATA_CACHE:
        data, timestamp = _DATA_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return data

    ticker = resolve_ticker(symbol)
    
    try:
        # Use session to bypass rate limits
        df = yf.download(ticker, period=period, interval=interval, progress=False, session=_SESSION)
    except Exception as e:
        # Fallback without session if session causes issues
        df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df is None or df.empty:
        raise ValueError(f"No data found for symbol: {symbol} (ticker: {ticker}). Yahoo Finance may be blocking the request.")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)

    # Save to cache
    _DATA_CACHE[cache_key] = (df, now)
    return df


def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata / stock info with caching."""
    symbol = symbol.upper()
    now = time.time()

    if symbol in _INFO_CACHE:
        info, timestamp = _INFO_CACHE[symbol]
        if now - timestamp < CACHE_TTL:
            return info

    ticker = resolve_ticker(symbol)
    yf_ticker = yf.Ticker(ticker, session=_SESSION)
    try:
        info = yf_ticker.info
    except Exception:
        info = {}

    result = {
        "name":        info.get("longName", symbol),
        "sector":      info.get("sector", "N/A"),
        "industry":    info.get("industry", "N/A"),
        "market_cap":  info.get("marketCap", None),
        "currency":    info.get("currency", "INR"),
        "description": str(info.get("longBusinessSummary", ""))[:300],
        "52w_high":    info.get("fiftyTwoWeekHigh", None),
        "52w_low":     info.get("fiftyTwoWeekLow", None),
        "pe_ratio":    info.get("trailingPE", None),
    }

    _INFO_CACHE[symbol] = (result, now)
    return result


def df_to_json_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-serializable list of records."""
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
