# CLAUDE.md

Race strategy game. The race runs lap by lap, pauses at decision points after key events (rain, heavy tire degredation, opponent pits, damage, safety car, overtaken), the player picks (pit/no pit, push harder,  and what wheel if pitting), the race continues. After the finish, the app shows how the player's choices compare to the best strategy the sim can find. Should be a 20 car race, with player controlling one.

## Non-negotiables

- The simulation is a pure function. `step(state, decision, seed) -> (state, events)`. No classes that hold race state, no module globals, no I/O inside the sim.
- The server is stateless. No sessions, no database, no files written per request. Every request carries the full race state. The browser owns state and saves it to localStorage.
- Same state + same seed = same outcome. Every random draw goes through an RNG seeded from `state.seed` and the current lap. Never call `random.random()` directly.
- Keep the state blob small. Target under 5 KB serialised. If it grows, ask before adding fields.
- Python 3.13, typed. `mypy --strict` on `sim/`. Tests in `pytest`. (Originally pinned to 3.12; bumped to match the only interpreter available on the dev machine — no 3.12 install found, no brew/pyenv present.)
- No Streamlit. Frontend is React + Vite + TypeScript.

## Layout

```
sim/            pure Python, no framework imports
  model.py      lap time, degradation, pit loss, weather
  race.py       step(), event detection, 19 rival AIs
  optimal.py    Monte Carlo search over strategy tree
  types.py      dataclasses for State, Car, Decision, Event
api/            FastAPI, thin wrappers around sim/
web/            React app
tests/
scripts/        offline calibration from FastF1 (later)
```

`api/` may import `sim/`. `sim/` imports nothing from `api/` or `web/`.

## API

- `POST /race/new` body `{track, seed}` returns initial `State`
- `POST /race/step` body `{state, decision}` runs laps until the next event or the finish, returns `{state, laps: [...], event}`
- `POST /race/optimal` body `{track, seed}` returns the best strategy line and per-lap positions, for the debrief screen

`laps` is the per-lap trace the client animates through. `event` is `null` on finish or one of the four decision types.

## Model v1 (hand-tuned, calibrate later)

Lap time per car:

```

lap_time = base (different car choices have different base times)
         + fuel_effect(lap)                       # linear, lighter car is faster
         + tyre_deg(compound, age)                # linear + cliff after N laps
         + weather_penalty(compound, wetness)     # slicks in rain are very slow
         + noise(rng)                             # small, seeded
```

Pit loss is random (18 to 30s) but majority fall in average (20 to 22s). Compounds: soft, medium, hard, inter, wet. Keep parameters in one dict in `model.py` so calibration can overwrite them.

Rivals run fixed plans, determined from start position and car base speed(one stop, two stop, reactive to rain). They do not react to the player in v1.

## Decision and Event types

Events with decisions:
1. `rain_start`: stay out on slicks (slower time and higher damage chance depending on rain amount) / inter / wet
2. `damage`: pit with extended fixing period / stay out with extened base time 
3. `overtaken`: push to retake with higher tyre degredation and faster lap time/ keep position and speed
4. `safety_car`: pit under SC - Soft, Medium, Hard / hold position
5. `pitting opportunity`: pit - Soft, Medium, Hard / stay out (push option for both choices for one lap) - mentions what opponents have pitted ahead

Should have a pre chosen pit strategy pre race, but can choose to pit on recommeneded laps or laps close to strategy non dependent of whether opponents pit or not. Include push option at all time, not just events. 



Each has a detector in `race.py` and a fixed set of options. 

## Frontend

- Race view: lap counter, gap board, tyre icons with wear levels, weather badge with rain amount, large visual race map with moving car icons. Ticks through `laps` at a fixed interval, pauses on `event`. The track map is a core part of the experience, not an optional visualisation. When the simulation is running, cars should visibly move around the track.
When a decision event occurs, pause the animation and show a prominent decision panel.

Example:
- Decision modal: shows the options from the event, nothing else. No hints in v1.
- Debrief: finish position, then per-decision delta vs `/race/optimal`.
- Save/resume from localStorage on load. One race at a time.

Ask for reference pictures before development.

## End of Race

Show:

- Finishing position
- Starting position
- Number of pit stops
- Tyre strategy
- Key decisions
- Time gained/lost from decisions
- A simple strategy rating

The debrief should explain major decisions, e.g.:

"You gained 8.4 seconds by pitting under the Safety Car."

"Your PUSH period gained 2.1 seconds but caused an additional 3.7 seconds of tyre degradation."

## Working style

- Small PRs, one concern each.
- Write the test before the feature for anything in `sim/`.
- Run `pytest` and `mypy` before saying a task is done.
- Do not add dependencies without asking. Current: fastapi, uvicorn, numpy, pytest, mypy.
- If unsure whether something belongs in the sim or the API, it belongs in the sim.

## Later (do not start until v1 is deployed)

- Calibrate deg curves and pit loss from FastF1 sessions (`scripts/`)
- More tracks
- Rivals that react to the player
- Vectorise Monte Carlo with numpy, put runtime numbers in the README
