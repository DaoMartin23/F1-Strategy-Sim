import type { State } from "./api/types";

const STORAGE_KEY = "f1-game-race-state";

export function loadRaceState(): State | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    return JSON.parse(raw) as State;
  } catch {
    return null;
  }
}

export function saveRaceState(state: State): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clearRaceState(): void {
  localStorage.removeItem(STORAGE_KEY);
}
