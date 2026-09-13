import type { Compound } from "../api/types";
import { TYRE_CLIFF_LAP } from "../simConstants";
import { COMPOUND_COLORS } from "../tyreColors";

interface Props {
  compound: Compound;
  tyreAge: number;
}

// Horizontal tyre-life bar for the player panel. Wear-fraction estimate
// mirrors TyreIcon.tsx's old formula exactly (tyre_age / cliff_lap, clamped
// to 1) - a visual estimate only, not real simulation logic.
export function TyreDegradationBar({ compound, tyreAge }: Props) {
  const wearFraction = Math.min(1, tyreAge / TYRE_CLIFF_LAP[compound]);
  const lifeFraction = 1 - wearFraction;
  const lifePct = Math.round(lifeFraction * 100);

  return (
    <div className="db-tyre-bar">
      <div className="db-tyre-bar-track" role="img" aria-label={`Tyre life ${lifePct}%`}>
        <div
          className="db-tyre-bar-fill"
          style={{ width: `${lifePct}%`, backgroundColor: COMPOUND_COLORS[compound] }}
        />
      </div>
      <span className="db-tyre-bar-label">{lifePct}% life</span>
    </div>
  );
}
