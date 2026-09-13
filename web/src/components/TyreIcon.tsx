import type { Compound } from "../api/types";
import { TYRE_CLIFF_LAP } from "../simConstants";

interface Props {
  compound: Compound;
  tyreAge: number;
  size?: number;
}

// Real F1 tyre-compound color convention (soft=red, medium=yellow,
// hard=white, inter=green, wet=blue) - a widely-known public convention,
// not proprietary team livery.
const COMPOUND_COLORS: Record<Compound, string> = {
  S: "#e10600",
  M: "#ffd400",
  H: "#f0f0f0",
  I: "#43b02a",
  W: "#0067ff",
};

export function TyreIcon({ compound, tyreAge, size = 32 }: Props) {
  const wearFraction = Math.min(1, tyreAge / TYRE_CLIFF_LAP[compound]);
  const freshFraction = 1 - wearFraction;
  const center = size / 2;
  const radius = size / 2 - 3;
  const circumference = 2 * Math.PI * radius;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`${compound} tyre, ${Math.round(wearFraction * 100)}% worn`}
    >
      <circle cx={center} cy={center} r={radius} fill="none" stroke="#333" strokeWidth={4} />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={COMPOUND_COLORS[compound]}
        strokeWidth={4}
        strokeDasharray={`${circumference * freshFraction} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${center} ${center})`}
      />
      <text x={center} y={center + size * 0.14} textAnchor="middle" fontSize={size * 0.4} fill="#fff">
        {compound}
      </text>
    </svg>
  );
}
