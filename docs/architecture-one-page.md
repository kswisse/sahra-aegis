# SAHRA in one page

**Determinism contract.** One cycle = one typed transcript. Given the same fixture and the
same approver, `run_cycle` replays byte-identically (`tests/golden/`, three transcripts). No
LLM sits in the decision path; an LLM may only render text in `channels/`.

## The six roles

| Role | May emit | Job in the cycle |
|------|----------|------------------|
| `monitor` | `observation` | reads the tiered sources (weather, site, satellite) and hands on one `HeatState` plus both WBGT readings when the tiers disagree |
| `predict` | `assessment`, `dispute` | fuses the observation, computes WBGT and the weighted risk score, bands it; raises a dispute instead of silently picking a tier |
| `arbiter` | `ruling` | settles a dispute under one policy, `conservative-max` |
| `plan` | `proposal` | turns the assessment into evidence-linked interventions, tagging a repeated refusal with the request that already covers it |
| `act` | `decision` | executes each intervention through the approval gate and records the outcome per action |
| `verify` | *(nothing)* | reads the finished transcript, reports findings, rewrites nothing |

Message kinds are closed: `observation`, `assessment`, `dispute`, `ruling`, `proposal`,
`decision`, `verification`. Each kind binds to exactly one payload model, so a `proposal`
cannot carry a ruling's payload (`protocol.py`).

## How a cycle runs

`AgentCoordinator.run(seed)` is a synchronous FIFO queue. It pops one message, appends it to
the transcript, hands it to the recipient, and queues whatever the recipient replies. Three
things abort the cycle as a `ProtocolViolation` rather than being tolerated: an unregistered
sender or recipient, and an agent emitting a kind outside its `emits` set. There is no
concurrency, no retry, and no broker - which is what makes the transcript the audit record
instead of a log of it.

**Conservative-max.** The arbiter's ruling payload carries `chosen_c` and the policy name.
When the site sensor and the weather model disagree by more than 1.0 °C the forecast runs on
the higher reading and names both in `reason_trace`. The verifier independently rejects a
ruling that lands below the maximum of the disputed readings, so the rule is checked rather
than trusted.

**Blackboard.** Between hours the supervisor syncs the approval queue into a per-zone
blackboard. Plan looks up `(zone, intervention kind)`; if a request is already open it tags
the new proposal with `linked_request` instead of filing a duplicate. One open request per
zone and kind, refreshed to the worst reading; every refusal stays in the audit.

## Five invariants the verifier checks

1. Every proposed intervention kind has a decision in the same cycle.
2. No `action_id` appears twice.
3. A refused action carries a `gate_reason=` in its `reason_trace`.
4. Each dispute has exactly one ruling, and no ruling exists without a dispute.
5. A ruling never chooses below the maximum of the disputed readings.

Findings are reported; the decisions they describe are already written and are never
rewritten. `verify: ok` means "no invariant broke", not "the decision was right".

## One worked cycle (`school-dxb-003`, 2027-07-14 13:00 UTC)

```
monitor -> predict : observation : wbgt 29.0 C from site
predict -> arbiter : dispute     : site 29.0 C vs weather-outdoor 31.1 C (gap above 1.0 C)
arbiter -> predict : ruling      : conservative-max, chose the higher 31.1 C
predict -> plan    : assessment  : wbgt 31.1 C; level=high; score=0.617
plan    -> act     : proposal    : shift_activity, activate_cooling, advise
act     -> verify  : decision    : 3 actions, all executed
verify             : ok
```

Reproduce with `python scripts/agent_transcript.py`.

## The human gate and the evidence boundary

A consequential intervention without an approver is **refused, never silently downgraded**:
the action record says `refused` with a reason, the approval queue keeps one open request, and
the rest of the cycle continues. What the engine measures is decision latency and action
uptake - whether a hazardous hour produced a decision and whether that decision was carried
out. It does not measure health outcomes, and the fixtures are reanalysis and station records,
not people. Every run report prints that boundary.
