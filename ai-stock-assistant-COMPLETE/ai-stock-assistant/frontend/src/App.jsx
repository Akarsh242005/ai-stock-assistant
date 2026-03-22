/**
 * ============================================================
 * AI StockVision — React Frontend Entry Point
 * ============================================================
 * Optional React version of the dashboard.
 * The standalone frontend/index.html works without React.
 *
 * Run:
 *   cd frontend
 *   npm install
 *   npm start
 * ============================================================
 */

import { useState, useEffect, useCallback } from "react";
import axios from "axios";

// ── Sub-components (inline for single-file portability) ──
import Dashboard     from "./components/Dashboard";
import Forecasting   from "./components/Forecasting";
import TechnicalAnalysis from "./components/TechnicalAnalysis";
import ChartVision   from "./components/ChartVision";
import ModelComparison from "./components/ModelComparison";
import Sidebar       from "./components/Sidebar";
import Header        from "./components/Header";

// ── API base URL ─────────────────────────────────────────
const API = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

// ── Pages ─────────────────────────────────────────────────
const PAGES = ["dashboard", "forecast", "analysis", "chart-vision", "comparison"];

export default function App() {
  const [page,     setPage]     = useState("dashboard");
  const [symbol,   setSymbol]   = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [forecast, setForecast] = useState(null);

  // ── Market time (IST) ──────────────────────────────────
  const [marketTime, setMarketTime] = useState("");
  const [marketOpen, setMarketOpen] = useState(false);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
      const h = ist.getHours(), m = ist.getMinutes().toString().padStart(2, "0");
      const open = h >= 9 && h < 16 && ist.getDay() > 0 && ist.getDay() < 6;
      setMarketTime(`${h}:${m}`);
      setMarketOpen(open);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // ── Fetch analysis + forecast ──────────────────────────
  const search = useCallback(async (sym) => {
    if (!sym) return;
    setLoading(true);
    setError(null);

    try {
      const [analysisRes, forecastRes] = await Promise.all([
        axios.get(`${API}/analysis/${sym}?period=6mo`),
        axios.get(`${API}/forecast/${sym}?period=2y`),
      ]);
      setAnalysis(analysisRes.data);
      setForecast(forecastRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch data. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = () => {
    if (symbol.trim()) search(symbol.trim().toUpperCase());
  };

  // ── Chart Vision ───────────────────────────────────────
  const [visionResult, setVisionResult] = useState(null);

  const analyzeChart = useCallback(async (file) => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await axios.post(`${API}/chart/analyze`, form);
      setVisionResult(res.data);
    } catch (err) {
      setError("Chart analysis failed. Check API connection.");
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Page content ───────────────────────────────────────
  const renderPage = () => {
    const props = { analysis, forecast, loading, error };
    switch (page) {
      case "dashboard":   return <Dashboard {...props} />;
      case "forecast":    return <Forecasting forecast={forecast} loading={loading} />;
      case "analysis":    return <TechnicalAnalysis analysis={analysis} loading={loading} />;
      case "chart-vision":return <ChartVision onAnalyze={analyzeChart} result={visionResult} loading={loading} />;
      case "comparison":  return <ModelComparison forecast={forecast} loading={loading} />;
      default:            return <Dashboard {...props} />;
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden",
                  background: "#080c10", color: "#e6edf3", fontFamily: "'DM Sans', sans-serif" }}>

      <Sidebar
        currentPage={page}
        onNavigate={setPage}
        marketTime={marketTime}
        marketOpen={marketOpen}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <Header
          symbol={symbol}
          onSymbolChange={setSymbol}
          onSearch={handleSearch}
          loading={loading}
        />
        <main style={{ flex: 1, overflow: "auto", padding: "20px" }}>
          {renderPage()}
        </main>
      </div>

    </div>
  );
}
