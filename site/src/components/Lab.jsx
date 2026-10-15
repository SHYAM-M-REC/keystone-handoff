import { useEffect, useState } from "react";
import Scene from "./Scene.jsx";
import { data, N_MONTHS, SEV_COLOUR, SEV_MARK, prettyRegion } from "../data/loader.js";

export default function Lab({ month, setMonth }) {
  const [exag, setExag] = useState(60);
  const [play, setPlay] = useState(false);
  const [ghost, setGhost] = useState(true);

  useEffect(() => {
    if (!play) return;
    const id = setInterval(() => setMonth((m) => { if (m >= N_MONTHS) { setPlay(false); return m; } return m + 1; }), 900);
    return () => clearInterval(id);
  }, [play, setMonth]);

  const rows = data.regions;
  return (
    <section className="section dark" id="lab">
      <div className="wrap">
        <h2 className="big">The temple lab</h2>
        <p className="sub">
          A simulated stone temple, captured once a month for a year. Drag to turn it. We planted a leaning tower, a column that settles
          and two cracks that grow, so the truth is known and every alert can be checked.
        </p>
        <div className="lab">
          <div className="lab-view">
            <Scene month={month} exag={exag} ghost={ghost} interactive distance={0.72} pointSize={0.05} />
            <div className="legend" aria-hidden="true">
              <span>moved one way</span><i className="bar" /><span>the other</span>
              <em><u className="q" /> inside the noise <u className="v" /> crack gap</em>
            </div>
            <p className="view-note">Movement drawn ×{exag}. Crack gaps drawn ×{data.gapExag} wider than real, so they can be seen.</p>
          </div>
          <aside className="lab-side">
            <div className="controls">
              <div className="row">
                <button className="btn small" onClick={() => { if (month >= N_MONTHS) setMonth(0); setPlay((p) => !p); }}>{play ? "Pause" : "Play"}</button>
                <label className="grow">
                  <span>Month <b>{month}</b> of {N_MONTHS}{month > 0 && <small> · {data.dates[month]}</small>}</span>
                  <input type="range" min="0" max={N_MONTHS} value={month} onChange={(e) => { setPlay(false); setMonth(+e.target.value); }} />
                </label>
              </div>
              <label>
                <span>Exaggerate movement <b>×{exag}</b></span>
                <input type="range" min="1" max="150" value={exag} onChange={(e) => setExag(+e.target.value)} />
              </label>
              <label className="check"><input type="checkbox" checked={ghost} onChange={(e) => setGhost(e.target.checked)} /> Show the temple at month 0, faint</label>
            </div>

            <h3>What KEYSTONE says</h3>
            <ul className="regions">
              {rows.map((r) => {
                const sev = month === 0 ? null : r.severity[month - 1];
                const v = month === 0 ? 0 : r.observed[month - 1];
                return (
                  <li key={r.id}>
                    <span className="rname">{prettyRegion(r.id)}</span>
                    <span className="rv">{v >= 0 ? "+" : ""}{v.toFixed(1)} mm</span>
                    <span className="chip" style={{ color: sev ? SEV_COLOUR[sev] : "#8b949b" }}>
                      {sev ? `${SEV_MARK[sev]} ${sev.toLowerCase()}` : "reference"}
                    </span>
                  </li>
                );
              })}
            </ul>

            <h3>Crack widths</h3>
            <ul className="cracks">
              {data.cracks.map((c) => (
                <li key={c.id}>
                  <span>{c.id}</span>
                  <span className="meter"><i style={{ width: `${Math.min(100, (c.width[month] / 8) * 100)}%` }} /></span>
                  <b>{c.width[month].toFixed(1)} mm</b>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </div>
    </section>
  );
}
