// A stylized, hand-tuned closed track shape - NOT a licensed/precise trace
// of Silverstone's real geometry (confirmed with the user as an acceptable
// approximation). Built as a parametric polar curve r(theta) around a fixed
// center: since every angle maps to exactly one point, the resulting closed
// curve is guaranteed to never self-intersect, which hand-placed bezier
// waypoints turned out not to be (see git history / commit message for the
// self-intersecting first attempts this replaced).
//
// The shape carries a long diagonal "straight" on one side and a pinched,
// hairpin-like dip on the other, evoking Silverstone's real silhouette (a
// long Hangar-Straight-like edge, a tighter infield section) without
// tracing its actual corner-by-corner layout.

export const TRACK_VIEWBOX = "0 0 1000 1000";

interface Point {
  x: number;
  y: number;
}

const CENTER: Point = { x: 500, y: 480 };
const BASE_RADIUS = 230;
const ASPECT_X = 1.5;
const ASPECT_Y = 1.0;
const SAMPLE_COUNT = 240;

function angularDelta(theta: number, center: number): number {
  return ((theta - center + Math.PI) % (2 * Math.PI)) - Math.PI;
}

function gaussianBump(theta: number, center: number, width: number, amplitude: number): number {
  const d = angularDelta(theta, center);
  return amplitude * Math.exp(-((d / width) ** 2));
}

function radiusAt(theta: number): number {
  let r = BASE_RADIUS;
  r += 55 * Math.cos(theta - 0.85); // bulge toward the long-straight side
  r -= 60 * Math.cos(2 * (theta - 0.85)); // flatten that bulge into a straighter edge
  r += 20 * Math.sin(4 * theta + 0.6) * (0.5 + 0.5 * Math.cos(theta - 2.6)); // localized esses waviness
  r -= gaussianBump(theta, 2.65, 0.35, 70); // pinched hairpin-like dip
  r += gaussianBump(theta, 0.15, 0.3, 25); // small kick-out near start/finish
  return r;
}

function samplePoints(): Point[] {
  const points: Point[] = [];
  for (let i = 0; i < SAMPLE_COUNT; i++) {
    const theta = (2 * Math.PI * i) / SAMPLE_COUNT;
    const r = radiusAt(theta);
    points.push({
      x: CENTER.x + r * ASPECT_X * Math.cos(theta),
      y: CENTER.y + r * ASPECT_Y * Math.sin(theta),
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
