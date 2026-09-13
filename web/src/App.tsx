import { useState } from "react";
import { PreRacePicker } from "./components/PreRacePicker";
import { clearRaceState, loadRaceState, saveRaceState } from "./storage";
import type { State } from "./api/types";

function App() {
  // localStorage is synchronous, so the saved race (if any) can be read
  // directly as the initial state - no effect/loading-state dance needed.
  const [raceState, setRaceState] = useState<State | null>(loadRaceState);

  function handleRaceCreated(state: State) {
    saveRaceState(state);
    setRaceState(state);
  }

  function handleNewRace() {
    clearRaceState();
    setRaceState(null);
  }

  if (raceState === null) {
    return <PreRacePicker onRaceCreated={handleRaceCreated} />;
  }

  return (
    <main>
      <h1>F1 Race Strategy Game</h1>
      <p>
        Race in progress — {raceState.track}, car {raceState.cars[0].car}, starting P
        {raceState.starting_position}, lap {raceState.lap}
      </p>
      <button type="button" onClick={handleNewRace}>
        New Race
      </button>
    </main>
  );
}

export default App;
