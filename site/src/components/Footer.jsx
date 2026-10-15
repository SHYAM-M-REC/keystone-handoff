import { Logo } from "./icons.jsx";
import { config } from "../config.js";

export default function Footer() {
  const { repository, video } = config.links;
  return (
    <footer className="footer">
      <div className="wrap foot">
        <div>
          <a className="brand" href="#top"><Logo size={26} /> <span>KEYSTONE</span></a>
          <p>A monument that measures itself, and raises its own alarm.</p>
        </div>
        <div className="foot-right">
          <p>{config.team} · {config.college}</p>
          <p>{config.event}</p>
          <p className="links">
            {repository && <a href={repository}>Repository</a>}
            {video && <a href={video}>Demo video</a>}
          </p>
        </div>
      </div>
    </footer>
  );
}
