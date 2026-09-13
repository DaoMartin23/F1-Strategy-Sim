interface Props {
  x: number;
  y: number;
  /** Heading in degrees; 0 = nose pointing "up" (north) in the SVG's local coordinates. */
  angle: number;
  color: string;
  highlight?: boolean;
  scale?: number;
}

// A small stylized top-down "model car" - not a photorealistic or
// team-liveried car (trademark-sensitive), just a clearly car-shaped icon:
// a tapered body, a cockpit, front/rear wings, and four wheel marks. Drawn
// in a local coordinate space with the nose at negative y, then translated
// and rotated into place by the caller.
export function CarIcon({ x, y, angle, color, highlight = false, scale = 1 }: Props) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`}>
      {highlight && (
        <rect x={-9} y={-15} width={18} height={28} rx={6} fill="none" stroke="#ffd400" strokeWidth={2.5} />
      )}
      {/* rear wing */}
      <rect x={-7} y={8} width={14} height={3} rx={1} fill="#111" />
      {/* body */}
      <path d="M 0 -13 L 6 -6 L 6 9 Q 6 12 0 12 Q -6 12 -6 9 L -6 -6 Z" fill={color} stroke="#111" strokeWidth={1} />
      {/* front wing */}
      <rect x={-8} y={-13} width={16} height={2.5} rx={1} fill="#111" />
      {/* cockpit */}
      <ellipse cx={0} cy={-2} rx={2.6} ry={4.5} fill="#111" opacity={0.75} />
      {/* wheels */}
      <rect x={-8.5} y={-8} width={3} height={5} rx={1} fill="#111" />
      <rect x={5.5} y={-8} width={3} height={5} rx={1} fill="#111" />
      <rect x={-8.5} y={4} width={3} height={5} rx={1} fill="#111" />
      <rect x={5.5} y={4} width={3} height={5} rx={1} fill="#111" />
    </g>
  );
}
