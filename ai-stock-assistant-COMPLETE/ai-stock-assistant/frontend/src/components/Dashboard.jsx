/**
 * Dashboard.jsx — Main overview page
 * Shows: stat cards, price chart, RSI, MACD, signal panel
 */

import { useEffect, useRef } from "react";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine,
} from "recharts";

const COLORS = {
  accent:  "#00e5a0",
  accent2: "#00b8ff",
  danger:  "#ff3860",
  warn:    "#ffb300",
  purple:  "#a78bfa",
  muted:   "#8b949e",
  surface: "#0d1117",
  surface2:"#161b22",
  border:  "#21262d",
};

// ── Stat Card ─────────────────────────────────────────────
function StatCard({ label, value, sub, accentColor = COLORS.accent }) {
  return (
    <div style={{
      background: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 12,
      padding: "14px 16px",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0,
                    height: 2, background: accentColor }} />
      <div style={{ fontSize: 10, color: COLORS.muted, letterSpacing: 1,
                    textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 22,
                    fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ── Signal Badge ──────────────────────────────────────────
function SignalBadge({ signal, confidence, color, score, reasons }) {
  const arrow = signal === "BUY" ? "▲" : signal === "SELL" ? "▼" : "⬡";
  const cls   = signal?.toLowerCase() || "hold";

  const badgeColors = {
    buy:  { bg: "rgba(0,229,160,.1)", border: "rgba(0,229,160,.3)", text: COLORS.accent },
    sell: { bg: "rgba(255,56,96,.1)", border: "rgba(255,56,96,.3)",  text: COLORS.danger },
    hold: { bg: "rgba(255,179,0,.1)", border: "rgba(255,179,0,.3)",  text: COLORS.warn },
  };
  const bc = badgeColors[cls] || badgeColors.hold;

  return (
    <div style={{ textAlign: "center", padding: "12px 0" }}>
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 8,
        padding: "12px 28px", borderRadius: 100,
        background: bc.bg, border: `1px solid ${bc.border}`,
        color: bc.text, fontFamily: "'Space Mono', monospace",
        fontSize: 22, fontWeight: 700, letterSpacing: "1.5px",
        marginBottom: 12,
      }}>
        {arrow} {signal}
      </div>

      <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 10 }}>
        Score: {score > 0 ? "+" : ""}{score} · Confidence: {confidence}%
      </div>

      {/* Confidence bar */}
      <div style={{ background: "#1c2332", borderRadius: 3, height: 5, overflow: "hidden",
                    margin: "0 20px 16px" }}>
        <div style={{ width: `${confidence}%`, height: "100%",
                      background: color, borderRadius: 3,
                      transition: "width 1s ease" }} />
      </div>

      {/* Reasons */}
      <div style={{ textAlign: "left", fontSize: 11, color: COLORS.muted, lineHeight: 2,
                    padding: "0 4px" }}>
        {(reasons || []).map((r, i) => (
          <div key={i}>› {r}</div>
        ))}
      </div>
    </div>
  );
}

// ── Custom tooltip ─────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#161b22", border: "1px solid #21262d",
                  borderRadius: 6, padding: "8px 12px", fontSize: 11 }}>
      <p style={{ color: COLORS.muted, marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color, margin: "2px 0" }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
        </p>
      ))}
    </div>
  );
};

