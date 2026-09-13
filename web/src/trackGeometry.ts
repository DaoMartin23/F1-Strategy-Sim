// A stylized, hand-tuned closed track shape - NOT a licensed/precise trace
// of Silverstone's real geometry (confirmed with the user as an acceptable
// approximation). Built from a small set of hand-placed vertices at
// strictly ascending angles around a fixed center, connected by exactly
// straight edges (via the standard point-normal line formula expressed in
// polar form), with each corner rounded off by blending the two adjacent
// straight-edge formulas over a small angular window. Because every vertex
// angle is strictly ascending by construction, the result is guaranteed
// star-shaped/non-self-intersecting - the same guarantee the original
// sine-sum curve relied on, just built from straight edges instead of
// smooth waves so it actually reads as straights + corners rather than a
// wobbly blob (an earlier, freehand-Cartesian-vertex version of this same
// approach briefly reintroduced self-intersection risk: hand-placing
// vertices by eye doesn't guarantee their angle-from-center comes out
// ascending, which a chicane-like detour violated - fixed by defining
// vertices directly as (angle, radius) pairs instead).
//
// One long back straight opposite a tighter, more technical infield corner
// sequence evokes Silverstone's real silhouette without tracing its actual
// corner-by-corner layout.

import type { CarState } from "./api/types";

export const TRACK_VIEWBOX = "0 0 1000 1000";

interface Point {
  x: number;
  y: number;
}

const CENTER: Point = { x: 500, y: 480 };
const SAMPLE_COUNT = 300;

// (angle in degrees, radius) pairs, strictly ascending angle. Every
// consecutive pair becomes an exactly straight edge; a long gap between two
// vertices' angles reads as a long straight (e.g. 5->6, the back straight),
// while several close-together vertices with tight radii read as a
// technical corner sequence (2/3/4, the infield hairpin).
const VERTEX_POLAR: [angleDeg: number, radius: number][] = [
  [0, 290], // 0: start/finish
  [35, 310], // 1: end of the pit straight, into turn 1's braking zone
  [72, 175], // 2: tightening right-hander
  [108, 130], // 3: tight hairpin-like bottom of the infield
  [145, 220], // 4: opening back up
  [183, 350], // 5: start of the long back straight (far side)
  [232, 385], // 6: end of the long back straight
  [266, 235], // 7: fast sweeping corner complex begins
  [298, 185], // 8: esses continue, tightening
  [333, 245], // 9: final corner back onto the pit straight
];

// Corner-rounding half-width in radians, index-aligned with VERTEX_POLAR -
// wider blends read as sweeping/gentle corners, narrower ones as
// tighter/sharper turns. Tuned per-vertex alongside the radii above (via
// visual iteration - see the redesign's commit message) rather than one
// constant, since a wide blend on a very sharp turn (e.g. vertex 6, an ~86
// degree direction change) visually pinches the road to a point.
const CORNER_BLEND: number[] = [0.12, 0.07, 0.07, 0.05, 0.08, 0.09, 0.05, 0.1, 0.08, 0.12];

const VERTICES: Point[] = VERTEX_POLAR.map(([angleDeg, r]) => {
  const theta = (angleDeg * Math.PI) / 180;
  return { x: CENTER.x + r * Math.cos(theta), y: CENTER.y + r * Math.sin(theta) };
});

const VERTEX_ANGLES: number[] = VERTICES.map((v) => Math.atan2(v.y - CENTER.y, v.x - CENTER.x));

interface LineParams {
  /** Unit normal (nx, ny) and perpendicular distance d from CENTER, satisfying nx*x + ny*y = d for every point (x, y) on the line, oriented so d >= 0. */
  nx: number;
  ny: number;
  d: number;
}

// The straight line through two vertices, expressed relative to CENTER so
// that r(theta) = d / (nx*cos(theta) + ny*sin(theta)) reconstructs it.
function lineThrough(a: Point, b: Point): LineParams {
  const ax = a.x - CENTER.x;
  const ay = a.y - CENTER.y;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.hypot(dx, dy);
  let nx = -dy / length;
  let ny = dx / length;
  let d = nx * ax + ny * ay;
  if (d < 0) {
    nx = -nx;
    ny = -ny;
    d = -d;
  }
  return { nx, ny, d };
}

const SEGMENTS: LineParams[] = VERTICES.map((v, i) => lineThrough(v, VERTICES[(i + 1) % VERTICES.length]));

function segmentRadius(seg: LineParams, theta: number): number {
  return seg.d / (seg.nx * Math.cos(theta) + seg.ny * Math.sin(theta));
}

// Wraps b - a into (-pi, pi].
function angleDiff(a: number, b: number): number {
  return ((b - a + Math.PI) % (2 * Math.PI)) - Math.PI;
}

function radiusAt(theta: number): number {
  const wrapped = ((theta % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  const n = VERTICES.length;
  for (let i = 0; i < n; i++) {
    const a0 = VERTEX_ANGLES[i];
    const a1 = VERTEX_ANGLES[(i + 1) % n];
    const span = ((angleDiff(a0, a1) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI) || 2 * Math.PI;
    const pos = ((angleDiff(a0, wrapped) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    if (pos > span) {
      continue;
    }

    let r = segmentRadius(SEGMENTS[i], wrapped);
    const distFromStart = pos;
    const distFromEnd = span - pos;
    const blendStart = CORNER_BLEND[i];
    const blendEnd = CORNER_BLEND[(i + 1) % n];

    if (distFromStart < blendStart) {
      const rPrev = segmentRadius(SEGMENTS[(i - 1 + n) % n], wrapped);
      const t = 0.5 - 0.5 * Math.cos(Math.PI * (distFromStart / blendStart));
      r = rPrev * (1 - t) + r * t;
    } else if (distFromEnd < blendEnd) {
      const rNext = segmentRadius(SEGMENTS[(i + 1) % n], wrapped);
      const t = 0.5 - 0.5 * Math.cos(Math.PI * (distFromEnd / blendEnd));
      r = r * t + rNext * (1 - t);
    }
    return r;
  }
  throw new Error(`radiusAt: theta ${theta} not covered by any track segment`);
}

function samplePoints(): Point[] {
  const points: Point[] = [];
  for (let i = 0; i < SAMPLE_COUNT; i++) {
    const theta = (2 * Math.PI * i) / SAMPLE_COUNT;
    const r = radiusAt(theta);
    points.push({
      x: CENTER.x + r * Math.cos(theta),
      y: CENTER.y + r * Math.sin(theta),
    });
  }
  return points;
}

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

const TRACK_POINTS = samplePoints();

export const TRACK_PATH_D = catmullRomToBezierPath(TRACK_POINTS);

// theta=0 sample (before the start/finish kick-out bump) - a reasonable
// start/finish marker position on the straighter edge.
export const START_FINISH_POINT: Point = TRACK_POINTS[0];

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
