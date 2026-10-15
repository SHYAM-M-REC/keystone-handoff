const stats = [
  { n: "3,698", t: "protected monuments in India" },
  { n: "92", t: "of the 1,655 inspected could not be traced" },
  { n: "546", t: "encroachments found, against 249 reported" },
];
export default function Problem() {
  return (
    <section className="section dark2" id="problem">
      <div className="wrap">
        <h2 className="big">A clipboard cannot watch a monument.</h2>
        <p className="sub">
          A government audit (CAG) found no complete physical survey of India's protected monuments since Independence.
          Damage is found late, by a person walking around, and a fixed alarm cannot tell a hot day from a failing wall.
        </p>
        <ul className="stats">
          {stats.map((s) => (
            <li key={s.n}><b>{s.n}</b><span>{s.t}</span></li>
          ))}
        </ul>
      </div>
    </section>
  );
}
