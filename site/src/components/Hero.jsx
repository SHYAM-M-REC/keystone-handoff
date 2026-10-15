import { useEffect, useState } from "react";
import Scene from "./Scene.jsx";
import { Logo } from "./icons.jsx";
import { config } from "../config.js";
import { data, N_MONTHS } from "../data/loader.js";

export default function Hero() {
  const [month, setMonth] = useState(0);
  useEffect(() => {
    // plays the simulated year on a loop: 0..12, hold, restart
    let m = 0;
    const id = setInterval(() => { m = (m + 1) % (N_MONTHS + 4); setMonth(Math.min(m, N_MONTHS)); }, 1000);
    return () => clearInterval(id);
  }, []);

  const tower = data.cracks.find((c) => c.id === "tower crack");
  return (
    <header className="hero" id="top">
      <div className="hero-scene" aria-hidden="true">
        <Scene month={month} exag={55} autoRotate interactive={false} pointSize={0.06} distance={0.95} shiftX={0.2} />
      </div>
      <div className="hero-shade" />
      <nav className="nav">
        <a className="brand" href="#top"><Logo /> <span>KEYSTONE</span></a>
        <div className="nav-links">
          <a href="#how">How it works</a>
          <a href="#lab">Temple lab</a>
          <a href="#season">Season or damage</a>
          <a href="#proof">What is proven</a>
        </div>
      </nav>
      <div className="hero-copy">
        <p className="kicker">{config.event} · {config.team}</p>
        <h1>KEYSTONE</h1>
        <p className="tagline">A monument that measures itself, and raises its own alarm.</p>
        <p className="lede">
          Photograph a heritage structure again and again. KEYSTONE builds a scaled 3D model, finds what really moved,
          tells the season from the damage, and sends the right person an inspection order.
        </p>
        <div className="cta">
          <a className="btn primary" href="#lab">Watch a simulated year</a>
          <a className="btn" href="#how">How it works</a>
        </div>
      </div>
      <div className="hero-ticker" role="status">
        <div className="ticks">
          {Array.from({ length: N_MONTHS + 1 }, (_, i) => <i key={i} className={i <= month ? "on" : ""} />)}
        </div>
        <p>
          <b>Simulated temple</b> · month {month} of {N_MONTHS}
          {month > 0 && <> · tower crack {tower.width[month].toFixed(1)} mm</>}
        </p>
      </div>
    </header>
  );
}
