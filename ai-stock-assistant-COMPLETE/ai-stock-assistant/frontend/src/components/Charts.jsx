/**
 * Forecasting.jsx — LSTM / Prophet / ARIMA forecast charts
 */
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from "recharts";

const C = { accent:"#00e5a0", accent2:"#00b8ff", muted:"#8b949e",
            surface:"#0d1117", border:"#21262d", purple:"#a78bfa" };

const card = { background: C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:16, marginBottom:14 };
const cardTitle = { fontSize:10, color:C.muted, letterSpacing:1.5, textTransform:"uppercase", marginBottom:12 };

const Tip = ({active,payload,label}) => {
  if(!active||!payload?.length) return null;
  return <div style={{background:"#161b22",border:"1px solid #21262d",borderRadius:6,padding:"8px 12px",fontSize:11}}>
    <p style={{color:C.muted,marginBottom:4}}>{label}</p>
    {payload.map((p,i)=><p key={i} style={{color:p.color,margin:"2px 0"}}>{p.name}: {p.value?.toFixed?.(2)??p.value}</p>)}
  </div>;
};

const MetricChip = ({label,value}) => (
  <div style={{background:"#161b22",border:"1px solid #21262d",borderRadius:6,padding:"7px 12px",display:"inline-block",marginRight:8}}>
    <div style={{fontSize:9,color:C.muted,letterSpacing:1}}>{label}</div>
    <div style={{fontFamily:"'Space Mono',monospace",fontSize:13,fontWeight:700}}>{value}</div>
  </div>
);

