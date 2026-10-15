"""Export the simulated temple year to one JSON file for the React site (site/src/data/temple.json).

    python tools/export_site_data.py site/src/data/temple.json

Everything is SIMULATED (console/monument.py); the alerts come from the real Decision code.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from console import monument as M  # noqa: E402

GAP_EXAG = 40.0


def b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


def main(out: str) -> None:
    tp = M.build_temple(0)
    res = M.run_year(tp, 0)
    months = []
    cracks = [dict(id=c["id"], region=c["region"], width=[], label=[]) for c in tp.cracks]
    for m in range(M.N_MONTHS + 1):
        st = M.month_state(tp, m, 0)
        rm, patch, inside = M.crack_patches(tp, st, GAP_EXAG)
        keep = ~rm
        pos = np.vstack([tp.points[keep], patch["pos"], inside["pos"]])
        disp = np.vstack([st.disp[keep], patch["disp"], inside["disp"]])
        meas = np.concatenate([st.measured[keep], patch["measured"], np.zeros(len(inside["pos"]))])
        kind = np.concatenate([st.significant[keep].astype(np.uint8), patch["sig"].astype(np.uint8),
                               np.full(len(inside["pos"]), 2, np.uint8)])
        months.append(dict(
            n=int(len(pos)),
            pos=b64(np.round(pos * 2).astype(np.int16)),             # 0.5 mm units
            disp=b64(np.round(disp * 100).astype(np.int16)),         # 0.01 mm units
            q=b64(np.clip(np.round(meas * 5), -127, 127).astype(np.int8)),   # 0.2 mm units
            kind=b64(kind)))
        for c, cs in zip(cracks, st.cracks):
            end = cs["poly"][-1] + 0.0
            c["width"].append(round(float(cs["width"]), 2))
            c["label"].append([round(float(v), 1) for v in end])
            c.setdefault("poly", []).append([[round(float(v), 1) for v in p] for p in cs["poly"]])
            c.setdefault("cdisp", []).append([[round(float(v), 2) for v in p] for p in cs["disp"]])

    last = res.analyses[-1]
    regions = []
    for ra in last:
        rid = ra.region_id
        r = ra.residuals
        regions.append(dict(
            id=rid, loadBearing=bool(ra.load_bearing), lod=round(tp.lod[rid], 2),
            observed=[round(float(v), 2) for v in res.series[rid]],
            expected=[round(float(v), 2) for v in r.expected],
            sigma=[round(float(v), 2) for v in r.sigma],
            severity=res.severity[rid],
            firstAlert=res.first_alert[rid], naiveFirst=res.naive_first[rid]))

    def alert_dict(a):
        return dict(region=a.region_id, severity=a.severity, recipient=a.recipient, reason=a.reason,
                    reference=a.reference_capture_id, latest=a.latest_capture_id, decided_on=a.decided_on)

    alerts = {}
    for rid in ("tower_upper", "col_b_lower", "lintel_upper", "plinth_lower"):
        k = res.first_alert[rid]
        if k:
            alerts[rid] = dict(first=alert_dict(next(x.alert for x in res.analyses[k - 1] if x.region_id == rid)),
                               final=alert_dict(next(x.alert for x in last if x.region_id == rid)))

    data = dict(
        simulated=True, gapExag=GAP_EXAG, dates=tp.dates, nPoints=int(len(tp.points)),
        months=months, cracks=cracks, regions=regions, alerts=alerts,
        crackSeries={k: [round(v, 2) for v in vs] for k, vs in res.crack_series.items()})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {out}: {Path(out).stat().st_size / 1e6:.1f} MB, {len(months)} months, "
          f"{sum(m['n'] for m in months) // len(months)} points per month")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "site" / "src" / "data" / "temple.json"))
