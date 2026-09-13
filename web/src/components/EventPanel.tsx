import type { CarState, Event } from "../api/types";
import { describeOption } from "../decisionOptions";

interface Props {
  event: Event | null;
  /** state.lap (the resting lap, not the mid-animation display lap) - only used to detect the pre-lap-1 "not started yet" state. */
  lap: number;
  animating: boolean;
  busy: boolean;
  playerPosition: number | null;
  cars: CarState[];
  onChoose: (choice: string) => void;
  onStart: () => void;
}

const EVENT_LABELS: Record<string, string> = {
  rain_start: "Rain Developing",
  rain_end: "Track Drying",
  damage: "Car Damage",
  overtaken: "Overtaken",
  safety_car: "Safety Car Deployed",
  pitting_opportunity: "Pitting Opportunity",
};

// A short, factual line under the heading - built only from data the sim
// actually provides via event.context (or things already known client-side
// like the player's position), never invented flavor text with numbers
// behind it.
function contextLine(event: Event, playerPosition: number | null): string {
  const posLabel = playerPosition !== null ? `You are P${playerPosition}. ` : "";
  switch (event.type) {
    case "rain_start":
      return `${posLabel}Rain is falling — track wetness ${Math.round(Number(event.context.wetness) * 100)}%.`;
    case "rain_end":
      return `${posLabel}The track is drying out — wetness down to ${Math.round(Number(event.context.wetness) * 100)}%.`;
    case "damage":
      return `${posLabel}Your car has taken damage.`;
    case "overtaken":
      return `${posLabel}Car ${String(event.context.overtaken_by)} has gone past you.`;
    case "safety_car":
      return `${posLabel}The field has bunched up. This could be a good opportunity to pit.`;
    case "pitting_opportunity": {
      const pitted = Array.isArray(event.context.rivals_pitted) ? event.context.rivals_pitted.length : 0;
      return `${posLabel}${pitted} rival${pitted === 1 ? " has" : "s have"} already pitted.`;
    }
    default:
      return posLabel;
  }
}

// The bottom-right panel is a permanent fixture of the dashboard (not a
// modal overlay) - subdued when there's nothing to decide, large and
// prominent when an event fires, per the reference design.
export function EventPanel({ event, lap, animating, busy, playerPosition, cars, onChoose, onStart }: Props) {
  if (event !== null && !animating) {
    return (
      <div className="db-panel db-event-panel db-event-active">
        <h2 className="db-event-heading">{EVENT_LABELS[event.type] ?? event.type}</h2>
        <p className="db-event-context">{contextLine(event, playerPosition)}</p>
        <div className="db-option-grid">
          {event.options.map((option) => {
            const { label, sublabel } = describeOption(option);
            return (
              <button
                key={option}
                type="button"
                className="db-button db-option-button"
                disabled={busy}
                onClick={() => onChoose(option)}
              >
                <span className="db-option-label">{label}</span>
                {sublabel !== "" && <span className="db-option-sublabel">{sublabel}</span>}
              </button>
            );
          })}
        </div>
        {busy && <p className="db-muted">Applying your choice…</p>}
      </div>
    );
  }

  if (lap === 0 && !animating) {
    return (
      <div className="db-panel db-event-panel db-event-idle">
        <h2 className="db-event-heading">Ready to Race</h2>
        <p className="db-event-context">{cars.length} cars on the grid. Lights out and away we go.</p>
        <button
          type="button"
          className="db-button db-button-primary db-start-button"
          disabled={busy}
          onClick={onStart}
        >
          {busy ? "Starting…" : "Start Race"}
        </button>
      </div>
    );
  }

  return (
    <div className="db-panel db-event-panel db-event-idle">
      <h2 className="db-event-heading">On Track</h2>
      <p className="db-event-context">{animating ? "Cars are on track…" : `Racing — lap ${lap}.`}</p>
    </div>
  );
}
