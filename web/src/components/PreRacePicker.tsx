import { useState } from "react";
import type { FormEvent } from "react";
import { createRace } from "../api/client";
import type { State } from "../api/types";
import { CAR_CHOICES, TRACKS } from "../carChoices";

interface Props {
  onRaceCreated: (state: State) => void;
}

function randomSeed(): number {
  return Math.floor(Math.random() * 1_000_000_000);
}

export function PreRacePicker({ onRaceCreated }: Props) {
  const [track] = useState<string>(TRACKS[0]);
  const [car, setCar] = useState<string>(CAR_CHOICES[0]);
  const [startingPosition, setStartingPosition] = useState<number>(10);
  const [seed, setSeed] = useState<number>(randomSeed);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const state = await createRace({ track, seed, car, starting_position: startingPosition });
      onRaceCreated(state);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)}>
      <h1>New Race</h1>

      <label>
        Track
        <select value={track} disabled>
          {TRACKS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <label>
        Car
        <select value={car} onChange={(event) => setCar(event.target.value)}>
          {CAR_CHOICES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>

      <label>
        Starting position
        <input
          type="number"
          min={1}
          max={20}
          value={startingPosition}
          onChange={(event) => setStartingPosition(Number(event.target.value))}
        />
      </label>

      <label>
        Seed
        <input
          type="number"
          value={seed}
          onChange={(event) => setSeed(Number(event.target.value))}
        />
      </label>

      <button type="submit" disabled={submitting}>
        {submitting ? "Starting..." : "Start Race"}
      </button>

      {error !== null && <p role="alert">{error}</p>}
    </form>
  );
}
