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
from functools import lru_cache
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


# ─── Simple In-Memory Cache (TTL) ─────────────────────────
CACHE_DATA: Dict[str, Any] = {}
CACHE_INFO: Dict[str, Any] = {}
CACHE_TTL = 300  # 5 minutes

def resolve_ticker(symbol: str) -> str:
    """Convert friendly name to yfinance ticker symbol."""
    upper = symbol.upper()
    return TICKER_MAP.get(upper, upper)


def fetch_stock_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance with caching."""
    ticker = resolve_ticker(symbol)
    cache_key = f"{ticker}_{period}_{interval}"
    now = time.time()

    if cache_key in CACHE_DATA:
        entry = CACHE_DATA[cache_key]
        if now - entry["time"] < CACHE_TTL:
            return entry["df"]

    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        raise ValueError(f"No data found for symbol: {symbol} (ticker: {ticker})")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    
    # Save to cache
    CACHE_DATA[cache_key] = {"df": df, "time": now}
    return df


def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata / stock info with caching."""
    ticker = resolve_ticker(symbol)
    now = time.time()

    if ticker in CACHE_INFO:
        entry = CACHE_INFO[ticker]
        if now - entry["time"] < CACHE_TTL:
            return entry["info"]

    t = yf.Ticker(ticker)
    info_raw = t.info
    info = {
        "name":        info_raw.get("longName", symbol),
        "sector":      info_raw.get("sector", "N/A"),
        "industry":    info_raw.get("industry", "N/A"),
        "market_cap":  info_raw.get("marketCap", None),
        "currency":    info_raw.get("currency", "INR"),
        "description": info_raw.get("longBusinessSummary", "")[:300],
        "fiftyTwoWeekHigh": info_raw.get("fiftyTwoWeekHigh", None),
        "fiftyTwoWeekLow":  info_raw.get("fiftyTwoWeekLow", None),
        "pe_ratio":    info_raw.get("trailingPE", None),
    }
    
    # Save to cache
    CACHE_INFO[ticker] = {"info": info, "time": now}
    return info


def df_to_json_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-serializable list of records."""
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
