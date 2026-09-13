import { useState } from "react";
import { stepRace } from "../api/client";
import type { Decision, LapTrace, State } from "../api/types";
import { TOTAL_LAPS } from "../simConstants";
import { DebriefScreen } from "./DebriefScreen";
import { DecisionModal } from "./DecisionModal";
import { GapBoard } from "./GapBoard";
import { TrackMap } from "./TrackMap";
import { TyreIcon } from "./TyreIcon";
import { WeatherBadge } from "./WeatherBadge";

interface Props {
  state: State;
  onStateChange: (state: State) => void;
  onNewRace: () => void;
}

// CLAUDE.md: "Ticks through laps at a fixed interval" - uniform per-lap
// duration, not adaptive/variable speed for long jumps.
const TICK_DURATION_MS = 500;

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

export function RaceView({ state, onStateChange, onNewRace }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null = resting (show the authoritative `state` directly); set while a
  // /race/step response's laps are being animated through one at a time.
  const [displayedLap, setDisplayedLap] = useState<LapTrace | null>(null);
  const [animationProgress, setAnimationProgress] = useState(0);
  const [animatingRetiredIds, setAnimatingRetiredIds] = useState<Set<number>>(new Set());
  // The chrome (gap board, tyre icon, weather badge) intentionally updates
  // immediately alongside `state` rather than staying in lockstep with the
  // map's animation - only the map's car positions visually journey through
  // the intermediate laps. Wetness specifically isn't part of State at all
  // (never persisted, per the sim's "derive, don't store" design), so the
  // only way to know current weather client-side is to remember it from the
  // last lap of the most recent /race/step response - reset to "unknown
  // dry" on a fresh page load until the next action reports it for real.
  const [lastKnownWetness, setLastKnownWetness] = useState(0);

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
        setLastKnownWetness(result.laps[result.laps.length - 1].wetness);
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

  return (
    <main>
      <h1>F1 Race Strategy Game</h1>

      <p>
        Lap {mapLap} / {TOTAL_LAPS} — <WeatherBadge wetness={lastKnownWetness} />
      </p>

      <TrackMap cars={mapCars} lap={mapLap} retiredIds={mapRetiredIds} animationProgress={mapAnimationProgress} />

      <p>
        <TyreIcon compound={player.compound} tyreAge={player.tyre_age} /> {player.car} — pit stops:{" "}
        {player.pit_count} — damage: {player.damage}
        {player.retired_lap !== null && " — DNF"}
      </p>

      <GapBoard cars={state.cars} />

      {finished && !animating && <DebriefScreen state={state} />}

      {!finished && !animating && state.pending_decision !== null && (
        <DecisionModal
          event={state.pending_decision}
          disabled={busy}
          onChoose={(choice) => void advance({ choice })}
        />
      )}

      {!finished && !animating && state.pending_decision === null && (
        <div>
          <button type="button" disabled={busy} onClick={() => void advance(null)}>
            Continue
          </button>
          <button type="button" disabled={busy} onClick={() => void advance({ push: !state.push_active })}>
            Push: {state.push_active ? "ON" : "OFF"}
          </button>
        </div>
      )}

      <button type="button" onClick={onNewRace}>
        New Race
      </button>

      {error !== null && <p role="alert">{error}</p>}
    </main>
  );
}
