# F1 Race Strategy Game

A lap-by-lap F1 race strategy game. See [CLAUDE.md](CLAUDE.md) for the full spec.

## Backend (sim + api)

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest
.venv/bin/mypy --strict sim/
```

## `sim/optimal.py` Monte Carlo search — runtime

Pure-Python, non-vectorized, one race simulation per candidate strategy. Measured on the dev machine:

- ~78ms per candidate.
- `n_samples=2000` (the originally planned default): **~156s**. Too slow for a synchronous API call, so the shipped default was lowered.
- `n_samples=200`: **~15.8s**.
- `n_samples=500` (current default): **~39s**.

A future numpy-vectorized rewrite (see CLAUDE.md's "Later" section) should batch candidates instead of looping in Python, which is the main target for speeding this up. At ~39s, `/race/optimal` will need a loading state in the frontend (Stage 22) rather than feeling instant.
