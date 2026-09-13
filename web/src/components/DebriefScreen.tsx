import { useEffect, useState } from "react";
import { getOptimal } from "../api/client";
import type { OptimalResult, State } from "../api/types";
import { decisionNarrative, rateStrategy, tyreStrategyNarrative } from "../debriefNarrative";
import { deriveStandings } from "../standings";

interface Props {
  state: State;
}

export function DebriefScreen({ state }: Props) {
  const [optimal, setOptimal] = useState<OptimalResult | null>(null);
  const [optimalError, setOptimalError] = useState<string | null>(null);
  const [optimalLoading, setOptimalLoading] = useState(true);

  const player = state.cars[0];

  useEffect(() => {
    let cancelled = false;
    setOptimalLoading(true);
    setOptimalError(null);
    getOptimal({
      track: state.track,
      seed: state.seed,
      car: player.car,
      starting_position: state.starting_position,
    })
      .then((result) => {
        if (!cancelled) setOptimal(result);
      })
      .catch((err) => {
        if (!cancelled) setOptimalError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setOptimalLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // A finished race's `state` is never mutated in place - a new race
    // replaces it wholesale - so re-running only when these identifying
    // fields change is equivalent to running once per finished race.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.track, state.seed, state.starting_position, player.car]);

  const standings = deriveStandings(state.cars);
  const finishEntry = standings.find((entry) => entry.id === player.id);
  const retiredLap = player.retired_lap;
  const finishingPositionLabel =
    retiredLap !== null ? `DNF (retired lap ${retiredLap})` : `P${finishEntry?.position ?? "?"}`;

  // No decisions exist past a DNF - there was nothing left to decide.
  const loggedDecisions =
    retiredLap !== null ? state.decision_log.filter((entry) => entry.lap <= retiredLap) : state.decision_log;
  const totalDelta = loggedDecisions.reduce((sum, entry) => sum + entry.delta_seconds, 0);

  return (
    <section className="debrief">
      <h2>Debrief</h2>
      <ul>
        <li>Starting position: P{state.starting_position}</li>
        <li>Finishing position: {finishingPositionLabel}</li>
        <li>Pit stops: {player.pit_count}</li>
        <li>Tyre strategy: {tyreStrategyNarrative(state.decision_log)}</li>
      </ul>

      <h3>Key decisions</h3>
      {loggedDecisions.length === 0 ? (
        <p>No decisions were needed this race.</p>
      ) : (
        <ul>
          {loggedDecisions.map((entry, index) => (
            <li key={`${entry.lap}-${entry.event_type}-${index}`}>{decisionNarrative(entry)}</li>
          ))}
        </ul>
      )}
      <p>
        Net time gained/lost from decisions: {totalDelta >= 0 ? "+" : ""}
        {totalDelta.toFixed(1)}s
      </p>

      <h3>Strategy rating</h3>
      {optimalLoading && <p>Computing the optimal strategy for comparison…</p>}
      {optimalError !== null && (
        <p role="alert">Could not compute the optimal-strategy comparison: {optimalError}</p>
      )}
      {optimal !== null && (
        <p>
          Rating: {rateStrategy(player, optimal)} — the best strategy the sim could find for this race finishes in{" "}
          {optimal.total_time.toFixed(1)}s
          {retiredLap === null && (
            <>
              {" "}
              ({player.total_time - optimal.total_time >= 0 ? "+" : ""}
              {(player.total_time - optimal.total_time).toFixed(1)}s vs your race)
            </>
          )}
          .
        </p>
      )}
    </section>
  );
}
