import { useEffect, useRef, useState } from "react";
import { CarIcon } from "./CarIcon";
import { computeTrackFractions, START_FINISH_POINT, TRACK_PATH_D, TRACK_VIEWBOX } from "../trackGeometry";
import type { State } from "../api/types";

const CAR_COUNT = 20;

// Evenly spaced, maximally distinguishable hues - one per grid car, keyed
// by the car's stable id (0-19), not its position in the array.
function colorForCar(carId: number): string {
  const hue = (carId * 360) / CAR_COUNT;
  return `hsl(${hue.toFixed(0)}deg 70% 55%)`;
}

interface CarPosition {
  x: number;
  y: number;
  angle: number;
}

// Samples a point on the path plus a point a little further along, to
// derive a heading via atan2 - the standard technique for orienting an
// icon that follows an SVG path. Reused as-is by Stage 20c once positions
// are animated instead of a static snapshot.
function positionAtFraction(path: SVGPathElement, totalLength: number, fraction: number): CarPosition {
  const wrapped = ((fraction % 1) + 1) % 1;
  const here = path.getPointAtLength(wrapped * totalLength);
  const aheadFraction = ((wrapped + 0.004) % 1) * totalLength;
  const ahead = path.getPointAtLength(aheadFraction);
  const headingDeg = (Math.atan2(ahead.y - here.y, ahead.x - here.x) * 180) / Math.PI + 90;
  return { x: here.x, y: here.y, angle: headingDeg };
}

interface Props {
  state: State;
}

export function TrackMap({ state }: Props) {
  const pathRef = useRef<SVGPathElement>(null);
  // Refs shouldn't be read during render (React rule - the ref might not
  // reflect the committed DOM yet); stash the element and its measured
  // length in state instead, set once after mount via the effect below.
  const [pathElement, setPathElement] = useState<SVGPathElement | null>(null);
  const [totalLength, setTotalLength] = useState<number | null>(null);

  useEffect(() => {
    const path = pathRef.current;
    if (path !== null) {
      setPathElement(path);
      setTotalLength(path.getTotalLength());
    }
  }, []);

  const fractions = computeTrackFractions(state.cars, state.lap);

  return (
    <svg viewBox={TRACK_VIEWBOX} width="100%" role="img" aria-label="Track map">
      <rect width="1000" height="1000" fill="#0f2a1d" />
      <path ref={pathRef} d={TRACK_PATH_D} fill="none" stroke="#3a3a3a" strokeWidth={28} strokeLinejoin="round" />
      <path d={TRACK_PATH_D} fill="none" stroke="#6b6b6b" strokeWidth={26} strokeLinejoin="round" />
      <circle cx={START_FINISH_POINT.x} cy={START_FINISH_POINT.y} r={5} fill="#ffd400" />
      {totalLength !== null &&
        pathElement !== null &&
        state.cars.map((car) => {
          const entry = fractions.find((f) => f.id === car.id);
          if (entry === undefined) {
            return null;
          }
          const pos = positionAtFraction(pathElement, totalLength, entry.fraction);
          return (
            <CarIcon
              key={car.id}
              x={pos.x}
              y={pos.y}
              angle={pos.angle}
              color={colorForCar(car.id)}
              highlight={car.id === 0}
              scale={1.4}
              opacity={entry.retired ? 0.35 : 1}
            />
          );
        })}
    </svg>
  );
}
