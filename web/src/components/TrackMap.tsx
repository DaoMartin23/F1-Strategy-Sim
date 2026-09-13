import { useEffect, useRef, useState } from "react";
import { CarIcon } from "./CarIcon";
import { START_FINISH_POINT, TRACK_PATH_D, TRACK_VIEWBOX } from "../trackGeometry";

const CAR_COUNT = 20;

// Evenly spaced, maximally distinguishable hues - one per grid car.
function colorForCar(carIndex: number): string {
  const hue = (carIndex * 360) / CAR_COUNT;
  return `hsl(${hue.toFixed(0)}deg 70% 55%)`;
}

interface CarPosition {
  x: number;
  y: number;
  angle: number;
}

// Samples a point on the path plus a point a little further along, to
// derive a heading via atan2 - the standard technique for orienting an
// icon that follows an SVG path. Reused as-is by Stage 20b/20c once car
// positions come from real gap data instead of fixed demo fractions.
function positionAtFraction(path: SVGPathElement, totalLength: number, fraction: number): CarPosition {
  const wrapped = ((fraction % 1) + 1) % 1;
  const here = path.getPointAtLength(wrapped * totalLength);
  const aheadFraction = ((wrapped + 0.004) % 1) * totalLength;
  const ahead = path.getPointAtLength(aheadFraction);
  const headingDeg = (Math.atan2(ahead.y - here.y, ahead.x - here.x) * 180) / Math.PI + 90;
  return { x: here.x, y: here.y, angle: headingDeg };
}

export function TrackMap() {
  const pathRef = useRef<SVGPathElement>(null);
  const [positions, setPositions] = useState<CarPosition[] | null>(null);

  useEffect(() => {
    const path = pathRef.current;
    if (path === null) {
      return;
    }
    const totalLength = path.getTotalLength();
    // Stage 20a demo only: fixed even spacing around the loop. Stage 20b
    // replaces this with real gap-based fractions from race state.
    const demoPositions = Array.from({ length: CAR_COUNT }, (_, i) =>
      positionAtFraction(path, totalLength, i / CAR_COUNT),
    );
    setPositions(demoPositions);
  }, []);

  return (
    <svg viewBox={TRACK_VIEWBOX} width="100%" role="img" aria-label="Track map">
      <rect width="1000" height="1000" fill="#0f2a1d" />
      <path ref={pathRef} d={TRACK_PATH_D} fill="none" stroke="#3a3a3a" strokeWidth={28} strokeLinejoin="round" />
      <path d={TRACK_PATH_D} fill="none" stroke="#6b6b6b" strokeWidth={26} strokeLinejoin="round" />
      <circle cx={START_FINISH_POINT.x} cy={START_FINISH_POINT.y} r={5} fill="#ffd400" />
      {positions?.map((pos, carIndex) => (
        <CarIcon
          key={carIndex}
          x={pos.x}
          y={pos.y}
          angle={pos.angle}
          color={colorForCar(carIndex)}
          highlight={carIndex === 0}
          scale={1.4}
        />
      ))}
    </svg>
  );
}
