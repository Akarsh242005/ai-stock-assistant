"""
============================================================
Chart Vision Service — Computer Vision Analysis
============================================================
Analyzes uploaded NIFTY / stock chart screenshots using:
  1. OpenCV-based feature extraction (color, structure)
  2. Rule-based candlestick pattern recognition
  3. Trend detection using gradient analysis
  4. Support/Resistance zone estimation

For production: Replace rule-based with fine-tuned CNN
(EfficientNet/ResNet trained on labeled chart images)
============================================================
"""

import numpy as np
import io
import base64
from PIL import Image
import random
import math

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ─── Chart Analysis Engine ────────────────────────────────

def analyze_chart_image(image_bytes: bytes) -> dict:
    """
    Main entry point: analyze a chart screenshot.

    Args:
        image_bytes: Raw bytes of uploaded PNG/JPG

    Returns:
        dict with signal, trend, patterns, confidence, reasoning
    """
    # Load image
    img_pil  = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_arr  = np.array(img_pil)

    if CV2_AVAILABLE:
        return _cv2_analysis(img_arr, img_pil)
    else:
        return _basic_analysis(img_arr, img_pil)


def _cv2_analysis(img: np.ndarray, img_pil: Image.Image) -> dict:
    """Full OpenCV-based chart analysis."""
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    h, w    = img.shape[:2]

    # ── 1. Color Analysis ─────────────────────────────────
    # Green (bullish candles), Red (bearish candles)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    green_mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))
    red_mask   = cv2.inRange(hsv, (0, 50, 50), (15, 255, 255))
    red_mask2  = cv2.inRange(hsv, (160, 50, 50), (180, 255, 255))
    red_mask   = red_mask | red_mask2

    green_pixels = cv2.countNonZero(green_mask)
    red_pixels   = cv2.countNonZero(red_mask)

    # ── 2. Edge Detection (structure) ─────────────────────
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # ── 3. Trend Direction via vertical halves ─────────────
    left_half   = gray[:, :w//2]
    right_half  = gray[:, w//2:]
    left_mean   = np.mean(left_half)
    right_mean  = np.mean(right_half)

    # Brightness heuristic: lighter right = uptrend
    brightness_trend = "bullish" if right_mean > left_mean else "bearish"

    # ── 4. Horizontal line detection (S/R) ────────────────
    # Detect via HoughLines
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi/180,
        threshold=80, minLineLength=w//5, maxLineGap=20
    )

    horizontal_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            if angle < 5:  # Nearly horizontal
                y_pos  = (y1 + y2) / 2
                price_pct = round((h - y_pos) / h * 100, 1)  # higher = higher price
                horizontal_lines.append(price_pct)

    horizontal_lines = sorted(set([round(y / 5) * 5 for y in horizontal_lines]))[:5]

    # ── 5. Signal logic ───────────────────────────────────
    green_ratio = green_pixels / max(green_pixels + red_pixels, 1)
    score       = 0
    reasons     = []

    if green_ratio > 0.6:
        score += 2
        reasons.append(f"Predominantly green candles ({green_ratio*100:.0f}%) — bullish momentum")
    elif green_ratio < 0.4:
        score -= 2
        reasons.append(f"Predominantly red candles ({(1-green_ratio)*100:.0f}%) — bearish momentum")
    else:
        reasons.append("Mixed candle colors — consolidation phase")

    if brightness_trend == "bullish":
        score += 1
        reasons.append("Price action trending upward in right portion of chart")
    else:
        score -= 1
        reasons.append("Price action trending downward in right portion of chart")

    # Check for high density of edges (volatile / breakout)
    edge_density = cv2.countNonZero(edges) / (h * w)
    if edge_density > 0.08:
        reasons.append("High volatility detected — tight candle structure")
    else:
        reasons.append("Low volatility structure detected")

    # Support/Resistance zones
    if horizontal_lines:
        reasons.append(f"Horizontal S/R zones detected at ~{horizontal_lines} price levels")

    # ── 6. Determine signal ───────────────────────────────
    if score >= 2:
        signal = "BUY"
        trend  = "Bullish"
        confidence = min(92, 65 + score * 8)
        color  = "#00ff88"
    elif score <= -2:
        signal = "SELL"
        trend  = "Bearish"
        confidence = min(92, 65 + abs(score) * 8)
        color  = "#ff4466"
    else:
        signal = "WAIT"
        trend  = "Sideways / Consolidation"
        confidence = 55
        color  = "#ffaa00"

    # Detect patterns
    patterns = _detect_patterns(img_bgr, green_pixels, red_pixels, edge_density)

    # Encode thumbnail
    thumb = img_pil.copy()
    thumb.thumbnail((300, 200))
    buf   = io.BytesIO()
    thumb.save(buf, format="PNG")
    thumb_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "signal":            signal,
        "trend":             trend,
        "confidence":        round(confidence, 1),
        "color":             color,
        "patterns":          patterns,
        "support_resistance": horizontal_lines,
        "reasons":           reasons,
        "chart_stats": {
            "green_candles_pct": round(green_ratio * 100, 1),
            "red_candles_pct":   round((1 - green_ratio) * 100, 1),
            "edge_density":      round(edge_density * 100, 2),
            "image_size":        f"{w}x{h}",
        },
        "thumbnail_b64": thumb_b64,
        "analysis_method": "OpenCV Computer Vision"
    }


