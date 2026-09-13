import { useState } from "react";
import { stepRace } from "../api/client";
import type { Decision, LapTrace, State } from "../api/types";
import { TOTAL_LAPS } from "../simConstants";
import { deriveStandings } from "../standings";
import { DebriefScreen } from "./DebriefScreen";
import { EventPanel } from "./EventPanel";
import { Leaderboard } from "./Leaderboard";
import { PlayerPanel } from "./PlayerPanel";
import { RivalPanel } from "./RivalPanel";
import { TrackMap } from "./TrackMap";
import { WeatherChip, WeatherPanel } from "./WeatherPanel";

interface Props {
  state: State;
  onStateChange: (state: State) => void;
  onNewRace: () => void;
}

// CLAUDE.md: "Ticks through laps at a fixed interval" - uniform per-lap
// duration, not adaptive/variable speed for long jumps. ~10s per lap so a
// car visibly completes one full loop of the track per tick, rather than
// zipping around it (the user's own report after playtesting the redesign).
const TICK_DURATION_MS = 10000;

// Plays through a LapTrace queue one lap at a time, calling onFrame every
// animation frame with the lap currently being shown and 0..1 progress
// through its fixed-duration tick. Resolves once every lap has played.
function playLapQueue(laps: LapTrace[], onFrame: (lap: LapTrace, progress: number) => void): Promise<void> {
  return new Promise((resolve) => {
    if (laps.length === 0) {
      resolve();
      return;
    }
    let index = 0;

    function playOneLap() {
      const lap = laps[index];
      const start = performance.now();

      function frame(now: number) {
        const progress = Math.min(1, (now - start) / TICK_DURATION_MS);
        onFrame(lap, progress);
        if (progress < 1) {
          requestAnimationFrame(frame);
          return;
        }
        index += 1;
        if (index < laps.length) {
          playOneLap();
        } else {
          resolve();
        }
      }

      requestAnimationFrame(frame);
    }

    playOneLap();
  });
}

function retiredIdSet(cars: State["cars"]): Set<number> {
  return new Set(cars.filter((car) => car.retired_lap !== null).map((car) => car.id));
}

// Every car's lap_time from the final LapTrace of a /race/step response -
// null if that response contained no laps (shouldn't happen in practice,
// but response.laps is technically nullable-length).
function lastLapTimesFrom(laps: LapTrace[]): Record<number, number> | null {
  if (laps.length === 0) {
    return null;
  }
  const finalLap = laps[laps.length - 1];
  const result: Record<number, number> = {};
  for (const car of finalLap.cars) {
    result[car.id] = car.lap_time;
  }
  return result;
}

export function RaceView({ state, onStateChange, onNewRace }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null = resting (show the authoritative `state` directly); set while a
  // /race/step response's laps are being animated through one at a time.
  const [displayedLap, setDisplayedLap] = useState<LapTrace | null>(null);
  const [animationProgress, setAnimationProgress] = useState(0);
  const [animatingRetiredIds, setAnimatingRetiredIds] = useState<Set<number>>(new Set());
  // The chrome (leaderboard, panels) intentionally updates immediately
  // alongside `state` rather than staying in lockstep with the map's
  // animation - only the map's car positions visually journey through the
  // intermediate laps. Wetness specifically isn't part of State at all
  // (never persisted, per the sim's "derive, don't store" design), so the
  // only way to know current weather client-side is to remember it from the
  // last lap of the most recent /race/step response - reset to "unknown
  // dry" on a fresh page load until the next action reports it for real.
  // previousWetness trails one step behind, purely to derive a genuine
  // rising/falling/steady trend for the weather panel (never a fabricated
  // forecast).
  const [lastKnownWetness, setLastKnownWetness] = useState(0);
  const [previousWetness, setPreviousWetness] = useState(0);
  const [lastLapTimes, setLastLapTimes] = useState<Record<number, number>>({});

  async function advance(decision: Decision | null) {
    setError(null);
    setBusy(true);
    try {
      const result = await stepRace(state, decision);
      // Persist the authoritative state immediately, decoupled from what's
      // visually animating below - a refresh mid-animation must resume at
      // the true state, never a partially-animated one.
      onStateChange(result.state);
      setAnimatingRetiredIds(retiredIdSet(result.state.cars));
      if (result.laps.length > 0) {
        setPreviousWetness(lastKnownWetness);
        setLastKnownWetness(result.laps[result.laps.length - 1].wetness);
        const times = lastLapTimesFrom(result.laps);
        if (times !== null) {
          setLastLapTimes(times);
        }
      }
      await playLapQueue(result.laps, (lap, progress) => {
        setDisplayedLap(lap);
        setAnimationProgress(progress);
      });
      setDisplayedLap(null);
      setAnimationProgress(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const animating = displayedLap !== null;
  const mapCars = displayedLap !== null ? displayedLap.cars : state.cars;
  const mapLap = displayedLap !== null ? displayedLap.lap : state.lap;
  const mapRetiredIds = displayedLap !== null ? animatingRetiredIds : retiredIdSet(state.cars);
  const mapAnimationProgress = displayedLap !== null ? animationProgress : 0;

  const player = state.cars[0];
  const finished = state.lap >= TOTAL_LAPS && state.pending_decision === null;
  const standings = deriveStandings(state.cars);
  const playerStanding = standings.find((entry) => entry.id === player.id) ?? null;

  return (
    <div className="race-dashboard">
      <header className="db-header">
        <div className="db-lap-counter">
          LAP {mapLap} / {TOTAL_LAPS}
        </div>
        <WeatherChip wetness={lastKnownWetness} />
        <button type="button" className="db-button" onClick={onNewRace}>
          New Race
        </button>
      </header>

      <section className="db-leaderboard">
        <Leaderboard cars={state.cars} lastLapTimes={lastLapTimes} />
      </section>

      <section className="db-right">
        <div className="db-panel db-trackmap-panel">
          <TrackMap cars={mapCars} lap={mapLap} retiredIds={mapRetiredIds} animationProgress={mapAnimationProgress} />
        </div>

        <div className="db-info-row">
          <PlayerPanel
            player={player}
            position={playerStanding?.position ?? null}
            lastLapTime={lastLapTimes[player.id] ?? null}
            pushActive={state.push_active}
          />
          <WeatherPanel wetness={lastKnownWetness} previousWetness={previousWetness} />
          <RivalPanel standings={standings} cars={state.cars} lastLapTimes={lastLapTimes} playerId={player.id} />
        </div>

        {finished && !animating ? (
          <DebriefScreen state={state} />
        ) : (
          <EventPanel
            event={state.pending_decision}
            lap={state.lap}
            animating={animating}
            busy={busy}
            playerPosition={playerStanding?.position ?? null}
            cars={state.cars}
            onChoose={(choice) => void advance({ choice })}
            onStart={() => void advance(null)}
          />
        )}
      </section>

      {error !== null && (
        <p role="alert" className="db-error">
          {error}
        </p>
      )}
    </div>
  );
}
