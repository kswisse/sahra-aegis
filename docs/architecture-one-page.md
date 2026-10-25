# SAHRA in one page

**Determinism contract.** One cycle = one typed transcript. Given the same fixture and the
same approver, `run_cycle` produces the same decisions and the same trace text every run; the
only fields that differ between runs are the generated action/request ids and the approval
timestamp, and the golden tests normalise exactly those. No LLM sits in the decision path; an
LLM may only render text in `channels/`.

## The six roles

| Role | May emit | Job in the cycle |
|------|----------|------------------|
| `monitor` | `observation` | reads the tiered sources (weather, site, satellite), fuses them into one `HeatState`, and hands on both WBGT readings when it has them |
| `predict` | `assessment`, `dispute` | fuses the observation, computes WBGT and the weighted risk score, bands it; raises a dispute instead of silently picking a tier |
| `arbiter` | `ruling` | settles a dispute under one policy, `conservative-max` |
| `plan` | `proposal` | turns the assessment into evidence-linked interventions, tagging a repeated refusal with the request that already covers it |
| `act` | `decision` | executes each intervention through the approval gate and records the outcome per action |
| `verify` | *(nothing)* | reads the finished transcript, reports findings, rewrites nothing |

Message kinds are closed: `observation`, `assessment`, `dispute`, `ruling`, `proposal`,
`decision`, `verification`. Each kind binds to exactly one payload model, so a `proposal`
cannot carry a ruling's payload (`protocol.py`). `verification` is the verifier's return
value, not a message any role emits - the verifier's `emits` set is empty, so it appears in
the transcript only as a finding list attached to the cycle.

## How a cycle runs

`AgentCoordinator.run(seed)` is a synchronous FIFO queue. It pops one message, appends it to
the transcript, hands it to the recipient, and queues whatever the recipient replies. Four
things abort the cycle as a `ProtocolViolation` rather than being tolerated: an unregistered
sender, an unregistered recipient, an agent emitting a kind outside its `emits` set, and a
reply claiming another role's name. The arbiter and predict additionally refuse a message
they cannot route. There is no concurrency, no retry, and no broker - which is what makes the
transcript the audit record instead of a log of it.

**Conservative-max.** The arbiter's ruling payload carries `chosen_c` and the policy name.
When the site sensor and the weather model disagree by more than 1.0 °C the forecast runs on
the higher reading and names both in `reason_trace`. The verifier independently flags a
ruling that lands below the maximum of the disputed readings, so the rule is checked rather
than trusted - flagged, not undone.

**Blackboard.** Plan resolves `(zone, kind)` to the request already open for it and passes the
id on its proposal. When that action is refused, the refusal's `reason_trace` carries
`linked_request=<id>`, so one audit line shows which open request the hour belongs to. The
queue holds one open request per zone and kind, refreshed to the worst reading; every refusal
still writes its own record. The blackboard is synced before each cycle when a queue is
supplied.

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
monitor -> predict : observation : school-dxb-003 at 2027-07-14 13:00 UTC; wbgt 29.0 C from site
predict -> arbiter : dispute     : wbgt-tier-conflict: site 29.0 C vs weather-outdoor 31.1 C (gap above 1.0 C)
arbiter -> predict : ruling      : conservative-max: tiers disagree: ...; chose the higher, conservative 31.1 C
predict -> plan    : assessment  : wbgt 31.1 C; level=high; score=0.617
plan    -> act     : proposal    : 3 interventions: shift_activity, activate_cooling, advise
act     -> verify  : decision    : 3 actions: shift_activity=executed, activate_cooling=executed, advise=executed
verify: ok
```

Abridged: the script prints two header lines first and repeats the ruling before `verify: ok`.
Reproduce with `python scripts/agent_transcript.py`.

## The human gate and the evidence boundary

A consequential intervention without an approver is **refused, never silently downgraded**:
the action record says `refused` with a reason, the approval queue keeps one open request, and
the rest of the cycle continues. What the engine measures is decision latency and action
uptake - whether a hazardous hour produced a decision and whether that decision was carried
out. It does not measure health outcomes, and the fixtures are reanalysis and station records,
not people. Every run report prints that boundary.
