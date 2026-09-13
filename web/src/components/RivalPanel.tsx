import type { CarState } from "../api/types";
import type { StandingEntry } from "../standings";
import { TyreBadge } from "./TyreBadge";

interface Props {
  standings: StandingEntry[];
  cars: CarState[];
  lastLapTimes: Record<number, number>;
  playerId: number;
}

function formatGap(entry: StandingEntry): string {
  if (entry.retired) {
    return "DNF";
  }
  if (entry.gapToLeader === null) {
    return "Leader";
  }
  return `+${entry.gapToLeader.toFixed(1)}s`;
}

// Two positions ahead and two behind the player - the cars actually
// relevant to the player's immediate strategy, kept compact rather than
// repeating the full leaderboard.
export function RivalPanel({ standings, cars, lastLapTimes, playerId }: Props) {
  const carsById = new Map(cars.map((car) => [car.id, car]));
  const playerIndex = standings.findIndex((entry) => entry.id === playerId);
  const nearby =
    playerIndex === -1
      ? []
      : standings.slice(Math.max(0, playerIndex - 2), playerIndex + 3).filter((entry) => entry.id !== playerId);

  return (
    <div className="db-panel">
      <h3 className="db-panel-title">Nearby Rivals</h3>
      {nearby.length === 0 ? (
        <p className="db-muted">No nearby rivals.</p>
      ) : (
        <ul className="db-rival-list">
          {nearby.map((entry) => {
            const car = carsById.get(entry.id);
            if (car === undefined) {
              return null;
            }
            return (
              <li key={entry.id} className="db-rival-row">
                <div className="db-rival-top">
                  <span className="db-rival-pos">P{entry.position}</span>
                  <span className="db-rival-name">Car {entry.id}</span>
                  <TyreBadge compound={car.compound} size={16} />
                </div>
                <div className="db-rival-bottom">
                  <span>{car.tyre_age}L tyre</span>
                  <span>{formatGap(entry)}</span>
                  <span>{lastLapTimes[entry.id] !== undefined ? `${lastLapTimes[entry.id].toFixed(1)}s` : "—"}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