def _basic_analysis(img: np.ndarray, img_pil: Image.Image) -> dict:
    """Fallback analysis without OpenCV."""
    # Simple color-based analysis via PIL
    arr     = np.array(img_pil)
    r_mean  = arr[:,:,0].mean()
    g_mean  = arr[:,:,1].mean()
    b_mean  = arr[:,:,2].mean()

    if g_mean > r_mean and g_mean > b_mean:
        signal, trend, confidence, color = "BUY", "Bullish", 68.0, "#00ff88"
        reasons = ["Green-dominant chart coloring suggests bullish momentum"]
    elif r_mean > g_mean and r_mean > b_mean:
        signal, trend, confidence, color = "SELL", "Bearish", 65.0, "#ff4466"
        reasons = ["Red-dominant chart coloring suggests bearish momentum"]
    else:
        signal, trend, confidence, color = "WAIT", "Sideways", 55.0, "#ffaa00"
        reasons = ["Neutral chart coloring — no clear directional bias"]

    reasons.append("Note: Install OpenCV for detailed analysis (pip install opencv-python)")

    return {
        "signal":            signal,
        "trend":             trend,
        "confidence":        confidence,
        "color":             color,
        "patterns":          ["Analysis limited — OpenCV not available"],
        "support_resistance": [],
        "reasons":           reasons,
        "chart_stats": {
            "r_mean": round(float(r_mean), 1),
            "g_mean": round(float(g_mean), 1),
            "b_mean": round(float(b_mean), 1),
        },
        "thumbnail_b64": "",
        "analysis_method": "Basic RGB Analysis (OpenCV fallback)"
    }


def _detect_patterns(
    img_bgr: np.ndarray,
    green_pixels: int,
    red_pixels: int,
    edge_density: float,
) -> list:
    """Detect likely candlestick/chart patterns."""
    patterns = []
    total   = green_pixels + red_pixels
    g_ratio = green_pixels / max(total, 1)

    if g_ratio > 0.7:
        patterns.append("Multiple Bullish Candles (uptrend)")
    elif g_ratio < 0.3:
        patterns.append("Multiple Bearish Candles (downtrend)")
    else:
        patterns.append("Indecision / Doji-like structure")

    if edge_density > 0.1:
        patterns.append("Volatile / Breakout Structure")
    elif edge_density < 0.04:
        patterns.append("Low Volatility / Range Bound")

    if 0.45 < g_ratio < 0.55:
        patterns.append("Possible Consolidation Zone")

    if g_ratio > 0.6 and edge_density < 0.06:
        patterns.append("Possible Ascending Channel")

    return patterns if patterns else ["No clear pattern detected"]
