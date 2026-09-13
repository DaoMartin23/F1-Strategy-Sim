import type { CarState } from "../api/types";
import { COMPOUND_NAMES } from "../tyreColors";
import { TyreBadge } from "./TyreBadge";
import { TyreDegradationBar } from "./TyreDegradationBar";

interface Props {
  player: CarState;
  position: number | null;
  /**
   * The player's most recently completed lap time. Doubles as both "last
   * lap" (once at rest) and "current lap" (while that lap is mid-animation)
   * - the sim has no partial-lap telemetry to show a genuinely separate
   * in-progress time, so rather than fabricate one, both concepts collapse
   * to this single real number.
   */
  lastLapTime: number | null;
  pushActive: boolean;
}

export function PlayerPanel({ player, position, lastLapTime, pushActive }: Props) {
  return (
    <div className="db-panel">
      <h3 className="db-panel-title">Your Car</h3>
      <div className="db-panel-headline">{position !== null ? `P${position}` : "—"}</div>

      <div className="db-player-tyre-row">
        <TyreBadge compound={player.compound} />
        <span>
          {COMPOUND_NAMES[player.compound]} — age {player.tyre_age}
        </span>
      </div>
      <TyreDegradationBar compound={player.compound} tyreAge={player.tyre_age} />

      <dl className="db-stat-list">
        <div>
          <dt>Last lap</dt>
          <dd>{lastLapTime !== null ? `${lastLapTime.toFixed(1)}s` : "—"}</dd>
        </div>
        <div>
          <dt>Pit stops</dt>
          <dd>{player.pit_count}</dd>
        </div>
        <div>
          <dt>Pace mode</dt>
          <dd className={pushActive ? "db-push-on" : undefined}>{pushActive ? "PUSH" : "STANDARD"}</dd>
        </div>
      </dl>

      {player.retired_lap !== null && <p className="db-dnf-badge">DNF — lap {player.retired_lap}</p>}
    </div>
  );
}
