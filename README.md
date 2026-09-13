# F1 Race Strategy Game

A lap-by-lap F1 race strategy game. See [CLAUDE.md](CLAUDE.md) for the full spec.

## Backend (sim + api)

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest
.venv/bin/mypy --strict sim/
.venv/bin/uvicorn api.main:app --reload   # serves on http://127.0.0.1:8000
```

## Frontend (web/)

Requires Node.js (v24 LTS or similar). If `node`/`npm` aren't on your PATH, this repo was built against a user-local install at `~/.local/node-v24.21.0` (no sudo) with `export PATH="$HOME/.local/node-v24.21.0/bin:$PATH"` in `~/.zshrc`.

```
cd web
npm install
npm run dev      # serves on http://localhost:5173, expects the API on http://127.0.0.1:8000
npm run build    # tsc -b + vite build
npm run lint
```

`web/src/api/types.ts` and `web/src/api/client.ts` are hand-written to mirror `sim/types.py`/`sim/optimal.py` and `api/schemas.py` — no codegen, so keep them in sync by hand when the Python side changes shape.

## `sim/optimal.py` Monte Carlo search — runtime

Pure-Python, non-vectorized, one race simulation per candidate strategy. Measured on the dev machine:

- ~78ms per candidate.
- `n_samples=2000` (the originally planned default): **~156s**. Too slow for a synchronous API call, so the shipped default was lowered.
- `n_samples=200`: **~15.8s**.
- `n_samples=500` (current default): **~39s**.

A future numpy-vectorized rewrite (see CLAUDE.md's "Later" section) should batch candidates instead of looping in Python, which is the main target for speeding this up. At ~39s, `/race/optimal` will need a loading state in the frontend (Stage 22) rather than feeling instant.
