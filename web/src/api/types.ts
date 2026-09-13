// Hand-written mirror of sim/types.py and sim/optimal.py.
// Field names and shapes must stay in sync with those dataclasses by hand -
// there is no codegen step for this in v1.

export type Compound = "S" | "M" | "H" | "I" | "W";

export type EventType =
  | "rain_start"
  | "rain_end"
  | "damage"
  | "overtaken"
  | "safety_car"
  | "pitting_opportunity";

export interface CarState {
  id: number;
  car: string;
  compound: Compound;
  tyre_age: number;
  pit_count: number;
  damage: number;
  total_time: number;
  retired_lap: number | null;
}

export interface CarLap {
  id: number;
  position: number;
  total_time: number;
  lap_time: number;
  compound: Compound;
  tyre_age: number;
}

export interface LapTrace {
  lap: number;
  wetness: number;
  cars: CarLap[];
}

export interface PitPlanEntry {
  target_lap: number;
  compound: Compound;
}

export interface DecisionLogEntry {
  lap: number;
  event_type: EventType;
  choice: string;
  delta_seconds: number;
}

export interface Event {
  type: EventType;
  lap: number;
  options: string[];
  context: Record<string, unknown>;
}

export interface Decision {
  choice?: string | null;
  push?: boolean | null;
}

export interface State {
  track: string;
  seed: number;
  lap: number;
  push_active: boolean;
  starting_position: number;
  player_strategy: PitPlanEntry[];
  pending_decision: Event | null;
  decision_log: DecisionLogEntry[];
  cars: CarState[];
  safety_car_ends_after_lap: number | null;
}

export type PushPolicy = "never" | "always";

export interface CandidateStrategy {
  stops: PitPlanEntry[];
  push_policy: PushPolicy;
  reactive_choices: Partial<Record<EventType, string>>;
}

export interface OptimalResult {
  total_time: number;
  strategy: CandidateStrategy;
  positions: number[];
}
