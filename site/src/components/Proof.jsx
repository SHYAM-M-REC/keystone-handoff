import { Check, Open } from "./icons.jsx";

const proven = [
  "The whole chain runs end to end, from capture check to inspection order.",
  "A planted 12 mm movement on a simulated wall was measured as 11.8 mm.",
  "In a simulated year the tower lean was flagged at month 7. A fixed threshold needed until month 10.",
  "A control crack that never changes stayed quiet all year.",
  "Two automatic test suites pass (32 and 22 checks).",
];
const open = [
  "Nothing has been tested on a real monument yet. All data on this page is simulated, with known truth.",
  "The 1 to 3 cm accuracy is a claim until one real capture with printed scale markers is measured.",
  "The crack model was trained on concrete: overlap score 0.65 there, 0.455 on brick.",
  "In the simulated year KEYSTONE raised one false alert on a neighbouring column. The cause is understood, the fix is not built.",
  "Photo-only reconstruction gives a sparse skeleton; dense, textured models need a GPU.",
];

export default function Proof() {
  return (
    <section className="section dark" id="proof">
      <div className="wrap">
        <h2 className="big">What is proven, and what is not</h2>
        <div className="proof">
          <div>
            <h3>Shown, on simulated data</h3>
            <ul>{proven.map((t) => <li key={t}><span className="ok"><Check /></span>{t}</li>)}</ul>
          </div>
          <div>
            <h3>Still open</h3>
            <ul>{open.map((t) => <li key={t}><span className="no"><Open /></span>{t}</li>)}</ul>
          </div>
        </div>
        <div className="next">
          <h3>Next</h3>
          <p>
            One real wall or monument, printed scale markers in view, a deliberate and measured change between two visits.
            Run both through the chain and report the real error. That test decides whether the numbers hold.
          </p>
        </div>
      </div>
    </section>
  );
}
