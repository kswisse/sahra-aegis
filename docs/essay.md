# SAHRA: from a heat reading to an accountable decision

## 1. The problem

Dubai manages heat at the scale of the city: heat maps, building codes, a midday ban. Exposure
does not happen at that scale. It happens at one school gate at 11:20, when a coach has to
decide whether a football session goes ahead, and at one work site where a supervisor has to
decide whether the crew keeps pouring concrete. A city-wide average cannot answer either
question, because two sites a few kilometres apart can sit three degrees apart in heat stress
on the same afternoon.

The regulatory instrument already exists. Ministerial Resolution No. 44 of 2022 bans work in
direct sun and in open places between 12:30 and 15:00, from 15 June to 15 September [C13]. It
is a blanket window applied to every site at once, and it is the correct floor rather than a
per-zone decision.

What is missing is not more data, and not another dashboard. It is the loop between a reading
and an action that a named person is accountable for.

## 2. What SAHRA decides

SAHRA runs one deterministic cycle with six roles and one transcript. Monitor reads the tiered
sources and fuses them into a single heat state. Predict computes wet-bulb globe temperature,
bands it, and raises a dispute instead of silently choosing between sources. Arbiter settles
the dispute. Plan proposes interventions. Act executes them through an approval gate. Verify
reads the finished cycle and reports whether any invariant broke.

The cycle is short enough to follow by hand. In the worked example the site sensor read
29.0 °C and the weather model 31.1 °C [C12]. SAHRA did not average them. It raised a dispute,
the arbiter ruled under one published policy, conservative-max, and took the higher reading;
the planner proposed three interventions; the verifier returned ok [C11].

Every decision is a typed object rather than prose: an intervention kind, the evidence that
supports it, a reason trace that carries the numbers, and, for anything consequential, the
name of the human who approved it.

The threshold contract is occupational: 28 °C WBGT, with bands at 28, 30 and 32 °C [C2]. The
vulnerability weights, 1.0 for schools and 1.05 for outdoor workers, are a design choice
rather than a measurement, and the code says so [C3].

Nothing consequential happens on the engine's own authority. Without an approver the action is
refused [C10].

## 3. Why six roles and not one loop

The architecture came from published evidence, not taste. A controlled 270-run study compared
a single agent, an LLM-orchestrated multi-agent system, and a deterministically orchestrated
one on the same 30 transactional tasks, with the same models and tools in every arm [C1]. The
LLM-orchestrated system lost reliability to coordination failures and passed 74.44% of its
runs; deterministic orchestration recovered most of that ground at 93.33%; the single agent
scored highest, at 94.44% [C1].

That last number is the honest part, and it is in the README. SAHRA chooses the deterministic
plane because it is replayable and auditable, not because it wins every comparison. The
multi-agent split buys separations of duty that one prompt cannot provide: the verifier must
not be the agent it verifies.

Cost is the other half. In that study every multi-agent arm used more tokens and more latency
than the single agent [C1]. SAHRA's control path calls no model at all, so it keeps the
structure that recovered the reliability without paying an inference bill for it. The study is
a preprint, not a consensus: it is the argument for this design, not a proof of it.

## 4. How it is validated

The method is replay, not a simulation of people. Archived Dubai weather is fed through the
engine hour by hour, and the checks are anchored on events that are externally dated. The
anchors fix when to look. They never assert what the outcome was.

Anchor one is the regulation itself. On 1 July 2026 the archived day peaks at 31.4 °C WBGT at
11:00, a high band [C6], and the replay asserts that the midday sample inside the ban window
bands high or worse. The engine reached a decision the regulation would recognise without
being told what the regulation says. A second archived day, 13 August 2026, peaks at 34.5 °C
at 14:00, extreme, and exercises the refusal path [C8].

Anchor two is station records. The replay file carries three official NCM readings, 51.6, 46.6
and 50.0 °C, alongside three reanalysis grid samples that sit below them, which is the
expected direction for a gridded product, and its highest row is 33.66 °C [C9]. The grid is a
coverage input, not evidence about people.

Regression is part of the validation: 149 tests [C4], three golden transcripts that reproduce
the same decisions and the same trace text on every run once the generated ids are normalised
[C5], and the conservative-max ruling reproduced from the transcript [C12].

## 5. What it cannot show

No per-event heat-illness series exists for the UAE, so the anchors are regulatory and
record-day facts, not health outcomes. ISO 7243, the standard SAHRA follows for screening,
tells you whether heat stress is present in a workplace. It does not predict harm to a
particular person [C2].

Two further limits are written into the repository rather than hidden. Satellite land-surface
temperature is a sanity check only: a reading far above air temperature is flagged, not acted
on. And the replay series is one 13:00 row per location, so it cannot represent the 09:00 to
12:00 exposure peak; the 24-hour fixtures carry the diurnal window instead.

What the engine reports is decision latency and action uptake: whether a hazardous hour
produced a decision, and whether that decision was carried out. Every run ends with that
sentence [C11].

## 6. The human gate

A consequential intervention without an approver is refused, not quietly downgraded. The
action record says refused and carries a gate reason, the approval queue holds one open
request per zone and kind, and the rest of the cycle continues [C10]. On the extreme archived
day that produced eight refusals across eight hazardous hours, one open request refreshed to
the worst reading it saw, and eight separate audit records.

This is the design, not a limitation. A rules engine should not be able to cancel a school day
on its own, and the refusal is the auditable part: it names what was proposed, on what
evidence, and who was missing. The verifier checks that no refused action lacks a reason.

The oversight is the product. A system that hid its escalations inside a dashboard would be
easier to demonstrate and worse to deploy.

## 7. Dubai deployment path

Phase one is what the repository does today: replay mode, offline, no integration, with every
number reproducible from a clean clone [C4] [C5].

Phase two is one school zone with its own site sensor and the weather tier as fallback, with
the midday rule still the ground rule. The engine already prefers the higher of two
disagreeing tiers [C12], which is exactly the behaviour a second source requires.

Phase three is an operator view over the audit log and the approval queue. The queue is the
only new surface.

Throughout, the data stays at zone level: no personal data, no individual records, and in
phase one nothing leaves the operator's machine at all.

## 8. Close

SAHRA closes one loop: a reading becomes a decision, the decision waits for a named approver,
the outcome is appended to an audit that cannot be rewritten, and a verifier checks the cycle
afterwards.

It measures decision latency and action uptake, not health outcomes [C11].

A judge can see all of it in three minutes: the transcript of one cycle, one archived day hour
by hour, and the audit tail behind both.

---

## Notes for the owner (not part of the essay)

- The bracketed tags `[C1]`...`[C13]` are rows in `docs/claims.md`. Delete them before pasting
  into the portal; they exist so you can check any sentence against its source in one hop.
- Length: about 1,270 words, inside the 1,200-1,500 target. No em dashes, no tables, no
  images, so a plain web form will not mangle it.
- Three sentences carry the whole risk profile. Keep them if you rewrite anything else:
  "The single agent scored highest, at 94.44%"; "The study is a preprint, not a consensus";
  "It measures decision latency and action uptake, not health outcomes."
- Do not add: a heat-illness count, a percentage of harm avoided, a rollout date, a partner
  name, or a cost saving. None of those is sourced, and each one turns a defensible essay into
  an indefensible claim.
