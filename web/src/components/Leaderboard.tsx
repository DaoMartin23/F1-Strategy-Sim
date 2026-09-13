import type { CarState } from "../api/types";
import { deriveStandings } from "../standings";
import { TyreBadge } from "./TyreBadge";

interface Props {
  cars: CarState[];
  /** Every car's most recently completed lap time, keyed by car id - absent until that car's first lap finishes. */
  lastLapTimes: Record<number, number>;
}

function formatGap(entry: { gapToLeader: number | null; retired: boolean }): string {
  if (entry.retired) {
    return "DNF";
  }
  if (entry.gapToLeader === null) {
    return "Leader";
  }
  return `+${entry.gapToLeader.toFixed(1)}s`;
}

function formatLastLap(seconds: number | undefined): string {
  return seconds === undefined ? "—" : `${seconds.toFixed(1)}s`;
}

export function Leaderboard({ cars, lastLapTimes }: Props) {
  const standings = deriveStandings(cars);
  const carsById = new Map(cars.map((car) => [car.id, car]));

  return (
    <table>
      <thead>
        <tr>
          <th>Pos</th>
          <th>Driver</th>
          <th>Tyre</th>
          <th>Gap</th>
          <th>Last Lap</th>
        </tr>
      </thead>
      <tbody>
        {standings.map((entry) => {
          const car = carsById.get(entry.id);
          if (car === undefined) {
            return null;
          }
          const rowClass = entry.id === 0 ? "db-player-row" : entry.retired ? "db-retired-row" : undefined;
          return (
            <tr key={entry.id} className={rowClass}>
              <td>{entry.position}</td>
              <td>{entry.id === 0 ? "YOU" : `Car ${entry.id}`}</td>
              <td>
                <TyreBadge compound={car.compound} size={20} />
              </td>
              <td>{formatGap(entry)}</td>
              <td>{formatLastLap(lastLapTimes[entry.id])}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
