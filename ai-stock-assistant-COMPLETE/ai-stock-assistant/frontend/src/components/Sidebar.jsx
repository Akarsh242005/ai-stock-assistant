/**
 * Sidebar.jsx — Navigation sidebar
 */
export function Sidebar({ currentPage, onNavigate, marketTime, marketOpen }) {
  const nav = [
    { id: "dashboard",    icon: "⬡", label: "Dashboard",          group: "Main" },
    { id: "forecast",     icon: "◈", label: "Forecasting",         group: "Main" },
    { id: "analysis",     icon: "◉", label: "Technical Analysis",  group: "Main" },
    { id: "chart-vision", icon: "◫", label: "Chart Vision AI",     group: "AI Tools" },
    { id: "comparison",   icon: "⊞", label: "Model Comparison",    group: "AI Tools" },
  ];

  const groups = [...new Set(nav.map(n => n.group))];

  return (
    <div style={{
      width: 210, minWidth: 210,
      background: "#0d1117",
      borderRight: "1px solid #21262d",
      display: "flex", flexDirection: "column",
      fontFamily: "'DM Sans', sans-serif",
    }}>
      {/* Logo */}
      <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #21262d" }}>
        <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
                      color: "#00e5a0", letterSpacing: 2, display: "flex",
                      alignItems: "center", gap: 7 }}>
          <div style={{ width: 6, height: 6, background: "#00e5a0", borderRadius: "50%",
                        animation: "pulse 2s infinite" }} />
          STOCKVISION
        </div>
        <div style={{ fontSize: 9, color: "#8b949e", marginTop: 3, letterSpacing: 1 }}>
          AI FORECASTING v1.0
        </div>
      </div>

      {/* Nav */}
      <div style={{ padding: "10px 8px", flex: 1 }}>
        {groups.map(group => (
          <div key={group}>
            <div style={{ fontSize: 9, color: "#4a5568", letterSpacing: 1.5,
                          padding: "10px 10px 4px", textTransform: "uppercase" }}>
              {group}
            </div>
            {nav.filter(n => n.group === group).map(item => (
              <div
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 9,
                  padding: "9px 10px", borderRadius: 6, cursor: "pointer",
                  marginBottom: 1, fontSize: 12,
                  color:      currentPage === item.id ? "#00e5a0" : "#8b949e",
                  background: currentPage === item.id ? "rgba(0,229,160,.08)" : "transparent",
                  border:     currentPage === item.id ? "1px solid rgba(0,229,160,.2)" : "1px solid transparent",
                  transition: "all .15s",
                }}
              >
                <span style={{ width: 16, textAlign: "center", fontSize: 13 }}>{item.icon}</span>
                {item.label}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Market status */}
      <div style={{ padding: "10px 14px", borderTop: "1px solid #21262d",
                    fontSize: 10, color: "#8b949e" }}>
        <span style={{ display: "inline-block", width: 6, height: 6,
                       borderRadius: "50%", marginRight: 5,
                       background: marketOpen ? "#00e5a0" : "#ff3860",
                       verticalAlign: "middle" }} />
        NSE
        <span style={{ float: "right", color: "#4a5568" }}>{marketTime}</span>
      </div>
    </div>
  );
}

/**
 * Header.jsx — Top search bar
 */
export function Header({ symbol, onSymbolChange, onSearch, loading }) {
  return (
    <div style={{
      background: "#0d1117",
      borderBottom: "1px solid #21262d",
      padding: "10px 16px",
      display: "flex", alignItems: "center", gap: 10,
    }}>
      {/* Search input */}
      <div style={{ flex: 1, position: "relative" }}>
        <span style={{ position: "absolute", left: 10, top: "50%",
                       transform: "translateY(-50%)", color: "#8b949e",
                       fontSize: 14, pointerEvents: "none" }}>⌕</span>
        <input
          value={symbol}
          onChange={e => onSymbolChange(e.target.value)}
          onKeyDown={e => e.key === "Enter" && onSearch()}
          placeholder="Symbol: NIFTY  RELIANCE  TCS  AAPL  MSFT..."
          style={{
            width: "100%",
            background: "#161b22", border: "1px solid #21262d",
            borderRadius: 6, color: "#e6edf3",
            fontFamily: "'Space Mono', monospace", fontSize: 12,
            padding: "9px 12px 9px 32px", outline: "none",
          }}
        />
      </div>

      {/* Analyze button */}
      <button
        onClick={onSearch}
        disabled={loading}
        style={{
          background: loading ? "#30363d" : "#00e5a0",
          color: "#000", border: "none", borderRadius: 6,
          padding: "9px 18px", fontFamily: "'Space Mono', monospace",
          fontSize: 11, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer",
          letterSpacing: 1, whiteSpace: "nowrap",
          transition: "all .2s",
        }}
      >
        {loading ? "LOADING..." : "▶ ANALYZE"}
      </button>
    </div>
  );
}

export default Sidebar;
