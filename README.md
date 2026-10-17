# SAHRA — Smart Adaptive Heat-Response Agent

An autonomous multi-agent system that turns urban heat data into timed, targeted
heat-protection actions for schoolchildren and outdoor workers in Dubai.

Heat risk in Dubai is knowable hours in advance and the mitigating actions already
exist in law; what is missing is the layer that decides *where and when* risk is
highest and *which* action should fire, then records whether the action changed
anything. SAHRA is that layer.

## What it does

- **Monitor** — fuses satellite land-surface temperature, gridded weather, and
  on-site WBGT sensor readings into one heat state per zone.
- **Predict** — scores risk per zone and per population group on the WBGT index
  (occupational threshold 28°C).
- **Plan** — selects interventions from the evidence-backed set: advisory,
  activity shift, cooling activation, escalation.
- **Act** — dispatches through the zone's own channel, with a human approval gate
  on every consequential action.
- **Verify** — records what was recommended, accepted, and what followed.

## Design position

The orchestrator is a **deterministic, typed state machine**. A controlled
evaluation found single-agent systems reaching 94.44% task success against 74.44%
for LLM-orchestrated multi-agent systems, with deterministically orchestrated
systems recovering to 93.33%. LLMs therefore render text and nothing else; they
never select or authorise an action.

Public claims are limited to decision latency and action uptake. The causal effect
of heat messaging on health outcomes is not yet established in the literature, and
the system does not assert it.

## Layout

```
src/sahra/          core: contracts, fusion, risk, planner, gate, audit, orchestrator
src/sahra/sensors/  satellite / weather / site providers
src/sahra/channels/ outbound advisories and the operator view
tests/              pytest
```

## Development

```
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m pytest
.venv\Scripts\python -m sahra.demo
```

## Background

Design specification: `../docs/superpowers/specs/2026-10-17-sahra-design.md`
Implementation plan: `../docs/superpowers/plans/2026-10-17-sahra-implementation.md`
