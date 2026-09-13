# F1 Race Strategy Game

A browser-based F1 race strategy game. You pick a car and starting grid slot, then race a 20-car field lap by lap: the sim pauses at key moments (rain starting or stopping, car damage, being overtaken, a safety car, a pitting opportunity) for you to make the call, and continues once you've decided. You can also push at any time for extra pace at the cost of extra tyre wear. After the finish, a debrief screen compares your race against the best strategy a Monte Carlo search can find for the same conditions.

## Features

- 20-car race with 19 rival AIs running fixed one-stop/two-stop/reactive-to-rain strategies
- Six decision event types: rain starting, rain stopping, damage, being overtaken, a safety car, and pitting opportunities
- A standing push toggle, on top of event-driven decisions
- Pre-race picker: choose your car, starting grid position, and race seed
- An animated track map with small model-car icons, spaced proportionally to real time gaps, following a stylized Silverstone-like layout
- Gap board, tyre wear icons, and a weather badge alongside the map
- Debrief screen: finishing vs. starting position, pit stops, tyre strategy, a narrated breakdown of every decision's time gained/lost, and a strategy rating against the sim's own best-found strategy
- Save/resume: race state lives in the browser's localStorage, one race at a time

## How it works

- **`sim/`** — the simulation itself, plain Python with no framework dependencies. `step()` advances one lap; `run_to_next_decision()` loops it until an event fires or the race ends. Every random draw (lap-time noise, pit loss, weather, incidents, grid shuffling) goes through an RNG seeded from `(seed, lap, purpose)`, so the same seed and the same decisions always produce the same race.
- **`api/`** — a stateless FastAPI layer, thin wrappers around `sim/`. No sessions, no database: every request carries the full race state, and the server holds nothing between requests.
  - `POST /race/new` — start a race for a given track, seed, car, and starting position
  - `POST /race/step` — apply a decision (or none) and run to the next event or the finish
  - `POST /race/optimal` — run the Monte Carlo search and return the best strategy found, for the debrief screen
- **`web/`** — a React + Vite + TypeScript frontend. No codegen: `web/src/api/types.ts` and `api/schemas.py` both mirror `sim/types.py`'s dataclasses by hand, so keep them in sync manually if the Python side changes shape.
- **`tests/`** — pytest suite for `sim/` and `api/`.

## Requirements

- Python 3.13
- Node.js v24 (LTS) or similar

## Running it

### Backend (sim + api)

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn api.main:app --reload   # serves on http://127.0.0.1:8000
```

### Frontend (web/)

```
cd web
npm install
npm run dev      # serves on http://localhost:5173, expects the API on http://127.0.0.1:8000
```

If `node`/`npm` aren't on your `PATH`, install Node without root (e.g. the official tarball extracted somewhere under your home directory) and add its `bin/` to `PATH`.

## Testing

```
.venv/bin/pytest              # 159 tests
.venv/bin/mypy --strict sim/
cd web && npx tsc --noEmit && npm run lint
```

There's no headless-browser test runner wired up for the frontend; UI changes are verified by manual playthroughs against a live `uvicorn`/`vite` pair and by rendering representative markup to check layout.

## The Monte Carlo optimal-strategy search

`sim/optimal.py` samples random candidate strategies (pit laps, compounds, a push policy, reactive choices per event type) and keeps the lowest total race time, reusing the same `run_to_next_decision()` the real race uses so there's no duplicated lap-time logic. It's pure Python and not vectorized, so it isn't instant: at the shipped default of `n_samples=500` it takes roughly 39 seconds, which is why the debrief screen fetches it asynchronously behind a loading state rather than blocking on it.

## Possible future work

- Calibrate degradation curves and pit loss from real FastF1 session data
- More tracks
- Rivals that react to the player instead of running fixed plans
- Vectorize the Monte Carlo search with numpy for a faster debrief
