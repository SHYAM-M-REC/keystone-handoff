import { data } from "../data/loader.js";

export default function Order() {
  const a = data.alerts.tower_upper.first;
  const no = `KS-${a.decided_on.replaceAll("-", "")}-T01`;
  return (
    <section className="section dark2" id="act">
      <div className="wrap split">
        <div>
          <h2 className="big">From alert to action</h2>
          <p className="sub">
            When something is serious KEYSTONE does not just colour a chart. It writes an inspection order for the right person, with the reason and the evidence
            behind it. It recommends. The custodian decides.
          </p>
          <ul className="routes">
            <li><b>Informational</b> goes to the monument record</li>
            <li><b>Watch</b> goes to the capture schedule: look again sooner</li>
            <li><b>Alert</b> goes to the regional office priority list</li>
            <li><b>Critical</b> goes to a structural engineer, with a site closure recommendation</li>
          </ul>
        </div>
        <article className="order" aria-label="Sample inspection order">
          <span className="stamp">simulated</span>
          <h3>Inspection order</h3>
          <dl>
            <div><dt>Order</dt><dd>{no}</dd></div>
            <div><dt>Date</dt><dd className="keep">{a.decided_on}</dd></div>
            <div><dt>Monument</dt><dd className="keep">M-02 (simulated temple)</dd></div>
            <div><dt>Region</dt><dd>{a.region.replace(/_/g, " ")}</dd></div>
            <div><dt>Level</dt><dd><b className="lvl">{a.severity}</b></dd></div>
            <div><dt>Sent to</dt><dd className="keep">{a.recipient[0].toUpperCase() + a.recipient.slice(1)}</dd></div>
            <div><dt>Compared</dt><dd className="keep">{a.reference} with {a.latest}</dd></div>
          </dl>
          <p className="why"><b>Why this was raised</b><br />{a.reason.split(". Recommend")[0].split(" Seasonal expectation")[0].replace(/[.;\s]+$/, "")}.</p>
          <div className="sign"><span>Reviewed by</span><i /><span>Date</span><i /></div>
          <p className="rec">KEYSTONE recommends. It has no authority to close a monument.</p>
        </article>
      </div>
    </section>
  );
}
