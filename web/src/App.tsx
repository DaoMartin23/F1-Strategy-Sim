import { useState } from "react";
import { PreRacePicker } from "./components/PreRacePicker";
import { RaceView } from "./components/RaceView";
import { clearRaceState, loadRaceState, saveRaceState } from "./storage";
import type { State } from "./api/types";

function App() {
  // localStorage is synchronous, so the saved race (if any) can be read
  // directly as the initial state - no effect/loading-state dance needed.
  const [raceState, setRaceState] = useState<State | null>(loadRaceState);

  function handleStateChange(state: State) {
    saveRaceState(state);
    setRaceState(state);
  }

  function handleNewRace() {
    clearRaceState();
    setRaceState(null);
  }

  if (raceState === null) {
    return <PreRacePicker onRaceCreated={handleStateChange} />;
  }

  return <RaceView state={raceState} onStateChange={handleStateChange} onNewRace={handleNewRace} />;
}

export default App;
