import type { Compound } from "./api/types";

// Real F1 tyre-compound color convention (soft=red, medium=yellow,
// hard=white, inter=green, wet=blue) - a widely-known public convention,
// not proprietary team livery. Single shared source of truth, reused by
// every component that shows a compound (previously duplicated only inside
// the now-removed TyreIcon.tsx).
export const COMPOUND_COLORS: Record<Compound, string> = {
  S: "#e10600",
  M: "#ffd400",
  H: "#f0f0f0",
  I: "#43b02a",
  W: "#0067ff",
};

export const COMPOUND_NAMES: Record<Compound, string> = {
  S: "Soft",
  M: "Medium",
  H: "Hard",
  I: "Intermediate",
  W: "Wet",
};
