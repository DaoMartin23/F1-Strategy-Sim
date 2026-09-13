import { useState } from "react";
import { stepRace } from "../api/client";
import type { Decision, State } from "../api/types";
import { TOTAL_LAPS } from "../carChoices";
import { DecisionModal } from "./DecisionModal";

interface Props {
  state: State;
  onStateChange: (state: State) => void;
  onNewRace: () => void;
}

export function RaceView({ state, onStateChange, onNewRace }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function advance(decision: Decision | null) {
    setError(null);
    setBusy(true);
    try {
      const result = await stepRace(state, decision);
      onStateChange(result.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const player = state.cars[0];
  const finished = state.lap >= TOTAL_LAPS && state.pending_decision === null;

  return (
    <main>
      <h1>F1 Race Strategy Game</h1>
      <p>
        Lap {state.lap} / {TOTAL_LAPS} — {player.car} — tyres: {player.compound} (age {player.tyre_age}) — pit
        stops: {player.pit_count} — damage: {player.damage}
        {player.retired_lap !== null && " — DNF"}
      </p>

      {finished && <p>Race finished.</p>}

      {!finished && state.pending_decision !== null && (
        <DecisionModal
          event={state.pending_decision}
          disabled={busy}
          onChoose={(choice) => void advance({ choice })}
        />
      )}

      {!finished && state.pending_decision === null && (
        <div>
          <button type="button" disabled={busy} onClick={() => void advance(null)}>
            Continue
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void advance({ push: !state.push_active })}
          >
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
