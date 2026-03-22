"""
============================================================
AI Stock Market Forecasting & Trading Assistant
Backend API — FastAPI Application
============================================================
Author: [Your Name]
Description: REST API for stock predictions, technical
             analysis, and chart image analysis.
============================================================
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import json
import typing

class NumpyResponse(Response):
    media_type = "application/json"
    def render(self, content: typing.Any) -> bytes:
        def fallback(o):
            import numpy as np
            import pandas as pd
            if isinstance(o, np.integer): return int(o)
            if isinstance(o, np.floating): return float(o)
            if hasattr(np, "bool_") and isinstance(o, np.bool_): return bool(o)
            if isinstance(o, np.ndarray): return o.tolist()
            if hasattr(pd, "Timestamp") and isinstance(o, pd.Timestamp): return o.isoformat()
            if hasattr(pd, "Series") and isinstance(o, pd.Series): return o.tolist()
            return str(o)
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=fallback,
        ).encode("utf-8")

# Internal modules
from routers import forecast, analysis, chart_vision, health

# ─── App Init ────────────────────────────────────────────
app = FastAPI(
    default_response_class=NumpyResponse,
    title="AI Stock Market Forecasting API",
    description="""
    A production-grade API for stock market analysis powered by:
    - LSTM Deep Learning forecasting
    - Facebook Prophet time-series models
    - ARIMA statistical forecasting
    - Technical Analysis (RSI, MACD, Bollinger Bands)
    - Computer Vision chart analysis
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS (allow frontend) ────────────────────────────────
origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────
app.include_router(health.router,       prefix="/api",          tags=["Health"])
app.include_router(forecast.router,     prefix="/api/forecast", tags=["Forecasting"])
app.include_router(analysis.router,     prefix="/api/analysis", tags=["Technical Analysis"])
app.include_router(chart_vision.router, prefix="/api/chart",    tags=["Chart Vision"])


# ─── Root ─────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "AI Stock Market Forecasting API is live 🚀",
        "docs": "/api/docs",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
