// A stylized, hand-tuned closed track shape tracing Silverstone's real
// corner-by-corner layout (per a reference circuit diagram: 18 numbered
// corners, sector boundaries, DRS zones) - not licensed/precise geometry,
// but every corner below corresponds to the matching numbered corner in
// that diagram, in order, rather than an abstract "evokes a track" shape.
//
// This is built from an ordered waypoint list run through a Catmull-Rom
// spline (below), NOT the single-valued-polar-function technique used
// earlier in the project. That technique (every angle from a fixed center
// maps to exactly one point) guarantees non-self-intersection by
// construction, but cannot represent this track at all: turns 6/7/8 form a
// tight hook where the path curls back on itself, and checking each
// point's angle from any plausible center shows it genuinely reversing
// direction across that hook - a hard topological mismatch, not a tuning
// problem. So this shape instead uses plain ordered waypoints (closer to
// the project's very first track-shape attempts) plus an explicit
// automated check (see the redesign commit message) that no two
// non-adjacent sampled segments of the finished path cross, run before
// this shape was accepted - since there's no more guarantee-by-construction
// to rely on.

import type { CarState } from "./api/types";

export const TRACK_WIDTH = 1200;
export const TRACK_HEIGHT = 750;
export const TRACK_VIEWBOX = `0 0 ${TRACK_WIDTH} ${TRACK_HEIGHT}`;

interface Point {
  x: number;
  y: number;
}

// Hand-placed waypoints digitized from the reference circuit diagram, in
// corner order (18 -> 17 -> ... -> 1 -> back to the start/finish near 18).
// "mid*"/"*_straight_mid" entries aren't real corners - they're extra
// collinear-ish points along the long straights so the Catmull-Rom fit
// doesn't bow them into a curve (a straight edge needs more than two points
// to stay straight under spline interpolation). Verified via a throwaway
// Python prototype rendered to PNG and compared against the reference image
// before porting here - see the redesign commit message.
const NAMED_WAYPOINTS: [name: string, x: number, y: number][] = [
  ["start_finish", 559.4, 162.5],
  ["turn18", 468.8, 115.6],
  ["turn17", 359.4, 181.3],
  ["turn16", 375.0, 221.9],
  ["turn15", 209.4, 387.5],
  ["back_straight_mid1", 318.8, 462.5],
  ["back_straight_mid2", 443.8, 546.9],
  ["turn14", 593.8, 625.0],
  ["turn13", 665.6, 693.8],
  ["turn12", 737.5, 665.6],
  ["turn11", 812.5, 681.3],
  ["turn10", 853.1, 609.4],
  ["sector2_straight_mid", 1006.3, 587.5],
  ["turn9", 1159.4, 565.6],
  ["turn8", 1116.3, 261.9],
  ["turn7", 887.5, 200.0],
  ["turn6", 1003.8, 313.1],
  ["turn5", 778.1, 562.5],
  ["turn4", 665.6, 562.5],
  ["turn3", 734.4, 490.6],
  ["turn2", 653.1, 415.6],
  ["turn1", 703.1, 300.0],
];

const VERTICES: Point[] = NAMED_WAYPOINTS.map(([, x, y]) => ({ x, y }));

function catmullRomToBezierPath(points: Point[]): string {
  const n = points.length;
  const at = (i: number) => points[((i % n) + n) % n];
  const parts: string[] = [`M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`];
  for (let i = 0; i < n; i++) {
    const p0 = at(i - 1);
    const p1 = at(i);
    const p2 = at(i + 1);
    const p3 = at(i + 2);
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    parts.push(
      `C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`,
    );
  }
  parts.push("Z");
  return parts.join(" ");
}

export const TRACK_PATH_D = catmullRomToBezierPath(VERTICES);

// The "start_finish" waypoint itself - vertex 0 above.
export const START_FINISH_POINT: Point = VERTICES[0];

export interface TrackMarker {
  x: number;
  y: number;
  /** Degrees, in the same "0 = pointing up, clockwise-positive" convention TrackMap.tsx already uses for car headings (atan2 + 90). */
  headingDeg: number;
}

