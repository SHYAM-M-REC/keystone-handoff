import raw from "./temple.json";

const decode = (b64, Type) => {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Type(u8.buffer);
};

const cache = new Map();

/** One month of the simulated temple: positions (0.5 mm units), displacement (0.01 mm), measured (0.2 mm), kind. */
export function getMonth(m) {
  if (!cache.has(m)) {
    const d = raw.months[m];
    cache.set(m, {
      n: d.n,
      pos: decode(d.pos, Int16Array),
      disp: decode(d.disp, Int16Array),
      q: decode(d.q, Int8Array),
      kind: decode(d.kind, Uint8Array),
    });
  }
  return cache.get(m);
}

export const maxPoints = Math.max(...raw.months.map((m) => m.n));
export const data = raw;
export const N_MONTHS = raw.months.length - 1;

export const SEV_COLOUR = { INFORMATIONAL: "#5FAE8B", WATCH: "#D9A441", ALERT: "#E0702F", CRITICAL: "#D6403A" };
export const SEV_MARK = { INFORMATIONAL: "●", WATCH: "▲", ALERT: "◆", CRITICAL: "■" };
export const prettyRegion = (id) => id.replace(/_/g, " ");
