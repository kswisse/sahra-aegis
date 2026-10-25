# Essay skeleton

Target: 1,200-1,500 words, English, for a non-technical judge reading once. Each section below
lists what it must establish, the numbers it is allowed to use (with their `docs/claims.md`
row id), and the sentence it must not write. Draft in this order; the opening is written last.

## 1. The problem (150 words)

- Dubai heat is managed at city scale, but exposure happens at one school gate or one work
  site. A city-wide average cannot tell a coordinator whether to move a football session.
- The regulatory instrument already exists: the MOHRE midday ban, 15 June-15 September,
  12:30-15:00 (`docs/claims.md` note 3). It is a blanket window, not a per-zone decision.
- The gap is not data, and not another dashboard. It is the loop between a reading and an
  action that someone is accountable for.
- **Do not write:** any claim that children or workers were harmed, or any number of heat
  illnesses. No such series exists in the UAE, and inventing one ends the submission.

## 2. What SAHRA decides (250 words)

- One cycle, six roles, one transcript: monitor reads, predict bands the heat stress, the
  arbiter settles a disagreement between sources, plan proposes, act executes through a human
  gate, verify checks the invariants. Cite the worked cycle: site 29.0 °C vs weather 31.1 °C,
  ruling 31.1 °C, three interventions, `verify: ok` (C12, C11).
- The decision is a typed object, not prose: an intervention kind, an evidence link, a reason
  trace, and an accountable approver for anything consequential.
- Threshold contract: 28 °C WBGT, bands 28/30/32 (C2). Weights are a design choice, not a
  measurement (C3) - say so in the same sentence.
- **Do not write:** "the agent decides autonomously". Consequential actions are refused
  without an approver (C10).

## 3. Why six roles and not one loop (200 words)

- The architecture was chosen on published evidence, not taste: a controlled 270-run study
  found LLM-orchestrated multi-agent control losing reliability to coordination failures
  (74.44%) while deterministic orchestration recovered most of it (93.33%), against a 94.44%
  single-agent baseline (C1).
- Honest reading: the single agent scored highest. SAHRA takes the deterministic plane for
  replayability and auditability, and the multi-agent split for separations of duty a single
  prompt cannot provide - the verifier must not be the agent it verifies.
- Cost is part of it: the LLM-orchestrated arm needed far more model calls and latency (C1).
  SAHRA's control path needs none.
- **Do not write:** "outperforms all architectures", or "proven". One preprint, phrase it as
  a controlled study.

## 4. How it is validated (250 words)

- Method: replay archived Dubai weather, anchor on externally dated events. The anchors fix
  *when* to look, never *what the outcome was* (spec §12).
- Anchor 1 - MOHRE window: the 2026-07-01 fixture peaks at 31.4 °C at 11:00, `high` band
  (C6), and the replay check asserts the midday sample inside the ban window bands `high` or
  worse. A decision the regulation would recognise, produced without reading the regulation.
- Anchor 2 - NCM record days: the replay file carries three station readings (51.6 / 46.6 /
  50.0 °C) and three reanalysis grid samples that sit below them; the highest row is 33.7 °C
  at 13:00 (C9). The grid is a coverage input, not evidence about people.
- Regression: 145 tests (C4), three byte-identical golden transcripts (C5), and the
  conservative-max ruling reproduced from the transcript (C12).
- **Do not write:** "validated against health outcomes", or any accuracy percentage for
  SAHRA itself. Nothing in the repo measures that.

## 5. What it cannot show (150 words)

- No per-event UAE heat-illness feed exists, so the anchors are regulatory and record-day
  facts, not outcomes. ISO 7243 is a screening ceiling: presence or absence of heat stress,
  not prediction of harm (C2, note 4).
- Satellite LST is used as a sanity check only - a reading far above air temperature is
  flagged, not acted on.
- The engine reports decision latency and action uptake. It does not report avoided harm.
  Every run ends with that sentence (C11).
- **Do not write:** "saves lives", "reduces heatstroke", or any projected percentage.

## 6. The human gate (150 words)

- A consequential intervention without an approver is refused, not downgraded: the action
  record says `refused` with a `gate_reason`, the queue holds one open request per zone and
  kind, the cycle continues (C10).
- Why: a school cannot be told to cancel a day by a rules engine alone, and the refusal is
  the auditable part. Eight refusals, one pending request, eight audit records.
- The verifier checks that no refused action lacks a reason (invariant 3).
- **Do not write:** "minimal human oversight". The oversight is the product.

## 7. Dubai deployment path (150 words)

- Phase 1 - replay mode, offline, no integration: what the repo does today (C4, C5).
- Phase 2 - one school zone with its own site sensor, the weather tier as fallback, MOHRE
  window still the ground rule. The engine already prefers the higher of two disagreeing
  tiers (C12), which is the behaviour a second source requires.
- Phase 3 - operator view over the audit log and approval queue; the queue is the only new
  surface.
- Costs and gates: no PII, zone-level aggregation only; nothing leaves the operator's
  machine in phase 1.
- **Do not write:** a rollout date, a partner name, or a savings figure. None is agreed.

## 8. Close (100 words)

- One sentence on the loop: reading → decision → approver → audit → verify.
- One sentence on the boundary: screening, not a health outcome (C11).
- One sentence on what a judge can run in three minutes: the transcript, the day, the audit
  tail (`docs/demo-script.md`).

## Checks before the essay leaves the machine

- Every number has a row id, and no row id is `unverified`.
- No sentence asserts a health outcome, a saving, or a partner.
- The single-agent caveat in C1 appears once, plainly, and is not buried.
- English only; no em dashes if the portal's form mangles them; no tables if the form strips
  them.
