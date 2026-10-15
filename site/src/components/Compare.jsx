import { data, SEV_COLOUR, SEV_MARK, prettyRegion } from "../data/loader.js";

const PLANTED = {
  tower_upper: "leans east",
  col_b_lower: "settles",
  lintel_upper: "sags with the column",
  plinth_lower: "sinks near the column",
  porch_roof_upper: "sags slightly",
};
const month = (m) => (m ? `month ${m}` : "never");

export default function Compare() {
  const rows = data.regions;
  const real = new Set(Object.keys(PLANTED));
  const falseK = rows.filter((r) => r.firstAlert && !real.has(r.id));
  const falseN = rows.filter((r) => r.naiveFirst && !real.has(r.id));
  return (
    <section className="section paper tight" id="compare">
      <div className="wrap">
        <h3 className="mid">Head to head, one simulated year</h3>
        <div className="table-wrap">
          <table className="cmp">
            <thead><tr><th>Region</th><th>Planted</th><th>KEYSTONE first alert</th><th>Fixed threshold first fires</th><th>KEYSTONE at month 12</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={real.has(r.id) ? "real" : ""}>
                  <td>{prettyRegion(r.id)}</td>
                  <td>{PLANTED[r.id] ?? "nothing"}</td>
                  <td>{month(r.firstAlert)}</td>
                  <td>{month(r.naiveFirst)}</td>
                  <td style={{ color: SEV_COLOUR[r.severity[11]] }}>{SEV_MARK[r.severity[11]]} {r.severity[11].toLowerCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="honest">
          <b>Honest note.</b>{" "}
          {falseK.length > 0 && <>KEYSTONE raised a false alert on {falseK.map((r) => `${prettyRegion(r.id)} (month ${r.firstAlert})`).join(", ")}: the settling column is one of only a few regions at that height, so early on it pulls the seasonal estimate. It cleared itself later. </>}
          {falseN.length > 0 && <>The fixed threshold gave a false alarm on {falseN.map((r) => prettyRegion(r.id)).join(", ")}. </>}
          The fixed threshold never fires on the beam or the plinth. KEYSTONE catches them because a steady trend and widening cracks count as evidence.
        </div>
      </div>
    </section>
  );
}
