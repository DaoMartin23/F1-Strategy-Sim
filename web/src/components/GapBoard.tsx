import type { CarState } from "../api/types";
import { deriveStandings } from "../standings";

interface Props {
  cars: CarState[];
}

function formatGap(entry: { gapToLeader: number | null; retired: boolean; position: number }): string {
  if (entry.retired) {
    return "DNF";
  }
  if (entry.gapToLeader === null) {
    return "Leader";
  }
  return `+${entry.gapToLeader.toFixed(1)}s`;
}

export function GapBoard({ cars }: Props) {
  const standings = deriveStandings(cars);

  return (
    <table>
      <caption>Standings</caption>
      <thead>
        <tr>
          <th>Pos</th>
          <th>Car</th>
          <th>Gap</th>
        </tr>
      </thead>
      <tbody>
        {standings.map((entry) => (
          <tr key={entry.id} aria-current={entry.id === 0 ? "true" : undefined}>
            <td>{entry.position}</td>
            <td>{entry.id === 0 ? "You" : `Car ${entry.id}`}</td>
            <td>{formatGap(entry)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