// ── Dashboard ──────────────────────────────────────────────
export default function Dashboard({ analysis, forecast, loading }) {
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 60, color: COLORS.muted }}>
        <div style={{ fontFamily: "'Space Mono', monospace", letterSpacing: 2 }}>
          LOADING...
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div style={{ textAlign: "center", padding: "60px 20px" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>◈</div>
        <div style={{ fontSize: 18, fontWeight: 500, marginBottom: 8 }}>
          AI Stock Market Forecasting System
        </div>
        <div style={{ fontSize: 13, color: COLORS.muted }}>
          Enter a stock symbol above to begin — NIFTY, RELIANCE, TCS, AAPL...
        </div>
      </div>
    );
  }

  const { indicators: ind, chart_data: cd, signal, confidence,
          score, color, reasons, info = {} } = analysis;

  // Prepare chart data
  const priceData = cd.dates.map((d, i) => ({
    date:     d,
    Close:    cd.close[i],
    "SMA 50": cd.sma_50?.[i],
    "BB Up":  cd.bb_upper?.[i],
    "BB Low": cd.bb_lower?.[i],
  }));

  const rsiData = cd.dates.map((d, i) => ({ date: d, RSI: cd.rsi?.[i] }));

  const macdData = cd.dates.map((d, i) => ({
    date:      d,
    MACD:      cd.macd_line?.[i],
    Signal:    cd.macd_signal?.[i],
    Histogram: cd.histogram?.[i],
  }));

  return (
    <div>
      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 16 }}>
        <StatCard label="Current Price"   value={ind.close?.toLocaleString("en-IN")}
          sub={`${info.currency || "INR"} · ${info.name || ""}`} accentColor={COLORS.accent2} />
        <StatCard label="Signal"          value={signal} sub={`Confidence: ${confidence}%`}
          accentColor={color} />
        <StatCard label="52W High / Low"
          value={(info["52w_high"] || 0).toLocaleString("en-IN")}
          sub={`Low: ${(info["52w_low"] || 0).toLocaleString("en-IN")}`}
          accentColor={COLORS.warn} />
        <StatCard label="P/E Ratio"       value={info.pe_ratio?.toFixed(1) || "N/A"}
          sub={info.sector || "—"} accentColor={COLORS.accent} />
      </div>

      {/* Price chart + RSI */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
        <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, color: COLORS.muted, letterSpacing: 1.5,
                        textTransform: "uppercase", marginBottom: 12 }}>
            Price + Bollinger Bands
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={priceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
              <XAxis dataKey="date" hide />
              <YAxis tick={{ fill: COLORS.muted, fontSize: 9 }} width={55} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 10, color: COLORS.muted }} />
              <Line dataKey="Close"   stroke={COLORS.accent2} dot={false} strokeWidth={2} />
              <Line dataKey="SMA 50"  stroke={COLORS.warn}    dot={false} strokeWidth={1.5} strokeDasharray="4 4" />
              <Line dataKey="BB Up"   stroke="rgba(0,229,160,.3)" dot={false} strokeWidth={1} />
              <Line dataKey="BB Low"  stroke="rgba(0,229,160,.3)" dot={false} strokeWidth={1} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, color: COLORS.muted, letterSpacing: 1.5,
                        textTransform: "uppercase", marginBottom: 12 }}>RSI (14)</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={rsiData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
              <XAxis dataKey="date" hide />
              <YAxis domain={[0, 100]} tick={{ fill: COLORS.muted, fontSize: 9 }} width={30} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={70} stroke="rgba(255,56,96,.4)"  strokeDasharray="4 4" />
              <ReferenceLine y={30} stroke="rgba(0,229,160,.4)"  strokeDasharray="4 4" />
              <Line dataKey="RSI" stroke={COLORS.purple} dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* MACD + Signal */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, color: COLORS.muted, letterSpacing: 1.5,
                        textTransform: "uppercase", marginBottom: 12 }}>MACD</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={macdData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
              <XAxis dataKey="date" hide />
              <YAxis tick={{ fill: COLORS.muted, fontSize: 9 }} width={40} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="Histogram" fill={COLORS.accent} opacity={0.7}
                   label={false}
                   // Color bars by sign
                   isAnimationActive={false}
              />
              <Line dataKey="MACD"   stroke={COLORS.accent2} dot={false} strokeWidth={2} type="monotone" />
              <Line dataKey="Signal" stroke="#ff6b6b" dot={false} strokeWidth={1.5} strokeDasharray="4 4" type="monotone" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 10, color: COLORS.muted, letterSpacing: 1.5,
                        textTransform: "uppercase", marginBottom: 12 }}>Trading Signal</div>
          <SignalBadge signal={signal} confidence={confidence}
                       color={color} score={score} reasons={reasons} />
        </div>
      </div>
    </div>
  );
}
