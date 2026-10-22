# SAHRA — Create AI Agents Championship submission checklist

Status: engine complete @ `ff30f31` (main, 99 tests, offline demo + replay).
Checked against verified competition facts as of 2026-10-20. `UNKNOWN` items
need a source before they gate anything — do not act on guesses.

## Competition facts (verified 2-source)

- 4 categories × USD 150,000, non-dilutive. SAHRA targets **Youth** (lead < 21)
  + **Societal**.
- Entry free, team ≤ 6, English-only artifacts.
- Registration opened 07/10/2026, expected close ~01/2027; Grand Final ~05/2027.
- Grand Final requirement: **"fully functional, working AI Agent on stage —
  not just an MVP."** SAHRA's offline demo + replay path exists; treat this as
  the binding bar, not the essay.
- **Originality rule:** "must not be copied or taken from an existing
  repository." Git history from root scaffold `6b65374` is the provenance
  record; keep it intact.

## Track A — Registration (human, do first)

- [ ] **TODO** Register at the official portal; capture confirmation + code.
- [ ] **TODO** Confirm which legal category name the form wants (Youth vs
      Young Innovators — wording may differ from the brief).
- [ ] **UNKNOWN→gate** Verify whether the form needs the lead's age proof
      < 21 (ID/passport) — have it ready, it's a fixed fact.
- [ ] **UNKNOWN** Whether team members may be added after registration.

## Track B — Technical deliverable (agent-owned)

Engine:
- [x] Deterministic 5-agent cycle, human-in-the-loop gate, append-only audit —
      all reviewed + tested (99 passing).
- [x] Offline demo: `.venv/Scripts/python -m sahra.demo`
- [x] Validation replay with external anchors (MOHRE window, NCM records):
      `python -m sahra.replay` — survives `python -O`.
- [x] Setup script `scripts/bootstrap.py` — one command from a clean clone
      (creates the venv, installs the project, runs the suite).
- [ ] **TODO** One-page architecture sheet with the annex claim
      (deterministic 93.33% vs LLM-orchestrated 74.44%) sourced to the paper.
- [x] Demo script `scripts/demo_day.py` — staged, screen-recordable, ≤ 3 min,
      English-only — hazardous day → proposal → approval → audit line.

Narrative:
- [ ] **TODO** Essay skeleton from spec §12, keeping the POV-v2 relabels:
      MOHRE ban = intervention under evaluation (not an outcome label); anchors
      are "externally dated"; ISO 7243 = screening ceiling.
- [ ] **TODO** Impact numbers: cite the decision metrics (latency/uptake), not
      health outcomes — scope line `demo.py` already carries.
- [ ] **TRACK/FIX-TIME** Replay gaps from the ledger: fixture is 13:00 only
      (exposure peak 09:00–12:00); "cycle continues past refusal" not
      test-locked; corrupt-fixture handling. Fix before Grand Final, not
      before registration.

## Track C — Legal / financial (human, flagged UNKNOWN — do not assume)

- [ ] **UNKNOWN→gate** Winner requirements from DCDE precedent: Dubai trade
      license + UAE bank account. For a UAE-resident minor: UAE Falcon
      license-equivalent path and Decree-Law 50/2022 ownership age (now 18)
      need source confirmation.
- [ ] **UNKNOWN** Whether prize payout rules changed vs the Create Apps
      precedent (third-party Fund Manager clause).
- [ ] **UNKNOWN** Official T&C of this championship — **not yet published**.
      Re-check the portal before acting on Track C.
- [ ] **UNKNOWN** PDPL child-data handling age (16 vs 18) — matters only if
      the demo touches any person-level data; keep the dataset zone-level
      (it already is) to sidestep this entirely.

## Reviewer-borrowed safety rules (carried for the submission review)

1. Do not claim WBGT bands are validated health thresholds — they are an
   ISO-derived screening cell for an occupational trigger.
2. Every number in the essay must trace to `replay.py` output or a cited
   source — no invented stats.
3. The "refused, never downgraded" behavior is the demo's strongest
   differentiator; show it on stage.
