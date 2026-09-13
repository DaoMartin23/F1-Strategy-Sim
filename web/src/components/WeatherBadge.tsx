interface Props {
  wetness: number;
}

function describeWetness(wetness: number): string {
  if (wetness < 0.15) return "Dry";
  if (wetness < 0.4) return "Damp";
  if (wetness < 0.7) return "Rain";
  return "Heavy rain";
}

export function WeatherBadge({ wetness }: Props) {
  const pct = Math.round(Math.min(1, Math.max(0, wetness)) * 100);
  return (
    <span>
      {describeWetness(wetness)} ({pct}% wet)
    </span>
  );
}
