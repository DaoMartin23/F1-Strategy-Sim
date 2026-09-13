// Button label + short consequence subtext for every raw decision.choice
// string the sim can produce (see sim/race.py's Event.options lists) -
// shared between EventPanel's decision buttons and (indirectly, via the
// same design language) the debrief's past-tense narration.

export interface OptionDescription {
  label: string;
  sublabel: string;
}

const PIT_COMPOUND_LABELS: Record<string, string> = {
  pit_soft: "SOFT",
  pit_medium: "MEDIUM",
  pit_hard: "HARD",
  pit_inter: "INTERMEDIATE",
  pit_wet: "WET",
};

const PIT_SUBLABELS: Record<string, string> = {
  pit_soft: "~20s loss - fastest, wears quickest",
  pit_medium: "~20s loss - balanced pace and wear",
  pit_hard: "~20s loss - slowest, most durable",
  pit_inter: "~20s loss - for light rain",
  pit_wet: "~20s loss - for heavy rain",
};

export function describeOption(choice: string): OptionDescription {
  const compoundLabel = PIT_COMPOUND_LABELS[choice];
  if (compoundLabel !== undefined) {
    return { label: `PIT — ${compoundLabel}`, sublabel: PIT_SUBLABELS[choice] };
  }
  switch (choice) {
    case "stay_out":
      return { label: "STAY OUT", sublabel: "Keep current tyres" };
    case "hold_position":
      return { label: "HOLD POSITION", sublabel: "Keep current pace and tyres" };
    case "push":
      return { label: "PUSH", sublabel: "More pace, higher tyre wear" };
    case "repair":
      return { label: "REPAIR", sublabel: "Extended stop to fix the damage" };
    default:
      return { label: choice.toUpperCase(), sublabel: "" };
  }
}
