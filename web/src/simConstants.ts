// Hardcoded constants mirroring values from sim/model.py's PARAMS/tables.
// No codegen - kept in sync by hand (same approach as api/types.ts).

export const CAR_CHOICES = [
  "car_1",
  "car_2",
  "car_3",
  "car_4",
  "car_5",
  "car_6",
  "car_7",
  "car_8",
  "car_9",
  "car_10",
] as const;

// v1 ships one track.
export const TRACKS = ["silverstone"] as const;

// Mirrors TRACKS["silverstone"]["laps"] in sim/model.py.
export const TOTAL_LAPS = 52;

// Mirrors PARAMS["tyre"][compound]["cliff_lap"] in sim/model.py - used only
// to estimate a visual wear percentage for the tyre icon, not for any real
// simulation logic.
export const TYRE_CLIFF_LAP: Record<string, number> = {
  S: 16,
  M: 27,
  H: 40,
  I: 22,
  W: 30,
};
