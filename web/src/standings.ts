import type { CarState } from "./api/types";

export interface StandingEntry {
  id: number;
  position: number;
  /** Seconds behind the leader; null for the leader's own row. */
  gapToLeader: number | null;
  retired: boolean;
}

// Mirrors sim/race.py's own ranking: active cars ordered by total_time
// ascending, retirees ranked behind every active car, ordered by
// retired_lap descending (lasted longer = better final classification).
export function deriveStandings(cars: CarState[]): StandingEntry[] {
  const active = [...cars].filter((car) => car.retired_lap === null).sort((a, b) => a.total_time - b.total_time);
  const retired = [...cars]
    .filter((car) => car.retired_lap !== null)
    .sort((a, b) => (b.retired_lap ?? 0) - (a.retired_lap ?? 0));

  const leaderTime = active.length > 0 ? active[0].total_time : 0;

  const activeEntries: StandingEntry[] = active.map((car, index) => ({
    id: car.id,
    position: index + 1,
    gapToLeader: index === 0 ? null : car.total_time - leaderTime,
    retired: false,
  }));

  const retiredEntries: StandingEntry[] = retired.map((car, index) => ({
    id: car.id,
    position: active.length + index + 1,
    gapToLeader: null,
    retired: true,
  }));

  return [...activeEntries, ...retiredEntries];
}