function ForecastPanel({ model, accentColor = C.accent }) {
  if (!model) return <div style={{color:C.muted,padding:20}}>No data</div>;
  const avpData = model.test_dates?.map((d,i)=>({date:d,Actual:model.actuals?.[i],Predicted:model.predictions?.[i]})) || [];
  const fcData  = model.forecast_dates?.map((d,i)=>({date:d,Forecast:model.forecast?.[i],Upper:model.forecast_upper?.[i],Lower:model.forecast_lower?.[i]})) || [];
  return (
    <div>
      <div style={{marginBottom:12}}>
        <MetricChip label="RMSE" value={model.metrics?.rmse?.toFixed(4)} />
        <MetricChip label="MAE"  value={model.metrics?.mae?.toFixed(4)} />
        <MetricChip label="MAPE" value={`${model.metrics?.mape?.toFixed(2)}%`} />
        <span style={{marginLeft:8,fontSize:12,fontFamily:"'Space Mono',monospace",
          color:model.direction==="UP"?"#00e5a0":"#ff3860"}}>
          {model.direction==="UP"?"▲ UP":"▼ DOWN"} {model.pct_change>0?"+":""}{model.pct_change}%
        </span>
      </div>
      <div style={card}>
        <div style={cardTitle}>Actual vs Predicted</div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={avpData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
            <XAxis dataKey="date" hide />
            <YAxis tick={{fill:C.muted,fontSize:9}} width={55} />
            <Tooltip content={<Tip/>} />
            <Legend iconSize={10} wrapperStyle={{fontSize:10,color:C.muted}} />
            <Line dataKey="Actual"    stroke={C.muted}      dot={false} strokeWidth={1.5} />
            <Line dataKey="Predicted" stroke={accentColor}  dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div style={card}>
        <div style={cardTitle}>7-Day Forecast</div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={fcData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
            <XAxis dataKey="date" tick={{fill:C.muted,fontSize:9}} />
            <YAxis tick={{fill:C.muted,fontSize:9}} width={55} />
            <Tooltip content={<Tip/>} />
            <Legend iconSize={10} wrapperStyle={{fontSize:10,color:C.muted}} />
            <Line dataKey="Upper"    stroke="rgba(0,184,255,.3)" dot={false} strokeWidth={1} />
            <Line dataKey="Lower"    stroke="rgba(0,184,255,.3)" dot={false} strokeWidth={1} />
            <Line dataKey="Forecast" stroke={C.accent2} dot={{r:4,fill:C.accent2}} strokeWidth={2.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function Forecasting({ forecast }) {
  const [tab, setTab] = useState("lstm");
  if (!forecast) return <div style={{textAlign:"center",padding:60,color:C.muted}}>Search a stock to see forecasts</div>;
  const tabs = [{id:"lstm",label:"LSTM"},{id:"prophet",label:"Prophet"},{id:"arima",label:"ARIMA"}];
  const colors = {lstm:C.accent,prophet:C.accent2,arima:C.purple};
  return (
    <div>
      <div style={{display:"flex",gap:4,marginBottom:14}}>
        {tabs.map(t=>(
          <div key={t.id} onClick={()=>setTab(t.id)} style={{
            padding:"7px 14px",borderRadius:6,fontSize:11,fontFamily:"'Space Mono',monospace",
            cursor:"pointer",border:"1px solid",
            borderColor:tab===t.id?"rgba(0,229,160,.3)":"#21262d",
            color:tab===t.id?"#00e5a0":"#8b949e",
            background:tab===t.id?"rgba(0,229,160,.1)":"transparent",
          }}>{t.label}</div>
        ))}
      </div>
      <ForecastPanel model={forecast[tab]} accentColor={colors[tab]} />
    </div>
  );
}


/**
 * TechnicalAnalysis.jsx
 */
export function TechnicalAnalysis({ analysis }) {
  if (!analysis) return <div style={{textAlign:"center",padding:60,color:C.muted}}>Search a stock to see indicators</div>;
  const { indicators:ind, chart_data:cd, signal, confidence, color, score, reasons } = analysis;
  const priceData = cd.dates.map((d,i)=>({date:d,Close:cd.close?.[i],"SMA50":cd.sma_50?.[i],"SMA200":cd.sma_200?.[i]}));
  const arr = signal==="BUY"?"▲":signal==="SELL"?"▼":"⬡";
  return (
    <div>
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:16}}>
        {[{l:"RSI",v:ind.rsi,c:ind.rsi<30?"#00e5a0":ind.rsi>70?"#ff3860":"#e6edf3"},
          {l:"MACD",v:ind.macd?.toFixed(3),c:ind.macd>ind.macd_signal?"#00e5a0":"#ff3860"},
          {l:"SMA 50",v:ind.sma_50?.toLocaleString?.("en-IN"),c:"#ffb300"},
          {l:"SMA 200",v:ind.sma_200?.toLocaleString?.("en-IN"),c:"#00b8ff"},
          {l:"Close",v:ind.close?.toLocaleString?.("en-IN"),c:"#e6edf3"},
        ].map(({l,v,c})=>(
          <div key={l} style={{background:"#161b22",border:"1px solid #21262d",borderRadius:6,padding:"7px 12px"}}>
            <div style={{fontSize:9,color:C.muted,letterSpacing:1}}>{l}</div>
            <div style={{fontFamily:"'Space Mono',monospace",fontSize:13,fontWeight:700,color:c}}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginBottom:14}}>
        <div style={card}>
          <div style={cardTitle}>Signal</div>
          <div style={{textAlign:"center",padding:"16px 0"}}>
            <div style={{display:"inline-flex",alignItems:"center",gap:8,padding:"12px 28px",borderRadius:100,
              background:signal==="BUY"?"rgba(0,229,160,.1)":signal==="SELL"?"rgba(255,56,96,.1)":"rgba(255,179,0,.1)",
              border:`1px solid ${signal==="BUY"?"rgba(0,229,160,.3)":signal==="SELL"?"rgba(255,56,96,.3)":"rgba(255,179,0,.3)"}`,
              color,fontFamily:"'Space Mono',monospace",fontSize:26,fontWeight:700,letterSpacing:1.5}}>
              {arr} {signal}
            </div>
            <div style={{marginTop:10,fontSize:12,color:C.muted}}>Score: {score>0?"+":""}{score} · {confidence}%</div>
          </div>
        </div>
        <div style={card}>
          <div style={cardTitle}>Reasoning</div>
          <ul style={{listStyle:"none",margin:0,padding:0}}>
            {(reasons||[]).map((r,i)=>(
              <li key={i} style={{padding:"5px 0",borderBottom:"1px solid #21262d",fontSize:11,color:C.muted,
                display:"flex",gap:6}}><span style={{color:"#00e5a0",flexShrink:0}}>›</span>{r}</li>
            ))}
          </ul>
        </div>
      </div>
      <div style={card}>
        <div style={cardTitle}>Price + MAs</div>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={priceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
            <XAxis dataKey="date" hide />
            <YAxis tick={{fill:C.muted,fontSize:9}} width={55} />
            <Tooltip content={<Tip/>} />
            <Legend iconSize={10} wrapperStyle={{fontSize:10,color:C.muted}} />
            <Line dataKey="Close"  stroke={C.accent2} dot={false} strokeWidth={2} />
            <Line dataKey="SMA50"  stroke="#ffb300"   dot={false} strokeWidth={1.5} strokeDasharray="5 5" />
            <Line dataKey="SMA200" stroke={C.purple}  dot={false} strokeWidth={1.5} strokeDasharray="8 4" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


/**
 * ChartVision.jsx — image upload + AI analysis result
 */
export function ChartVision({ onAnalyze, result, loading }) {
  const handleFile = (e) => { const f=e.target.files[0]; if(f) onAnalyze(f); };
  const handleDrop = (e) => { e.preventDefault(); const f=e.dataTransfer.files[0]; if(f) onAnalyze(f); };
  const arr = result?.signal==="BUY"?"▲":result?.signal==="SELL"?"▼":"⬡";
  const sigColor = result?.color||C.muted;

  return (
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
      <div>
        <div style={card}>
          <div style={cardTitle}>Upload Chart Screenshot</div>
          <div onDragOver={e=>e.preventDefault()} onDrop={handleDrop}
               onClick={()=>document.getElementById("cv-file").click()}
               style={{border:"2px dashed #30363d",borderRadius:12,padding:"36px 20px",
                       textAlign:"center",cursor:"pointer",transition:"all .2s"}}>
            <div style={{fontSize:32,marginBottom:10}}>⬡</div>
            <div style={{fontSize:13,fontWeight:500,marginBottom:4}}>Drop chart screenshot here</div>
            <div style={{fontSize:11,color:C.muted}}>or click to browse · PNG / JPG</div>
          </div>
          <input id="cv-file" type="file" accept="image/*" onChange={handleFile} style={{display:"none"}} />
        </div>
      </div>
      <div>
        {loading && <div style={{textAlign:"center",padding:60,color:C.muted,fontFamily:"'Space Mono',monospace"}}>ANALYZING...</div>}
        {!loading && !result && <div style={{textAlign:"center",padding:60}}><div style={{fontSize:36,marginBottom:12}}>◫</div><div style={{color:C.muted}}>Upload a chart to analyze</div></div>}
        {!loading && result && (
          <div style={card}>
            <div style={cardTitle}>AI Analysis Result</div>
            <div style={{display:"flex",gap:16,alignItems:"start",marginBottom:16}}>
              {result.thumbnail_b64 && <img src={`data:image/png;base64,${result.thumbnail_b64}`} alt="chart" style={{width:160,borderRadius:6,border:"1px solid #21262d"}} />}
              <div style={{flex:1}}>
                <div style={{fontFamily:"'Space Mono',monospace",fontSize:40,fontWeight:700,color:sigColor,lineHeight:1,marginBottom:6}}>{arr} {result.signal}</div>
                <div style={{fontSize:12,color:C.muted,marginBottom:10}}>Trend: {result.trend}</div>
                <div style={{fontSize:10,color:C.muted,marginBottom:4}}>Confidence: {result.confidence}%</div>
                <div style={{background:"#1c2332",borderRadius:3,height:5,overflow:"hidden"}}>
                  <div style={{width:`${result.confidence}%`,height:"100%",background:sigColor,borderRadius:3}} />
                </div>
              </div>
            </div>
            <ul style={{listStyle:"none",margin:0,padding:0}}>
              {(result.reasons||[]).map((r,i)=>(
                <li key={i} style={{padding:"5px 0",borderBottom:"1px solid #21262d",fontSize:11,color:C.muted,display:"flex",gap:6}}>
                  <span style={{color:"#00e5a0"}}>›</span>{r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}


/**
 * ModelComparison.jsx
 */
export function ModelComparison({ forecast }) {
  if (!forecast) return <div style={{textAlign:"center",padding:60,color:C.muted}}>Search a stock to compare models</div>;
  const ms=[forecast.lstm,forecast.prophet,forecast.arima];
  const best=ms.reduce((a,b)=>a.metrics?.rmse<b.metrics?.rmse?a:b);
  const upCount=ms.filter(m=>m.direction==="UP").length;
  const fcData=forecast.lstm.forecast_dates?.map((d,i)=>({date:d,LSTM:forecast.lstm.forecast?.[i],Prophet:forecast.prophet.forecast?.[i],ARIMA:forecast.arima.forecast?.[i]}));

  return (
    <div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:16}}>
        <div style={{background:C.surface,border:"1px solid #21262d",borderRadius:12,padding:"14px 16px",position:"relative",overflow:"hidden"}}>
          <div style={{position:"absolute",top:0,left:0,right:0,height:2,background:C.accent}} />
          <div style={{fontSize:10,color:C.muted,letterSpacing:1,textTransform:"uppercase",marginBottom:6}}>Best Model</div>
          <div style={{fontFamily:"'Space Mono',monospace",fontSize:16,fontWeight:700}}>{best.model}</div>
          <div style={{fontSize:11,color:C.muted,marginTop:4}}>RMSE: {best.metrics?.rmse?.toFixed(2)}</div>
        </div>
        <div style={{background:C.surface,border:"1px solid #21262d",borderRadius:12,padding:"14px 16px",position:"relative",overflow:"hidden"}}>
          <div style={{position:"absolute",top:0,left:0,right:0,height:2,background:upCount>=2?"#00e5a0":"#ff3860"}} />
          <div style={{fontSize:10,color:C.muted,letterSpacing:1,textTransform:"uppercase",marginBottom:6}}>Consensus</div>
          <div style={{fontFamily:"'Space Mono',monospace",fontSize:16,fontWeight:700,color:upCount>=2?"#00e5a0":"#ff3860"}}>{upCount>=2?"BULLISH":"BEARISH"}</div>
          <div style={{fontSize:11,color:C.muted,marginTop:4}}>{upCount}/3 say UP</div>
        </div>
        {ms.slice(0,2).map(m=>(
          <div key={m.model} style={{background:C.surface,border:"1px solid #21262d",borderRadius:12,padding:"14px 16px",position:"relative",overflow:"hidden"}}>
            <div style={{position:"absolute",top:0,left:0,right:0,height:2,background:"#00b8ff"}} />
            <div style={{fontSize:10,color:C.muted,letterSpacing:1,textTransform:"uppercase",marginBottom:6}}>{m.model} 7d Δ</div>
            <div style={{fontFamily:"'Space Mono',monospace",fontSize:18,fontWeight:700,color:m.pct_change>=0?"#00e5a0":"#ff3860"}}>{m.pct_change>=0?"+":""}{m.pct_change}%</div>
          </div>
        ))}
      </div>

      <div style={card}>
        <div style={cardTitle}>Performance Metrics</div>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
          <thead><tr>{["Model","RMSE ↓","MAE ↓","MAPE ↓","Direction","7-day Δ"].map(h=>(
            <th key={h} style={{textAlign:"left",padding:"8px 12px",background:"#161b22",color:C.muted,fontSize:9,letterSpacing:1.5,textTransform:"uppercase",fontWeight:400}}>{h}</th>
          ))}</tr></thead>
          <tbody>{ms.map(m=>(
            <tr key={m.model} style={{background:m.model===best.model?"rgba(0,229,160,.04)":"transparent"}}>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",fontWeight:600}}>
                {m.model}{m.model===best.model&&<span style={{background:"rgba(0,229,160,.15)",color:"#00e5a0",fontSize:9,padding:"2px 6px",borderRadius:4,marginLeft:6,letterSpacing:1}}>BEST</span>}
              </td>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",fontFamily:"'Space Mono',monospace"}}>{m.metrics?.rmse?.toFixed(4)}</td>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",fontFamily:"'Space Mono',monospace"}}>{m.metrics?.mae?.toFixed(4)}</td>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",fontFamily:"'Space Mono',monospace"}}>{m.metrics?.mape?.toFixed(2)}%</td>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",color:m.direction==="UP"?"#00e5a0":"#ff3860"}}>{m.direction==="UP"?"▲ UP":"▼ DOWN"}</td>
              <td style={{padding:"10px 12px",borderBottom:"1px solid #21262d",color:m.pct_change>=0?"#00e5a0":"#ff3860"}}>{m.pct_change>=0?"+":""}{m.pct_change}%</td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      <div style={card}>
        <div style={cardTitle}>7-Day Forecast Comparison</div>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={fcData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
            <XAxis dataKey="date" tick={{fill:C.muted,fontSize:9}} />
            <YAxis tick={{fill:C.muted,fontSize:9}} width={55} />
            <Tooltip content={<Tip/>} />
            <Legend iconSize={10} wrapperStyle={{fontSize:10,color:C.muted}} />
            <Line dataKey="LSTM"    stroke={C.accent}  dot={{r:4,fill:C.accent}}  strokeWidth={2.5} />
            <Line dataKey="Prophet" stroke={C.accent2} dot={{r:4,fill:C.accent2}} strokeWidth={2} strokeDasharray="6 3" />
            <Line dataKey="ARIMA"   stroke={C.purple}  dot={{r:4,fill:C.purple}}  strokeWidth={2} strokeDasharray="3 3" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
