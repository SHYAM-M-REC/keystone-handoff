import { useState } from "react";
import { data, SEV_COLOUR, SEV_MARK, prettyRegion } from "../data/loader.js";

const PICK = ["tower_upper", "col_b_lower", "lintel_upper", "plinth_lower", "cella_east_upper"];
const PLANTED = {
  tower_upper: "The tower leans east from month 2.",
  col_b_lower: "This column settles into soft ground from month 4.",
  lintel_upper: "The beam above that column sags with it.",
  plinth_lower: "The plinth sinks near the column.",
  cella_east_upper: "Nothing is planted here. It only breathes with the weather.",
  cella_front_upper: "Nothing is planted here.",
};

const W = 760, H = 340, L = 52, R = 18, T = 20, B = 40;

function Chart({ r, month }) {
  const xs = (i) => L + ((i - 1) / 11) * (W - L - R);
  const lo = r.expected.map((e, i) => e - 2 * r.sigma[i]);
  const hi = r.expected.map((e, i) => e + 2 * r.sigma[i]);
  const all = [...r.observed, ...lo, ...hi, 2 * r.lod, -2 * r.lod];
  const ymin = Math.floor(Math.min(...all) - 1), ymax = Math.ceil(Math.max(...all) + 1);
  const ys = (v) => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B);
  const pts = (arr) => arr.map((v, i) => `${xs(i + 1)},${ys(v)}`).join(" ");
  const band = `${hi.map((v, i) => `${xs(i + 1)},${ys(v)}`).join(" ")} ${lo.map((v, i) => `${xs(12 - i)},${ys(lo[11 - i])}`).join(" ")}`;
  const ticks = [];
  const step = (ymax - ymin) > 30 ? 10 : 5;
  for (let v = Math.ceil(ymin / step) * step; v <= ymax; v += step) ticks.push(v);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={`Movement of ${prettyRegion(r.id)} against the seasonal band`}>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={ys(v)} y2={ys(v)} className="gridline" />
          <text x={L - 8} y={ys(v) + 4} textAnchor="end" className="axis">{v}</text>
        </g>
      ))}
      <text x={12} y={T + 4} className="axis">mm</text>
      {Array.from({ length: 12 }, (_, i) => (
        <text key={i} x={xs(i + 1)} y={H - 14} textAnchor="middle" className="axis">{i + 1}</text>
      ))}
      <text x={(L + W - R) / 2} y={H - 0} textAnchor="middle" className="axis">month since the reference capture</text>

      <polygon points={band} className="band" />
      <polyline points={pts(r.expected)} className="expected" />
      {[2 * r.lod, -2 * r.lod].map((v) => <line key={v} x1={L} x2={W - R} y1={ys(v)} y2={ys(v)} className="naive" />)}

      {r.naiveFirst && (
        <g>
          <line x1={xs(r.naiveFirst)} x2={xs(r.naiveFirst)} y1={T} y2={H - B} className="mk naivemk" />
          <text x={xs(r.naiveFirst) + 6} y={T + 12} className="mklabel naivelabel">fixed threshold fires</text>
        </g>
      )}
      {r.firstAlert && (
        <g>
          <line x1={xs(r.firstAlert)} x2={xs(r.firstAlert)} y1={T} y2={H - B} className="mk" />
          <text x={xs(r.firstAlert) - 6} y={T + 14} textAnchor={r.firstAlert > 8 ? "end" : "start"} className="mklabel">KEYSTONE alerts</text>
        </g>
      )}
      {month > 0 && <line x1={xs(month)} x2={xs(month)} y1={T} y2={H - B} className="cursor" />}
      <polyline points={pts(r.observed)} className="observed" />
      {r.observed.map((v, i) => (
        <circle key={i} cx={xs(i + 1)} cy={ys(v)} r={i + 1 === month ? 6 : 4} fill={SEV_COLOUR[r.severity[i]]} className="dot" />
      ))}
    </svg>
  );
}

export default function Season({ month }) {
  const [pick, setPick] = useState("tower_upper");
  const r = data.regions.find((x) => x.id === pick);
  const fa = r.firstAlert, nf = r.naiveFirst;
  return (
    <section className="section paper" id="season">
      <div className="wrap">
        <h2 className="big">Season, or damage?</h2>
        <p className="sub">
          Stone breathes with heat and rain. The shaded band is what the weather explains for this region, learned from the other regions
          at the same height. <b>Inside the band it is the season. Outside it, and staying outside, is the structure.</b>
        </p>
        <div className="tabs" role="tablist">
          {PICK.map((id) => (
            <button key={id} role="tab" aria-selected={pick === id} className={pick === id ? "on" : ""} onClick={() => setPick(id)}>{prettyRegion(id)}</button>
          ))}
        </div>
        <div className="season">
          <div className="chart-card">
            <Chart r={r} month={month} />
            <ul className="key">
              <li><i className="k-obs" /> measured movement (dot colour = KEYSTONE level)</li>
              <li><i className="k-band" /> what the weather explains</li>
              <li><i className="k-naive" /> a fixed threshold (2× the noise limit)</li>
            </ul>
          </div>
          <div className="verdict">
            <p className="planted">{PLANTED[pick] ?? ""}</p>
            <dl>
              <div><dt>KEYSTONE</dt><dd>{fa ? <>first alert in <b>month {fa}</b></> : <>never alerts</>}</dd></div>
              <div><dt>Fixed threshold</dt><dd>{nf ? <>first fires in <b>month {nf}</b></> : <>never fires</>}</dd></div>
              <div><dt>At month 12</dt><dd className="cap" style={{ color: SEV_COLOUR[r.severity[11]] }}>{SEV_MARK[r.severity[11]]} {r.severity[11].toLowerCase()}</dd></div>
            </dl>
            <p className="fine">The month marker follows the slider in the temple lab above.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
