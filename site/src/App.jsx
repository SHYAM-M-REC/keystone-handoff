import { useState } from "react";
import Hero from "./components/Hero.jsx";
import Problem from "./components/Problem.jsx";
import Pipeline from "./components/Pipeline.jsx";
import Lab from "./components/Lab.jsx";
import Season from "./components/Season.jsx";
import Compare from "./components/Compare.jsx";
import Order from "./components/Order.jsx";
import Proof from "./components/Proof.jsx";
import Footer from "./components/Footer.jsx";
import { N_MONTHS } from "./data/loader.js";

export default function App() {
  const [month, setMonth] = useState(N_MONTHS);   // the lab starts at the end of the year
  return (
    <>
      <Hero />
      <main>
        <Problem />
        <Pipeline />
        <Lab month={month} setMonth={setMonth} />
        <Season month={month} />
        <Compare />
        <Order />
        <Proof />
      </main>
      <Footer />
    </>
  );
}
