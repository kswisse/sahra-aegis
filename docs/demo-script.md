# Three-minute demo script

Run from the repo root. Every command below is offline and finishes in under a second, so the
three minutes are narration, not waiting.

**Prerequisites:** `.venv` already built (`scripts/bootstrap.py` did it), no network, no model
download, no fixture regeneration. Terminal font large enough that the transcript is readable
on video; scrollback cleared first.

**Budget:** beat 1 0:00-0:40 · beat 2 0:40-1:40 · beat 3 1:40-2:20 · close 2:20-3:00.

## Rehearse the whole take in one command

Paste this once, in the same terminal you will record in. It runs all three beats in order, so a
recording is one paste and three beats of narration, with no typing on camera:

```powershell
.venv\Scripts\python.exe scripts\agent_transcript.py; .venv\Scripts\python.exe scripts\demo_day.py; .venv\Scripts\python.exe scripts\demo_day.py --audit sahra-demo-out\demo-beat3.jsonl | Select-String "Audit tail" -Context 0,9
```

It prints 106 lines and ends with the audit tail. If any expected line below is missing, stop
and fix the script before recording; do not narrate around a missing line.

## Beat 1 - one cycle, as messages (0:00-0:40)

```
.venv/Scripts/python scripts/agent_transcript.py
```

Expected, in this order (the numbers are fixed by the fixture; the script prints two header
lines first, and repeats the ruling before `verify: ok`):

```
monitor -> predict : observation : school-dxb-003 at 2027-07-14 13:00 UTC; wbgt 29.0 C from site
predict -> arbiter : dispute     : wbgt-tier-conflict: site 29.0 C vs weather-outdoor 31.1 C (gap above 1.0 C)
arbiter -> predict : ruling      : conservative-max: ... chose the higher, conservative 31.1 C from weather-outdoor
predict -> plan    : assessment  : wbgt 31.1 C; level=high; score=0.617
plan    -> act     : proposal    : 3 interventions: shift_activity, activate_cooling, advise
act     -> verify  : decision    : 3 actions: shift_activity=executed, ...
verify: ok
```

Say: the site sensor and the weather model disagreed, and the system did not average them. It
raised a dispute, the arbiter took the higher reading, and the forecast ran on the
conservative number. The verifier then checked the finished cycle and reported no broken
invariant. No model was called.

## Beat 2 - one archived day (0:40-1:40)

```
.venv/Scripts/python scripts/demo_day.py
```

Point at the table while it scrolls (24 rows, one per hour), then at these lines:

```
  11:00   44.9   32.5  extreme  escalate   escalate=refused, shift_activity=executed, ...
Peak WBGT 34.5 C at 14:00 local (extreme band).
```

Say: at 09:00 the day crosses into `high` and cooling is activated. At 11:00 it crosses 32 °C,
the escalation becomes consequential, and with no approver on duty the gate **refuses** it -
it does not silently downgrade it, and the rest of the cycle still runs.

Then scroll to:

```
  one open request per zone and kind: <id> (kind escalate)
  first raised at 11:00, last refreshed to WBGT 34.5 C (extreme) at 14:00
Coordinator decision on the peak-hour escalation (14:00, WBGT 34.5 C):
  request <id> -> APPROVED by coordinator@dxbops
```

Say: eight hazardous hours, eight refusals, and exactly one open request, refreshed to the
worst reading. The approver signs at 14:00 - and the approval is appended as a new record, not
a rewrite of the eight refusals.

## Beat 3 - the audit trail (1:40-2:20)

```
.venv/Scripts/python scripts/demo_day.py --audit sahra-demo-out\\demo-beat3.jsonl | Select-String "Audit tail" -Context 0,9
```

Expected: the last 8 of 69 records, ending with

```
  <stamp>  escalate          -> executed (approved_by=coordinator@dxbops)
```

Say: the log is append-only and every line carries the approver, so a reviewer can see who
signed what and when. Same fixture, same run - the decisions and the trace text come out
identical every time; only the generated ids and the approval timestamp differ, and the golden
tests normalise exactly those.

## Close (2:20-3:00)

Do not run anything. Say the closing paragraph from the narration section below, word for word:
it is the claim boundary, and it is the one part of the video a judge may quote back at you.

## Read-aloud narration

Word for word, in this order. It is written to be spoken: short clauses, no numbers you have to
look up, and the pauses are already in the time budget. 371 words at a calm pace is about 2:40 of
speech inside a 3:00 take, so the pauses are yours to spend on scrolling. Read it once aloud
before recording.

**Beat 1 (0:00-0:40).**

> This is one decision cycle, printed as the messages the agents actually pass. The site sensor
> read 29.0 degrees. The weather model read 31.1. The system did not average them, and it did not
> quietly pick one. It raised a dispute, and an arbiter settled it under a single published rule:
> take the higher reading. So the forecast ran on 31.1, the conservative number. The planner then
> proposed three interventions, and the verifier checked the finished cycle and found no broken
> invariant. No language model was called anywhere in that path. It is a state machine.

**Beat 2 (0:40-1:40).**

> Now the same engine over one archived Dubai day, hour by hour. Twenty-four rows, one per hour.
> At nine in the morning the heat crosses into the high band and cooling is activated. At eleven
> it crosses thirty-two degrees, which makes escalation consequential. Watch what happens. With no
> approver on duty, the gate refuses it. It does not downgrade it, and it does not hide it. The
> refusal is written to the audit with its reason, and the rest of the cycle still runs.
>
> Eight hazardous hours, eight refusals, and exactly one open request, refreshed each hour to the
> worst reading it has seen.
>
> At two in the afternoon the coordinator signs. The approval is appended as a new record. The
> eight refusals stay exactly where they were.

**Beat 3 (1:40-2:20).**

> The audit tail is the last eight of sixty-nine records for that day. Append-only: nothing above
> it was rewritten. Every line names the intervention, its outcome, and who approved it. The same
> fixture produces the same decisions and the same trace text on every run. Only the generated ids
> and the approval timestamp change, and the golden tests normalise exactly those.

**Close (2:20-3:00).**

> What this measures is decision latency and action uptake: did a hazardous hour produce a
> decision, and was that decision carried out. It does not measure health outcomes, and the
> fixture is reanalysis, not a station observation. What you have seen is a loop that is
> auditable end to end, and that refuses to act without a human.

Do not improvise the closing paragraph. It is the claim boundary, and it is the one part of the
video that a judge may quote back at you.

## Fallback

If beat 2 fails on stage (terminal too narrow, the audit path is not writable), fall back to
the short deterministic demo. It is quicker but it still writes its audit log, to
`sahra-demo-out/audit.jsonl`:

```
.venv/Scripts/python -m sahra.demo
```

If that directory is the problem, run the command from a scratch directory instead. Expected:
three `verify: ok` lines and one `escalate -> refused`. Then go straight to the close; beat 3
is a nicety, the refusal is the point.

If the venv itself fails, run `python scripts/bootstrap.py` (one command, needs network) and
say what it is doing while it runs - or play the pre-recorded take.

## Dry-run checklist

- [ ] Cleared shell, repo root, `.venv` active by absolute path.
- [ ] `git status` clean before recording; `sahra-demo-out/` is gitignored.
- [ ] Full run timed: transcript + day + audit tail under 3:00 including narration.
- [ ] Every printed line above still matches (fixtures or engine changed -> fix this file first).
- [ ] Read the closing paragraph once without looking at the screen.
