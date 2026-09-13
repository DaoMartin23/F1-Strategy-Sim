import type { CarState, DecisionLogEntry, EventType, OptimalResult } from "./api/types";

const EVENT_LABELS: Record<EventType, string> = {
  rain_start: "the start of rain",
  rain_end: "the rain stopping",
  damage: "car damage",
  overtaken: "being overtaken",
  safety_car: "the Safety Car",
  pitting_opportunity: "a pitting opportunity",
};

const COMPOUND_NAMES: Record<string, string> = {
  soft: "Soft",
  medium: "Medium",
  hard: "Hard",
  inter: "Intermediate",
  wet: "Wet",
};

function describeChoice(choice: string): string {
  if (choice.startsWith("pit_")) {
    const compound = COMPOUND_NAMES[choice.slice(4)] ?? choice.slice(4);
    return `pitted for ${compound} tyres`;
  }
  switch (choice) {
    case "stay_out":
      return "stayed out";
    case "hold_position":
      return "held position";
    case "push":
      return "pushed";
    case "repair":
      return "repaired the car";
    default:
      return choice;
  }
}

// Matches CLAUDE.md's example phrasing: "You gained 8.4 seconds by pitting
// under the Safety Car."
export function decisionNarrative(entry: DecisionLogEntry): string {
  const gained = entry.delta_seconds >= 0;
  const magnitude = Math.abs(entry.delta_seconds).toFixed(1);
  const action = describeChoice(entry.choice);
  const verb = gained ? "gained" : "lost";
  return `Lap ${entry.lap}: you ${action} in response to ${EVENT_LABELS[entry.event_type]} — ${verb} ${magnitude}s.`;
}

// Reconstructs the compound-change history from decision_log (every pit
// choice the player made was necessarily logged there, since the only way
// to pit in this UI is by answering a decision). "repair" pits are
// deliberately excluded - they don't change compound, so aren't a new
// stint.
export function tyreStrategyNarrative(decisionLog: DecisionLogEntry[]): string {
  const stints = ["Medium (start)"];
  for (const entry of decisionLog) {
    if (entry.choice.startsWith("pit_")) {
      const compound = COMPOUND_NAMES[entry.choice.slice(4)] ?? entry.choice.slice(4);
      stints.push(`${compound} (lap ${entry.lap})`);
    }
  }
  return stints.join(" → ");
}

export function rateStrategy(player: CarState, optimal: OptimalResult): string {
  if (player.retired_lap !== null) {
    return "DNF";
  }
  const deltaToOptimal = player.total_time - optimal.total_time;
  if (deltaToOptimal <= 5) return "Excellent";
  if (deltaToOptimal <= 20) return "Good";
  if (deltaToOptimal <= 45) return "Fair";
  return "Poor";
}
