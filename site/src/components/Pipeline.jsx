import { Camera, Cube, Delta, Crack, Wave, Bell } from "./icons.jsx";

const steps = [
  { i: <Camera />, h: "Check the photos", p: "A phone or low-cost drone takes the pictures. A quality gate checks they are sharp, cover the whole structure and show the scale markers, and says where to reshoot." },
  { i: <Cube />, h: "Build a scaled 3D model", p: "Markers at surveyed positions fix true size, so every visit lands in the same frame and the numbers are in millimetres." },
  { i: <Delta />, h: "Find what moved", p: "Two visits are aligned and every region is measured. Each point carries its own noise limit, so small shifts are never mistaken for movement." },
  { i: <Crack />, h: "Watch the cracks", p: "A U-Net measures crack width in photos. Widening counts as separate evidence, not just a picture." },
  { i: <Wave />, h: "Season or damage?", p: "Heat and rain move stone. KEYSTONE learns what normal looks like from the monument's own regions, and only movement beyond it that stays beyond it counts." },
  { i: <Bell />, h: "Act and record", p: "Four levels, from informational to critical. A printable inspection order goes to the right person, and every capture is archived with an integrity check." },
];

export default function Pipeline() {
  return (
    <section className="section paper" id="how">
      <div className="wrap">
        <h2 className="big">Six steps, no one in the loop to interpret.</h2>
        <p className="sub">Every visit runs the same chain. The code behind this page is the project's real pipeline.</p>
        <ol className="steps">
          {steps.map((s, k) => (
            <li key={s.h}>
              <div className="ico">{s.i}</div>
              <h3>{s.h}</h3>
              <p>{s.p}</p>
              {k < steps.length - 1 && <span className="join" aria-hidden="true" />}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
