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
from typing import Optional, Dict, Any
import os

try:
    from .. import config
except (ImportError, ValueError):
    import backend.config as config

# Create a session with custom headers to prevent rate limits
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://finance.yahoo.com",
    "Referer": "https://finance.yahoo.com"
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
        # One last try with a fresh session
        try:
            temp_session = requests.Session()
            df = yf.download(ticker, period=period, interval=interval, progress=False, session=temp_session)
        except:
            pass
            
    if df is None or df.empty:
        raise ValueError(f"No data found for symbol: {symbol} (ticker: {ticker}). Yahoo Finance may be blocking the request.")

    # Flatten MultiIndex columns if present
    if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if hasattr(df, 'index'):
        df.index = pd.to_datetime(df.index)
    
    if hasattr(df, 'dropna'):
        df.dropna(inplace=True)

    # Save to cache
    _DATA_CACHE[cache_key] = (df, now)
    return df


def fetch_finnhub_info(symbol: str) -> Dict[str, Any]:
    """Fetch metadata from Finnhub if possible."""
    if not config.FINNHUB_API_KEY:
        return {}
    
    # Try to map to Finnhub format (usually just the symbol or SYMBOL.NS)
    # Finnhub often uses US symbols without prefix
    try:
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={config.FINNHUB_API_KEY}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata / stock info with caching and multi-source fallback."""
    symbol = symbol.upper()
    now = time.time()

    if symbol in _INFO_CACHE:
        info, timestamp = _INFO_CACHE[symbol]
        if now - timestamp < CACHE_TTL:
            return info

    ticker = resolve_ticker(symbol)
    
    # Try Finnhub First for Metadata (More reliable than Yahoo .info)
    fh_info = fetch_finnhub_info(symbol)
    if not fh_info and "." in ticker:
        # Try without suffix for Indian stocks in Finnhub (sometimes works)
        fh_info = fetch_finnhub_info(symbol.split(".")[0])

    # Fallback to Yahoo for deeper metadata or if Finnhub failed
    yf_ticker = yf.Ticker(ticker, session=_SESSION)
    try:
        yf_info = yf_ticker.info
    except Exception:
        yf_info = {}

    # Hybrid Result
    result = {
        "name":        fh_info.get("name") or yf_info.get("longName") or symbol,
        "sector":      fh_info.get("finnhubIndustry") or yf_info.get("sector") or "N/A",
        "industry":    fh_info.get("finnhubIndustry") or yf_info.get("industry") or "N/A",
        "market_cap":  yf_info.get("marketCap", None),
        "currency":    fh_info.get("currency") or yf_info.get("currency") or "INR",
        "description": str(yf_info.get("longBusinessSummary", ""))[:300],
        "52w_high":    yf_info.get("fiftyTwoWeekHigh", None),
        "52w_low":     yf_info.get("fiftyTwoWeekLow", None),
        "pe_ratio":    yf_info.get("trailingPE", None),
    }

    # If we still have almost no info, try to get at least the name from yfinance download if available
    if result["name"] == symbol:
        try:
            # Maybe the data cache has it?
            pass # We could try more here but usually if download worked, info might work eventually
        except:
            pass

    _INFO_CACHE[symbol] = (result, now)
    return result


def df_to_json_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-serializable list of records."""
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
