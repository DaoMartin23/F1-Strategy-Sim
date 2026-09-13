import { useEffect, useRef, useState } from "react";
import { CarIcon } from "./CarIcon";
import {
  CORNER_MARKERS,
  computeAnimatedFractions,
  START_FINISH_HEADING_DEG,
  START_FINISH_POINT,
  TRACK_HEIGHT,
  TRACK_PATH_D,
  TRACK_VIEWBOX,
  TRACK_WIDTH,
  type TrackMarker,
} from "../trackGeometry";

const CAR_COUNT = 20;

// Half the road's drawn stroke width (see the two <path> strokeWidths
// below) - reused so the checkered line/curbs line up with the road's
// actual edges instead of a separately-guessed number.
const ROAD_HALF_WIDTH = 14;

// A black/white checkered strip across the road at the start/finish line,
// oriented perpendicular to the track direction there.
function CheckeredLine({ x, y, headingDeg }: TrackMarker) {
  const squareCount = 8;
  const squareWidth = (ROAD_HALF_WIDTH * 2) / squareCount;
  return (
    <g transform={`translate(${x} ${y}) rotate(${headingDeg})`}>
      {Array.from({ length: squareCount }, (_, i) => (
        <rect
          key={i}
          x={-ROAD_HALF_WIDTH + i * squareWidth}
          y={-3}
          width={squareWidth}
          height={6}
          fill={i % 2 === 0 ? "#111" : "#f5f5f5"}
        />
      ))}
    </g>
  );
}

// Small red/white curb detailing on both edges of the road at a corner
// apex, oriented along the track direction there.
function CornerCurb({ x, y, headingDeg }: TrackMarker) {
  const stripeCount = 3;
  const stripeLength = 4;
  const stripes = (side: -1 | 1) =>
    Array.from({ length: stripeCount }, (_, i) => (
      <rect
        key={i}
        x={side * ROAD_HALF_WIDTH - 2}
        y={-stripeLength * 1.5 + i * stripeLength}
        width={4}
        height={stripeLength}
        fill={i % 2 === 0 ? "#c81e1e" : "#f5f5f5"}
      />
    ));
  return (
    <g transform={`translate(${x} ${y}) rotate(${headingDeg})`}>
      {stripes(-1)}
      {stripes(1)}
    </g>
  );
}

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
// icon that follows an SVG path.
function positionAtFraction(path: SVGPathElement, totalLength: number, fraction: number): CarPosition {
  const wrapped = ((fraction % 1) + 1) % 1;
  const here = path.getPointAtLength(wrapped * totalLength);
  const aheadFraction = ((wrapped + 0.004) % 1) * totalLength;
  const ahead = path.getPointAtLength(aheadFraction);
  const headingDeg = (Math.atan2(ahead.y - here.y, ahead.x - here.x) * 180) / Math.PI + 90;
  return { x: here.x, y: here.y, angle: headingDeg };
}

interface Props {
  /** Whichever cars' total_time should drive this frame's positions - either
   * a resting State's cars, or one LapTrace entry's cars mid-animation. */
  cars: { id: number; total_time: number }[];
  lap: number;
  retiredIds: ReadonlySet<number>;
  /** 0 for a resting/static display; 0..1 while mid-tick-animation. */
  animationProgress: number;
}

export function TrackMap({ cars, lap, retiredIds, animationProgress }: Props) {
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

  const fractions = computeAnimatedFractions(cars, lap, retiredIds, animationProgress);

  return (
    <svg viewBox={TRACK_VIEWBOX} width="100%" role="img" aria-label="Track map">
      <rect width={TRACK_WIDTH} height={TRACK_HEIGHT} fill="#0f2a1d" />
      <path ref={pathRef} d={TRACK_PATH_D} fill="none" stroke="#3a3a3a" strokeWidth={28} strokeLinejoin="round" />
      <path d={TRACK_PATH_D} fill="none" stroke="#6b6b6b" strokeWidth={26} strokeLinejoin="round" />
      {CORNER_MARKERS.map((marker, i) => (
        <CornerCurb key={i} {...marker} />
      ))}
      <CheckeredLine x={START_FINISH_POINT.x} y={START_FINISH_POINT.y} headingDeg={START_FINISH_HEADING_DEG} />
      {totalLength !== null &&
        pathElement !== null &&
        cars.map((car) => {
          const fraction = fractions.get(car.id);
          if (fraction === undefined) {
            return null;
          }
          const pos = positionAtFraction(pathElement, totalLength, fraction);
          return (
            <CarIcon
              key={car.id}
              x={pos.x}
              y={pos.y}
              angle={pos.angle}
              color={colorForCar(car.id)}
              highlight={car.id === 0}
              scale={1.4}
              opacity={retiredIds.has(car.id) ? 0.35 : 1}
            />
          );
        })}
    </svg>
  );
}
