"""
============================================================
Technical Analysis Service (Verdict Edition)
============================================================
Computes RSI, MACD, Bollinger Bands, Moving Averages.
Generates BUY / SELL / HOLD signals with explicit verdicts.
============================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

# ─── Indicator Calculations ───────────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

def compute_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return {"upper": upper, "middle": sma, "lower": lower}

def compute_moving_averages(close: pd.Series) -> Dict[str, pd.Series]:
    return {
        "sma_20":  close.rolling(20).mean(),
        "sma_50":  close.rolling(50).mean(),
        "sma_200": close.rolling(200).mean(),
    }

def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) for volatility-based Stop Loss."""
    tr1 = (high - low).abs()
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ─── Signal Generation ────────────────────────────────────

def generate_signal(df: pd.DataFrame) -> Dict[str, Any]:
    close = df["Close"]
    rsi = compute_rsi(close)
    macd = compute_macd(close)
    bb = compute_bollinger_bands(close)
    mas = compute_moving_averages(close)

    # Latest values
    rsi_val = float(rsi.iloc[-1])
    macd_val = float(macd["macd"].iloc[-1])
    sig_val = float(macd["signal"].iloc[-1])
    close_val = float(close.iloc[-1])
    bb_upper = float(bb["upper"].iloc[-1])
    bb_lower = float(bb["lower"].iloc[-1])
    sma50 = float(mas["sma_50"].iloc[-1]) if not pd.isna(mas["sma_50"].iloc[-1]) else close_val
    sma200 = float(mas["sma_200"].iloc[-1]) if not pd.isna(mas["sma_200"].iloc[-1]) else close_val

    score = 0
    reasons = []

    # RSI (Oversold < 30, Overbought > 70)
    if rsi_val < 30:
        score += 2
        reasons.append(f"RSI={rsi_val:.1f} — extremely oversold (bullish)")
    elif rsi_val > 70:
        score -= 2
        reasons.append(f"RSI={rsi_val:.1f} — extremely overbought (bearish)")
    
    # MACD Crossover
    if macd_val > sig_val:
        score += 1
        reasons.append("MACD is in a bullish crossover state")
    else:
        score -= 1
        reasons.append("MACD is in a bearish crossover state")
    
    # Bollinger Bands
    if close_val <= bb_lower:
        score += 1
        reasons.append("Price hitting lower Bollinger Band — potential reversal")
    elif close_val >= bb_upper:
        score -= 1
        reasons.append("Price hitting upper Bollinger Band — potential pullback")

    # Trend (MA Cross)
    if sma50 > sma200:
        score += 1
        reasons.append("Golden Cross (Bullish Pattern): SMA50 > SMA200")
    else:
        score -= 1
        reasons.append("Death Cross (Bearish Pattern): SMA50 < SMA200")

    # Determine explicit verdict
    verdict = ""
    if score >= 3:
        signal = "BUY"
        confidence = min(95, 75 + (score - 2) * 7)
        color = "#00ff88"
        verdict = "STRONG BULLISH: Multiple indicators suggest a high-probability entry point." if score >= 5 else "BULLISH: Positive momentum detected. Good entry for long positions."
    elif score <= -3:
        signal = "SELL"
        confidence = min(95, 75 + (abs(score) - 2) * 7)
        color = "#ff4466"
        verdict = "STRONG BEARISH: Indicators suggest a major reversal or crash. Exit/Short suggested." if score <= -5 else "BEARISH: Negative momentum building. Consider protecting profits or exiting."
    else:
        signal = "HOLD"
        confidence = 60 + abs(score) * 5
        color = "#ffaa00"
        verdict = "NEUTRAL: Market is consolidated or sideways. Wait for a clearer breakout."

    # --- EXPERT FEATURE: Risk Guard Setup ---
    atr_series = compute_atr(df["High"], df["Low"], df["Close"])
    atr_val = float(atr_series.iloc[-1])
    
    trade_setup = None
    if signal == "BUY":
        stop_loss = close_val - (1.5 * atr_val)
        target = close_val + (3.0 * atr_val)
        trade_setup = {
            "entry": round(close_val, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "risk_reward": "1:2 (Good Risk Management)"
        }
    elif signal == "SELL":
        stop_loss = close_val + (1.5 * atr_val)
        target = close_val - (3.0 * atr_val)
        trade_setup = {
            "entry": round(close_val, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "risk_reward": "1:2 (Good Risk Management)"
        }

    indicators = {
        "rsi": round(rsi_val, 2),
        "macd": round(macd_val, 4),
        "macd_signal": round(sig_val, 4),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "sma_50":   round(sma50, 2),
        "sma_200":  round(sma200, 2),
        "close":    round(close_val, 2),
        "atr":      round(atr_val, 2),
    }

    tail = df.tail(100).copy()
    tail.index = tail.index.strftime("%Y-%m-%d")

    chart_data = {
        "dates":      list(tail.index),
        "close":      [round(v, 2) for v in tail["Close"].tolist()],
        "sma_50":     [round(v, 2) if not pd.isna(v) else None for v in mas["sma_50"].tail(100).tolist()],
        "sma_200":    [round(v, 2) if not pd.isna(v) else None for v in mas["sma_200"].tail(100).tolist()],
        "bb_upper":   [round(v, 2) if not pd.isna(v) else None for v in bb["upper"].tail(100).tolist()],
        "bb_lower":   [round(v, 2) if not pd.isna(v) else None for v in bb["lower"].tail(100).tolist()],
        "rsi":        [round(v, 2) if not pd.isna(v) else None for v in rsi.tail(100).tolist()],
        "macd_line":  [round(v, 4) if not pd.isna(v) else None for v in macd["macd"].tail(100).tolist()],
        "macd_signal":[round(v, 4) if not pd.isna(v) else None for v in macd["signal"].tail(100).tolist()],
        "histogram":  [round(v, 4) if not pd.isna(v) else None for v in macd["histogram"].tail(100).tolist()],
    }

    return {
        "signal":     signal,
        "verdict":    verdict,
        "trade_setup": trade_setup,
        "confidence": round(confidence, 1),
        "score":      score,
        "color":      color,
        "reasons":    reasons,
        "indicators": indicators,
        "chart_data": chart_data,
    }
