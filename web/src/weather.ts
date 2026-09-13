// Wetness -> description/trend helpers, shared between WeatherPanel and its
// header WeatherChip (kept out of WeatherPanel.tsx itself so that file only
// exports components, per react-refresh's lint rule).

export function describeWetness(wetness: number): string {
  if (wetness < 0.15) return "Dry";
  if (wetness < 0.4) return "Damp";
  if (wetness < 0.7) return "Rain";
  return "Heavy Rain";
}

export function wetnessPct(wetness: number): number {
  return Math.round(Math.min(1, Math.max(0, wetness)) * 100);
}

// Only ever derived from real, already-known wetness readings (this tick's
// vs the previous one) - never a fabricated forecast, since the sim has no
// concept of predicted future weather to draw on (confirmed with the user).
export function describeTrend(wetness: number, previousWetness: number): string {
  const delta = wetness - previousWetness;
  if (Math.abs(delta) < 0.02) {
    return "Steady";
  }
  return delta > 0 ? "Rising" : "Falling";
}
