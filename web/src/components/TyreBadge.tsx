import type { Compound } from "../api/types";
import { COMPOUND_COLORS, COMPOUND_NAMES } from "../tyreColors";

interface Props {
  compound: Compound;
  size?: number;
}

// A compact colored compound indicator - just the compound, no wear info
// (that's TyreDegradationBar's job, for the player panel specifically).
// Used in the leaderboard and rival panel where space is tight.
export function TyreBadge({ compound, size = 22 }: Props) {
  return (
    <span
      className="db-tyre-badge"
      style={{ width: size, height: size, fontSize: size * 0.52, backgroundColor: COMPOUND_COLORS[compound] }}
      title={COMPOUND_NAMES[compound]}
    >
      {compound}
    </span>
  );
}
