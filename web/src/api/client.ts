import type { Decision, Event, LapTrace, OptimalResult, State } from "./types";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${path} failed: ${response.status} ${detail}`);
  }
  return (await response.json()) as T;
}

export interface RaceSetup {
  track: string;
  seed: number;
  car: string;
  starting_position: number;
}

export interface StepResult {
  state: State;
  laps: LapTrace[];
  event: Event | null;
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`/health failed: ${response.status}`);
  }
  return (await response.json()) as { status: string };
}

export function createRace(setup: RaceSetup): Promise<State> {
  return postJson<State>("/race/new", setup);
}

export function stepRace(state: State, decision: Decision | null): Promise<StepResult> {
  return postJson<StepResult>("/race/step", { state, decision });
}

export function getOptimal(setup: RaceSetup): Promise<OptimalResult> {
  return postJson<OptimalResult>("/race/optimal", setup);
}
