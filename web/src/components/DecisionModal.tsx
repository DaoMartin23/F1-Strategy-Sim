import type { Event } from "../api/types";

interface Props {
  event: Event;
  onChoose: (choice: string) => void;
  disabled: boolean;
}

const EVENT_LABELS: Record<string, string> = {
  rain_start: "Rain is starting",
  rain_end: "Rain is stopping",
  damage: "Your car has damage",
  overtaken: "You've been overtaken",
  safety_car: "Safety car deployed",
  pitting_opportunity: "Pitting opportunity",
};

// Per CLAUDE.md: "Decision modal: shows the options from the event, nothing
// else. No hints in v1." - plain buttons, no numeric guidance.
export function DecisionModal({ event, onChoose, disabled }: Props) {
  return (
    <div role="dialog" aria-modal="true">
      <h2>{EVENT_LABELS[event.type] ?? event.type}</h2>
      <p>Lap {event.lap}</p>
      <div>
        {event.options.map((option) => (
          <button key={option} type="button" disabled={disabled} onClick={() => onChoose(option)}>
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
