import { describeTrend, describeWetness, wetnessPct } from "../weather";

interface Props {
  wetness: number;
  previousWetness: number;
}

// Compact header chip - lap counter's neighbor, not a full panel.
export function WeatherChip({ wetness }: { wetness: number }) {
  return (
    <span className="db-weather-chip">
      {describeWetness(wetness)} — {wetnessPct(wetness)}% wet
    </span>
  );
}

export function WeatherPanel({ wetness, previousWetness }: Props) {
  return (
    <div className="db-panel">
      <h3 className="db-panel-title">Track &amp; Weather</h3>
      <div className="db-panel-headline">{describeWetness(wetness)}</div>
      <dl className="db-stat-list">
        <div>
          <dt>Wetness</dt>
          <dd>{wetnessPct(wetness)}%</dd>
        </div>
        <div>
          <dt>Trend</dt>
          <dd>{describeTrend(wetness, previousWetness)}</dd>
        </div>
      </dl>
    </div>
  );
}
