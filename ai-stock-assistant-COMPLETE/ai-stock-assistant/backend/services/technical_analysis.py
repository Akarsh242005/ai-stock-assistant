"""
============================================================
Technical Analysis Service
============================================================
Computes RSI, MACD, Bollinger Bands, Moving Averages.
Generates BUY / SELL / HOLD signals from combined logic.
============================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


# ─── Indicator Calculations ───────────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, pd.Series]:
    """MACD line, signal line, histogram."""
    ema_fast   = close.ewm(span=fast,   adjust=False).mean()
    ema_slow   = close.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def compute_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> Dict[str, pd.Series]:
    """Upper band, lower band, middle band (SMA)."""
    sma   = close.rolling(window=period).mean()
    std   = close.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return {"upper": upper, "middle": sma, "lower": lower}


def compute_moving_averages(close: pd.Series) -> Dict[str, pd.Series]:
    """50-day and 200-day Simple Moving Averages."""
    return {
        "sma_20":  close.rolling(20).mean(),
        "sma_50":  close.rolling(50).mean(),
        "sma_200": close.rolling(200).mean(),
    }


# ─── Signal Generation ────────────────────────────────────

def generate_signal(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Combine all indicators to produce a final trading signal.

    Scoring system:
        +1 per bullish indicator
        -1 per bearish indicator
        0 for neutral

    Returns signal dict with reasoning.
    """
    close = df["Close"]

    # Compute indicators
    rsi     = compute_rsi(close)
    macd    = compute_macd(close)
    bb      = compute_bollinger_bands(close)
    mas     = compute_moving_averages(close)

    # Latest values
    rsi_val   = float(rsi.iloc[-1])
    macd_val  = float(macd["macd"].iloc[-1])
    sig_val   = float(macd["signal"].iloc[-1])
    close_val = float(close.iloc[-1])
    bb_upper  = float(bb["upper"].iloc[-1])
    bb_lower  = float(bb["lower"].iloc[-1])
    sma50     = float(mas["sma_50"].iloc[-1]) if not pd.isna(mas["sma_50"].iloc[-1]) else close_val
    sma200    = float(mas["sma_200"].iloc[-1]) if not pd.isna(mas["sma_200"].iloc[-1]) else close_val

    score = 0
    reasons = []

    # RSI analysis
    if rsi_val < 30:
        score += 2
        reasons.append(f"RSI={rsi_val:.1f} — oversold (bullish)")
    elif rsi_val > 70:
        score -= 2
        reasons.append(f"RSI={rsi_val:.1f} — overbought (bearish)")
    else:
        reasons.append(f"RSI={rsi_val:.1f} — neutral zone")

    # MACD crossover
    if macd_val > sig_val:
        score += 1
        reasons.append("MACD above signal line — bullish crossover")
    else:
        score -= 1
        reasons.append("MACD below signal line — bearish crossover")

    # Bollinger Bands
    if close_val <= bb_lower:
        score += 1
        reasons.append("Price at lower Bollinger Band — potential reversal")
    elif close_val >= bb_upper:
        score -= 1
        reasons.append("Price at upper Bollinger Band — potential pullback")

    # Golden/Death Cross
    if sma50 > sma200:
        score += 1
        reasons.append("Golden Cross: SMA50 > SMA200 (long-term bullish)")
    else:
        score -= 1
        reasons.append("Death Cross: SMA50 < SMA200 (long-term bearish)")

    # Price vs SMA50
    if close_val > sma50:
        score += 1
        reasons.append("Price above SMA50 — short-term bullish")
    else:
        score -= 1
        reasons.append("Price below SMA50 — short-term bearish")

    # Determine signal
    if score >= 3:
        signal = "BUY"
        confidence = min(95, 60 + score * 7)
        color = "#00ff88"
    elif score <= -3:
        signal = "SELL"
        confidence = min(95, 60 + abs(score) * 7)
        color = "#ff4466"
    else:
        signal = "HOLD"
        confidence = 50 + abs(score) * 5
        color = "#ffaa00"

    # Build indicator snapshot
    indicators = {
        "rsi": round(rsi_val, 2),
        "macd": round(macd_val, 4),
        "macd_signal": round(sig_val, 4),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "sma_50":   round(sma50, 2),
        "sma_200":  round(sma200, 2),
        "close":    round(close_val, 2),
    }

    # Time-series for charts (last 100 rows)
    tail = df.tail(100).copy()
    tail.index = tail.index.strftime("%Y-%m-%d")

    chart_data = {
        "dates":      list(tail.index),
        "close":      [round(v, 2) for v in tail["Close"].tolist()],
        "sma_50":     [round(v, 2) if not pd.isna(v) else None
                       for v in mas["sma_50"].tail(100).tolist()],
        "sma_200":    [round(v, 2) if not pd.isna(v) else None
                       for v in mas["sma_200"].tail(100).tolist()],
        "bb_upper":   [round(v, 2) if not pd.isna(v) else None
                       for v in bb["upper"].tail(100).tolist()],
        "bb_lower":   [round(v, 2) if not pd.isna(v) else None
                       for v in bb["lower"].tail(100).tolist()],
        "rsi":        [round(v, 2) if not pd.isna(v) else None
                       for v in rsi.tail(100).tolist()],
        "macd_line":  [round(v, 4) if not pd.isna(v) else None
                       for v in macd["macd"].tail(100).tolist()],
        "macd_signal":[round(v, 4) if not pd.isna(v) else None
                       for v in macd["signal"].tail(100).tolist()],
        "histogram":  [round(v, 4) if not pd.isna(v) else None
                       for v in macd["histogram"].tail(100).tolist()],
    }

    return {
        "signal":     signal,
        "confidence": round(confidence, 1),
        "score":      score,
        "color":      color,
        "reasons":    reasons,
        "indicators": indicators,
        "chart_data": chart_data,
    }
