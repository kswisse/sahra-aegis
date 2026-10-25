# Claims ledger

Every number that appears in `README.md`, `docs/submission-checklist.md`, the essay, or the
demo narration resolves to one row here. If a number is not in this table, it does not ship.

Classes: `engine-output` (reproduced by a command in this repo), `external` (a source a
reader can open), `unverified` (must be rewritten or deleted before submission).

| id | claim | where it appears | class | evidence | action |
|----|-------|------------------|-------|----------|--------|
| C1 | Deterministic orchestration 93.33% task success vs 74.44% LLM-orchestrated, single-agent baseline 94.44%, over 270 runs (30 tasks x 3 repetitions) | `README.md` "Why deterministic"; design spec s5 | external | Malik & Qureshi, *Do Multi-Agent LLM Systems Actually Help? A Controlled Evaluation of Single-Agent, LLM-Orchestrated, and Deterministically Orchestrated Architectures*, Zenodo preprint, 25 Sep 2026, doi:10.5281/zenodo.22957164. PDF p.7: "System A passed 85 of 90 runs (94.44%). System B passed 67 of 90 (74.44%). System C passed 84 of 90 (93.33%)." | keep, cite DOI, and state that the single agent scored highest (see note 1) |
| C2 | Occupational WBGT threshold 28 °C; bands <28 low / 28-30 moderate / 30-32 high / >=32 extreme | `README.md` contract; `src/sahra/risk.py` | external | research note `outdoor-occupational-environments-and-heat-stress-in-iran-journal-of-environment` (J Environ Health Sci Eng); ISO 7243 is the screening standard named in the design spec | keep |
| C3 | Vulnerability weights `school=1.0`, `outdoor_worker=1.05` | `README.md` contract; `src/sahra/risk.py` | engine-output | design choice, not a measured value: asserted in `tests/test_risk.py` ordering tests | keep, and never present as evidence |
| C4 | 145 tests | `README.md` "Run it" | engine-output | `python -m pytest -q` -> `145 passed` | keep |
| C5 | 3 golden transcripts byte-identical | `README.md` regression section; `tests/test_golden.py` | engine-output | `python -m pytest tests/test_golden.py -q` -> `3 passed` | keep |
| C6 | 2026-07-01 fixture peaks at 31.4 °C at 11:00 local, `high` band, no escalation | `README.md` fixture table | engine-output | `python scripts/demo_day.py --fixture data/dubai_hourly_2026-07-01.json` -> `Peak WBGT 31.4 C at 11:00 local (high band).` and `No escalation was raised on this day` | keep |
| C7 | That run writes 57 audit records | `README.md` demo walkthrough | engine-output | same command -> `Audit tail (last 8 of the 57 records this run wrote; the log is append-only)` | keep |
| C8 | 2026-08-13 extreme fixture peaks at 34.5 °C at 14:00 local and writes 69 records | `README.md` fixture table | engine-output | `python scripts/demo_day.py` -> `Peak WBGT 34.5 C at 14:00 local (extreme band).` and `69 records` | keep |
| C9 | Highest replay row is 33.7 °C at 13:00 (`dubai-2026-08-05`) | `README.md` fixture table | engine-output | `python -m sahra.replay` -> `dubai-2026-08-05-grid-extreme 44.4 33.66 ... extreme` (33.7 is the rounded value) | keep, print 33.66 when a second decimal matters |
| C10 | One open approval request per zone and kind, all refusals kept in the audit | `README.md` "Escalation"; `docs/architecture-one-page.md` | engine-output | `python scripts/demo_day.py` -> `one open request per zone and kind: <id> (kind escalate)`; `python -m sahra.demo` -> `escalate -> refused`, `verify: ok` | keep |
| C11 | Every cycle ends with `verify: ok` and a scope sentence | `README.md`; demo narration | engine-output | `python -m sahra.demo` -> `verify: ok; 4 actions decided, 3 actions executed, 1 refused pending human approval; claim limited to decision latency and action uptake, not health outcome` | keep |
| C12 | The school-vs-weather conflict resolves to the higher reading (`conservative-max`) | `README.md` worked cycle; `docs/architecture-one-page.md` | engine-output | `python scripts/agent_transcript.py` -> `ruling: tiers disagree: site 29.0 C vs weather-outdoor 31.1 C, gap 2.1 C; chose the higher, conservative 31.1 C from weather-outdoor` | keep |

## Notes

1. **C1 as reported by the source.** The deterministic arm (93.33%) beat the LLM-orchestrated
   arm (74.44%) but not the single-agent baseline (94.44%); the paper attributes the
   LLM-orchestrated loss to coordination failures that destroyed authoritative state, and the
   deterministic arm's own weakness to reduced flexibility on conditional instructions
   (limitations section). SAHRA's reason for the deterministic plane is therefore reliability
   plus replayability, not a claim that it beats every alternative. Do not write "outperforms
   all architectures".
2. **C1 is one preprint, not a consensus.** Not peer reviewed, no citing works at the time of
   writing. Phrase it as "a controlled 270-run study" and never as "proven". The same three
   percentages also appear in MaCTG's Table 1 as *different* metrics (94.44% total Pass@5,
   74.44% for an ablated variant, 93.33% for one subset), so a reader who has seen both papers
   may ask. Answer with the DOI and the run counts: 85/90, 67/90, 84/90.
3. **External anchors stay external.** The NCM station readings in `data/dubai_replay.json`
   (51.6 / 46.6 / 50.0 °C) are the source's numbers, recorded as fixture input; the engine's
   output for those days is C9 and the replay checks. Never present a station record as an
   engine result, and never present an engine result as an observed temperature.
4. **No health outcomes.** Every run report ends with the scope sentence in C11. Keep it in the
   demo narration; it is the claim boundary, not boilerplate.
5. **Re-verify the engine rows** with the commands above after any change to the engine. A
   stale count here is worse than no count.
