"""
============================================================
Stock Data Service (Hardened Production Edition)
============================================================
Fetches historical & intraday stock data using:
1. Finnhub (Primary — Highly Reliable for Real-time)
2. YahooQuery (Secondary Fallback)
3. yfinance (Tertiary Fallback)
============================================================
"""

import yfinance as yf
from yahooquery import Ticker as YQTicker
import pandas as pd
import numpy as np
import time
import requests
import random
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

try:
    from backend.config import FINNHUB_API_KEY
except ImportError:
    try:
        from config import FINNHUB_API_KEY
    except ImportError:
        FINNHUB_API_KEY = None

# Rotating User Agents (Stealth 3.0 - Human Emulation)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

_SESSION = requests.Session()

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """Decorator for exponential backoff retries."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * (2 ** x) + random.uniform(0, 1))
                    print(f"Retry {x+1}/{retries} for {func.__name__} after {sleep:.2f}s due to: {e}")
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator

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
CACHE_TTL = 60  # 1 minute for live prices

def resolve_ticker(symbol: str) -> str:
    """Convert friendly name to internal ticker symbol."""
    upper = symbol.upper()
    return TICKER_MAP.get(upper, upper)

def format_finnhub_symbol(ticker: str) -> str:
    """Format ticker for Finnhub. Keeps .NS for Indian stocks as per Finnhub docs."""
    # If it's a NIFTY index, handle specially or leave as is
    if ticker.startswith("^"): return ticker
    # For common US stocks, return as is
    # For Indian stocks, Finnhub usually uses .NS
    return ticker

@retry_with_backoff(retries=1, backoff_in_seconds=1)
def fetch_finnhub_candles(ticker: str, days: int = 365) -> pd.DataFrame:
    """Fetch candle data from Finnhub with improved error handling."""
    if not FINNHUB_API_KEY:
        print("Finnhub API Key is missing - skipping Layer 1")
        return pd.DataFrame()
    
    ticker_fh = format_finnhub_symbol(ticker)
    end = int(time.time())
    start = end - (days * 24 * 60 * 60)
    
    try:
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={ticker_fh}&resolution=D&from={start}&to={end}&token={FINNHUB_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data.get("s") != "ok":
            return pd.DataFrame()
            
        df = pd.DataFrame({
            "Open": data["o"],
            "High": data["h"],
            "Low": data["l"],
            "Close": data["c"],
            "Volume": data["v"]
        }, index=pd.to_datetime(data["t"], unit="s"))
        return df
    except Exception as e:
        print(f"Finnhub candle fetch failed: {e}")
        return pd.DataFrame()

def fetch_stock_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> Tuple[pd.DataFrame, str]:
    """Fetch OHLCV data with primary Finnhub and secondary Yahoo strategies."""
    ticker = resolve_ticker(symbol)
    cache_key = f"{ticker}_{period}_{interval}"
    now = time.time()

    if cache_key in CACHE_DATA:
        entry = CACHE_DATA[cache_key]
        if now - entry["time"] < CACHE_TTL:
            return entry["df"], entry["source"]

    df = None
    source = "Unknown"

    # --- Layer 1: Finnhub (Primary) ---
    try:
        if FINNHUB_API_KEY:
            df = fetch_finnhub_candles(ticker)
            if df is not None and not df.empty:
                source = "Finnhub"
                print(f"Data for {ticker} fetched from Finnhub")
    except Exception as e:
        print(f"Finnhub failed for {ticker}: {e}")

    # --- Layer 2: YahooQuery (Fallback 1) ---
    if df is None or df.empty:
        try:
            yq = YQTicker(ticker, session=_SESSION)
            history = yq.history(period=period, interval=interval)
            if hasattr(history, 'empty') and not history.empty:
                if isinstance(history.index, pd.MultiIndex):
                    try:
                        df = history.xs(ticker)
                    except KeyError:
                        df = history.iloc[history.index.get_level_values(0) == ticker]
                else:
                    df = history
                source = "Yahoo (Ref 1)"
        except Exception as e:
            print(f"YahooQuery failed for {ticker}: {e}")

    # --- Layer 3: yfinance (Fallback 2) ---
    if df is None or df.empty:
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df is not None and not df.empty:
                source = "Yahoo (Ref 2)"
        except Exception as e:
            print(f"yfinance failed for {ticker}: {e}")

    if df is None or df.empty:
        raise ValueError(f"Market data temporarily unavailable for {symbol}. Our providers (Finnhub & Yahoo) are experiencing high traffic. Please retry in a few moments.")

    # Cleanup and Normalization
    if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    cols_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'adj close': 'Adj Close'}
    df.rename(columns=lambda x: cols_map.get(x.lower(), x), inplace=True)
    
    if 'Close' not in df.columns and 'close' in df.columns:
        df['Close'] = df['close']

    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    
    # Save to cache
    CACHE_DATA[cache_key] = {"df": df, "time": now, "source": source}
    return df, source

def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata with caching and prioritized sources."""
    ticker = resolve_ticker(symbol)
    now = time.time()

    if ticker in CACHE_INFO:
        entry = CACHE_INFO[ticker]
        if now - entry["time"] < 300: # 5 min cache for info
            return entry["info"]

    info = {}
    source = "Yahoo" # Default source for info

    # Try Finnhub Profile first
    try:
        if FINNHUB_API_KEY:
            ticker_fh = format_finnhub_symbol(ticker)
            url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker_fh}&token={FINNHUB_API_KEY}"
            data = requests.get(url, timeout=5).json()
            if data and "name" in data:
                info = {
                    "name": data.get("name"),
                    "sector": data.get("finnhubIndustry"),
                    "currency": data.get("currency"),
                }
                source = "Finnhub"
    except: pass

    # Complement with Yahoo
    try:
        t = yf.Ticker(ticker)
        yinfo = t.info
        info.update({
            "name": info.get("name") or yinfo.get("longName") or yinfo.get("shortName") or symbol,
            "industry": yinfo.get("industry") or info.get("sector") or "N/A",
            "description": yinfo.get("longBusinessSummary", "")[:300],
            "fiftyTwoWeekHigh": yinfo.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": yinfo.get("fiftyTwoWeekLow"),
            "regularMarketPrice": yinfo.get("regularMarketPrice") or yinfo.get("currentPrice"),
            "previousClose": yinfo.get("previousClose"),
            "currency": info.get("currency") or yinfo.get("currency", "INR"),
            "source": source
        })
    except:
        if not info:
             info = {"name": symbol, "source": "Limited"}
    
    CACHE_INFO[ticker] = {"info": info, "time": now}
    return info

def df_to_json_records(df: pd.DataFrame) -> list:
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
