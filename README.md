# SAHRA

Rules-based multi-agent heat-stress decision engine for Dubai — schools and
outdoor workforces. SAHRA monitors weather, derives WBGT heat stress, plans
interventions, enforces human approval for consequential actions, and logs
every decision to an append-only audit.

Built for the Create AI Agents Championship (Dubai Chamber of Digital Economy).

## Why deterministic

SAHRA's control plane is a typed state machine — no LLM anywhere in the
decision path. An LLM may only render text in `channels/`. This follows the
evidence that deterministic agent orchestration outperforms LLM-orchestrated
control at equal capability (93.33% vs 74.44% in the benchmark that decided
this architecture; single-agent baseline 94.44%).

## Architecture

Five agents over one deterministic cycle (`run_cycle` in
`src/sahra/orchestrator.py`):

| Stage | Module | Role |
|-------|--------|------|
| Monitor | `sensors/` | weather / site / satellite providers, tiered sourcing with offline fixtures |
| Predict | `fusion.py`, `risk.py` | fusion into `HeatState`; WBGT in two forms — ISO 7243 outdoor (Dimiceli globe term) and a no-solar fallback (`0.7·Tw + 0.3·Ta`, Stull 2011 wet-bulb) |
| Plan | `planner.py` | evidence-linked interventions: ADVISE → SHIFT_ACTIVITY → ACTIVATE_COOLING → ESCALATE |
| Act | `gate.py` | approval gate: a consequential intervention without an approver is **refused, never silently downgraded** |
| Verify | `audit.py` | append-only JSONL log; every action carries a `reason_trace`; no PII |

Contract: occupational WBGT threshold **28 °C**; bands `<28` low / `28–30`
moderate / `30–32` high / `≥32` extreme; vulnerability weights `school=1.0`,
`outdoor_worker=1.05`.

## Run

```bash
.venv/Scripts/python -m pytest -q          # 65 tests
.venv/Scripts/python -m sahra.demo         # end-to-end cycle, offline
.venv/Scripts/python -m sahra.replay       # 6-day Dubai replay + validation claims
```

Dependencies: Python ≥ 3.11, pydantic ≥ 2.6. No geospatial or LLM library.

## Validation evidence

`python -m sahra.replay` replays real archived Dubai weather from committed
fixtures (`data/dubai_replay.json`) and prints five claims:

1. **External anchor** — the 2026-07-01 engine output falls inside the MOHRE
   statutory midday-ban window (published regulation).
2. **External anchor** — official NCM station records (51.6 / 46.6 / 50.0 °C)
   asserted as an upper bound the reanalysis cannot exceed.
3. **Screening ceiling** — ISO 7243 outdoor WBGT ≥ no-solar fallback on the
   solar day (formula-internal, regression guard).
4. **Screening ceiling** — both forms band identically at the threshold
   (regression guard).
5. **Record-day refutation** — the 51.6 °C record-air-temp day bands *moderate*
   at 5 % RH while a 44.4 °C grid day bands *extreme*: record air temperature is
   not a heat-stress label.

Claims 1–2 are externally dated; claims 3–4 are formula-internal and framed as
what they are — screening/regression checks, not outcome labels. Validation
runs survive `python -O` (assertions are explicit raises; "OK" is earned, not
printed for free).

## Scope limits

- The system measures *decision latency and action uptake*, not health
  outcomes.
- Site sensors and satellite LST are offline stubs returning sane defaults;
  absence is normal and modeled as `None`.
- The audit log is append-only but has no fsync guarantee (in-process durability).