// Heading at vertex i via the same tangent direction the Catmull-Rom fit
// above already uses for that vertex ((p[i+1] - p[i-1]), see c1x/c1y) - so
// markers drawn with this heading sit flush with the actual curve there,
// not just the straight line between neighboring vertices.
function headingAt(index: number): number {
  const n = VERTICES.length;
  const prev = VERTICES[(index - 1 + n) % n];
  const next = VERTICES[(index + 1) % n];
  return (Math.atan2(next.y - prev.y, next.x - prev.x) * 180) / Math.PI + 90;
}

export const START_FINISH_HEADING_DEG = headingAt(0);

// One marker per real numbered corner (the "turnN" waypoints - excludes the
// "*_mid*" helper points along the straights, which aren't corners) for
// TrackMap.tsx to draw small red/white curb detailing at.
export const CORNER_MARKERS: TrackMarker[] = NAMED_WAYPOINTS.flatMap(([name, x, y], index) =>
  name.startsWith("turn") ? [{ x, y, headingDeg: headingAt(index) }] : [],
);

// Mirrors TRACKS["silverstone"]["base_lap_time"] in sim/model.py - used only
// as a fallback before any lap has completed (state.lap === 0), when there's
// no real average pace to estimate from yet.
const FALLBACK_LAP_TIME_SECONDS = 91.5;

export interface CarTrackFraction {
  id: number;
  /** 0..1 fraction of the way around the loop; the leader sits at 0. */
  fraction: number;
  retired: boolean;
}

interface GapEntry {
  id: number;
  totalTime: number;
  retired: boolean;
}

// Core gap -> track-fraction math, shared by the static (Stage 20b) and
// animated (Stage 20c) call sites below. The leader is pinned at fraction 0
// (there's no real sub-lap progress data to place them more precisely -
// this represents one instant, not yet knowing "how far into the current
// lap" anyone is); every other car sits behind that by its gap, expressed
// as a fraction of the estimated average lap time, wrapped mod 1 so a car a
// full lap or more down still renders at a sensible on-track position
// (it'll coincidentally land near the leader again, which is exactly how
// being lapped looks on a real track map).
function computeGapFractions(entries: GapEntry[], lap: number): Map<number, number> {
  const active = entries.filter((entry) => !entry.retired);
  const leaderTotalTime = active.length > 0 ? Math.min(...active.map((entry) => entry.totalTime)) : 0;
  const avgLapTime = lap > 0 && leaderTotalTime > 0 ? leaderTotalTime / lap : FALLBACK_LAP_TIME_SECONDS;

  const result = new Map<number, number>();
  for (const entry of entries) {
    const gapSeconds = entry.totalTime - leaderTotalTime;
    const gapFraction = gapSeconds / avgLapTime;
    result.set(entry.id, ((-gapFraction % 1) + 1) % 1);
  }
  return result;
}

// Static snapshot from a full race State (Stage 20b - the "resting" display
// between animations, and the very first render before any lap has been
// animated through).
export function computeTrackFractions(cars: CarState[], lap: number): CarTrackFraction[] {
  const entries = cars.map((car) => ({ id: car.id, totalTime: car.total_time, retired: car.retired_lap !== null }));
  const fractions = computeGapFractions(entries, lap);
  return cars.map((car) => ({ id: car.id, fraction: fractions.get(car.id) ?? 0, retired: car.retired_lap !== null }));
}

// Per-tick animated positions (Stage 20c) from one LapTrace entry.
// animationProgress runs 0..1 over the tick's fixed duration; adding it to
// the same static fraction formula above is enough to make the leader
// complete exactly one full loop over the tick while every other car
// maintains its gap-based offset throughout - see the Stage 20c commit
// message for the short derivation of why plain addition (mod 1) is
// equivalent to re-deriving "(animationProgress - gapFraction) mod 1" from
// scratch.
export function computeAnimatedFractions(
  carLaps: { id: number; total_time: number }[],
  lap: number,
  retiredIds: ReadonlySet<number>,
  animationProgress: number,
): Map<number, number> {
  const entries = carLaps.map((car) => ({ id: car.id, totalTime: car.total_time, retired: retiredIds.has(car.id) }));
  const staticFractions = computeGapFractions(entries, lap);
  const result = new Map<number, number>();
  // animationProgress is always in [0, 1] and staticFraction always in
  // [0, 1), so their sum is always in [0, 2) - a plain modulo is enough,
  // no negative-wraparound handling needed here.
  for (const [id, staticFraction] of staticFractions) {
    result.set(id, (animationProgress + staticFraction) % 1);
  }
  return result;
}
