// Hardcoded to mirror sim/model.py's CAR_CHOICES keys. No codegen - keep in
// sync by hand if the Python side changes (same approach as api/types.ts).
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
