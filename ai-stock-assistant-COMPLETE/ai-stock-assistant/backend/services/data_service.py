"""
============================================================
Stock Data Service (Hardened Edition)
============================================================
Fetches historical & intraday stock data using:
1. YahooQuery (Stealth Layer)
2. yfinance (Primary Fallback)
3. Finnhub (Fail-Soft Failover)
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
from typing import Optional, Dict, Any

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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

_SESSION = requests.Session()

def jitter():
    """Simulate human reaction time between 200ms and 800ms."""
    time.sleep(random.uniform(0.2, 0.8))

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

def fetch_finnhub_candles(ticker: str, resolution: str = "D", days: int = 365) -> pd.DataFrame:
    """Fail-soft fallback using Finnhub candles if Yahoo is unreachable."""
    try:
        if not FINNHUB_API_KEY:
            return pd.DataFrame()
        
        end = int(time.time())
        start = end - (days * 24 * 60 * 60)
        
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={ticker}&resolution={resolution}&from={start}&to={end}&token={FINNHUB_API_KEY}"
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
        print(f"Finnhub candle fallback failed for {ticker}: {e}")
        return pd.DataFrame()

def fetch_stock_data(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV data with multi-layer fallback strategy."""
    ticker = resolve_ticker(symbol)
    cache_key = f"{ticker}_{period}_{interval}"
    now = time.time()

    if cache_key in CACHE_DATA:
        entry = CACHE_DATA[cache_key]
        if now - entry["time"] < CACHE_TTL:
            return entry["df"]

    df = None

    # --- Layer 1: YahooQuery (More resilient than yfinance) ---
    try:
        jitter()
        yq = YQTicker(ticker, session=_SESSION)
        # Map period/interval to yahooquery format
        history = yq.history(period=period, interval=interval)
        if hasattr(history, 'empty') and not history.empty:
            if isinstance(history.index, pd.MultiIndex):
                # Safely extract the ticker from MultiIndex
                try:
                    df = history.xs(ticker)
                except KeyError:
                    # If ticker is not exactly in index (e.g. index has different format), take first group
                    df = history.iloc[history.index.get_level_values(0) == ticker]
            else:
                df = history
    except Exception as e:
        print(f"YahooQuery failed for {ticker}: {e}")

    # --- Layer 2: yfinance Fallback ---
    if df is None or (hasattr(df, 'empty') and df.empty):
        try:
            jitter()
            # IMPORTANT: Let yf handle its own session to avoid 'curl_cffi' errors
            df = yf.download(ticker, period=period, interval=interval, progress=False, session=None)
        except Exception as e:
            print(f"yfinance fallback failed for {ticker}: {e}")

    # --- Layer 3: Finnhub Candles (Fail-Soft) ---
    if df is None or df.empty:
        print(f"All Yahoo sources blocked for {ticker}. Attempting Finnhub failover...")
        df = fetch_finnhub_candles(ticker)
        # Handle Indian stocks suffix for Finnhub if needed
        if (df is None or df.empty) and "." in ticker:
            df = fetch_finnhub_candles(ticker.split(".")[0])

    if df is None or df.empty:
        raise ValueError(f"CRITICAL: Too Many Requests. Both Yahoo and Finnhub are temporarily unavailable for {symbol}. Try again in 5 minutes.")

    # Flatten MultiIndex columns if present
    if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # NORMALIZE COLUMN NAMES (Standardize to TitleCase for yfinance compatibility)
    # This fixes KeyError: 'Close' when using yahooquery (which returns lowercase)
    cols_map = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'adjclose': 'Adj Close',
        'adj close': 'Adj Close'
    }
    df.rename(columns=lambda x: cols_map.get(x.lower(), x), inplace=True)

    # Ensure critical columns exist
    if 'Close' not in df.columns and 'close' in df.columns:
        df['Close'] = df['close']

    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    
    # Save to cache
    CACHE_DATA[cache_key] = {"df": df, "time": now}
    return df

def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata with caching and multiple sources."""
    ticker = resolve_ticker(symbol)
    now = time.time()

    if ticker in CACHE_INFO:
        entry = CACHE_INFO[ticker]
        if now - entry["time"] < CACHE_TTL:
            return entry["info"]

    # Try Finnhub first for metadata (rarely rate-limited)
    info = {}
    try:
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={FINNHUB_API_KEY}"
        data = requests.get(url, timeout=5).json()
        if data:
            info = {
                "name": data.get("name", symbol),
                "sector": data.get("finnhubIndustry", "N/A"),
                "currency": data.get("currency", "INR"),
                "market_cap": data.get("marketCapitalization", 0) * 1000000,
            }
    except: pass

    # Supplement/Fallback with YFinance
    try:
        t = yf.Ticker(ticker, session=_SESSION)
        yinfo = t.info
        info.update({
            "industry": yinfo.get("industry", info.get("sector", "N/A")),
            "description": yinfo.get("longBusinessSummary", "")[:300],
            "fiftyTwoWeekHigh": yinfo.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": yinfo.get("fiftyTwoWeekLow"),
            "pe_ratio": yinfo.get("trailingPE"),
            "regularMarketPrice": yinfo.get("regularMarketPrice")
        })
    except: pass
    
    CACHE_INFO[ticker] = {"info": info, "time": now}
    return info

def df_to_json_records(df: pd.DataFrame) -> list:
    df_copy = df.copy()
    df_copy.index = df_copy.index.strftime("%Y-%m-%d")
    return df_copy.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")
