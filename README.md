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

Two modules sit across the cycle rather than inside it: the **day supervisor**
drives `run_cycle` once per hour over an archived day, and the **approval
queue** is where a refusal waits for a human.

## The time axis: the day supervisor

`src/sahra/supervisor.py` runs one control cycle per hour over a committed
archived day and returns a `DayTimeline`: 24 `HourlyStep`s, each carrying the
WBGT, the band, the kinds dispatched for the first time that day, the kinds
dispatched earlier today that the planner proposed again in this same hour, and
the status of each. A day reads as a rising curve rather than 24 repetitions of
the same advisory — a kind dispatched at 09:00 and proposed again at 14:00 is
listed under `active_kinds`, not re-listed as a new dispatch. `active_kinds`
is a display rule, not a deactivation: a kind leaves the timeline at the hour
the planner stops proposing it, because the band moved. Every action of every
hour is appended to the audit; nothing is filtered.

```bash
.venv/Scripts/python scripts/demo_day.py                                   # the extreme day
.venv/Scripts/python scripts/demo_day.py --fixture data/dubai_hourly_2026-07-01.json
```

The demo prints the hour-by-hour table, the escalation refused for want of an
approver, the coordinator's approval of it, and the tail of the append-only
audit — offline and deterministic, with the fixture's dataset and source URL
in the header.

## The approval queue

`src/sahra/hitl.py` is where the human decision lives. A consequential
intervention refused for want of an approver is opened as a pending request;
the coordinator's decision is appended to the same append-only audit as a new
record, and the original refusal is never rewritten. `ActionRecord.status` is
narrowed to `executed | refused` — the only two outcomes the orchestrator and
the queue produce — so an unexpected outcome fails loudly instead of quietly
changing what the verification line means.

## One-command setup

```bash
python scripts/bootstrap.py
```

Stdlib only: creates `.venv` if it is missing, installs the project into it
(`pip install -e .`), installs the test runner, and runs the suite. It prints
every command it ran and the final test line. The only network it needs is
PyPI, for pydantic and pytest.

## Run

```bash
.venv/Scripts/python -m pytest -q            # 94 tests
.venv/Scripts/python scripts/demo_day.py     # one archived day, hour by hour
.venv/Scripts/python -m sahra.demo           # end-to-end cycle, offline
.venv/Scripts/python -m sahra.replay         # 6-day Dubai replay + validation claims
```

Dependencies: Python ≥ 3.11, pydantic ≥ 2.6. No geospatial or LLM library.

## Fixture provenance

| Fixture | Dataset | Date | Peak WBGT | What it is for |
|---------|---------|------|-----------|----------------|
| `data/dubai_hourly_2026-08-13.json` | ECMWF ERA5 reanalysis, hourly, 10 m wind and 2 m temperature (Open-Meteo historical archive; CC BY 4.0 / Copernicus) | 2026-08-13 | **34.5 °C** at 14:00 local — `extreme` | the extreme day: the band is crossed, so the escalation path, the refusal and the approval all run on archived data |
| `data/dubai_hourly_2026-07-01.json` | same | 2026-07-01 | **31.4 °C** at 11:00 local — `high` | a full diurnal day that **never escalates**: the peak stays under the 32 °C extreme threshold, so no approval is needed |
| `data/dubai_replay.json` | Open-Meteo historical archive (ERA5-backed), one 13:00-local row per place; three rows also carry the NCM station reading | 2025-04-27 → 2026-08-05 | highest row 33.7 °C at 13:00 — `extreme` (`dubai-2026-08-05`); the file holds one row per day, not a diurnal day | the labelled replay checks: the MOHRE-window row, an off-season control row, and three reanalysis-vs-station comparisons |

Every committed fixture is **reanalysis, not station observation**. They are
coverage inputs: they let the engine be exercised and checked offline, and
they can support a statement about *what the engine does*. **No fixture is an
external anchor.** The only external anchors in this repository are the
published MOHRE midday-ban regulation and the official NCM station readings —
and they anchor claims about the engine's *output* (which band a day lands in),
never about health.

## Validation evidence

`python -m sahra.replay` replays real archived Dubai weather from committed
fixtures (`data/dubai_replay.json`) and prints five claims:

1. **External anchor** — the 13:00 row `dubai-2026-07-01-mohre` in
   `data/dubai_replay.json` falls inside the MOHRE statutory midday-ban
   window (published regulation). That is the replay fixture's midday row, not
   the hourly fixture `data/dubai_hourly_2026-07-01.json`, which is a coverage
   input that never escalates.
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
- The committed fixtures are reanalysis coverage inputs, not observations, and
  no claim about health, mortality or intervention efficacy may be derived
  from them.
