# Functional Arbor v0.9 — causal eligibility

v0.8 showed that soma consequence can physically return to distant structure and can strongly alter survival when the **correct branch is deliberately tagged**. Yet free learning remained null.

v0.9 freezes the exact v0.8 graph-retrograde carrier and changes only the eligibility mark attached to reward.

The result is another useful negative:

> **Transport is not enough, and merely remembering which cells were recently active or recently born is still not enough. Exact birth-event eligibility shows a numerical trend but fails a 16-seed paired confirmation. Reconnect competition tags also fail their shuffled control. The signed timing tag is too sparse/late in this implementation to count as a valid negative.**

Canonical GitHub Actions receipts:

- 8-seed hostile screen: run `31236823133`;
- 16-seed event confirmation: run `31236949078`.

## What is held fixed

All arms inherit the same:

- binary fixed-speed arbor;
- second-order wave transport;
- explicit quasi-static extracellular solve;
- coherent extracellular guidance;
- persistent one-cell growth cones;
- independent connectivity-safe retraction;
- 70-cell material budget;
- temporal task and reward schedule;
- one-edge-per-tick retrograde carrier from v0.8.

Only **eligibility semantics** change.

## Arms

- `activity`: exact v0.8 recent-use baseline.
- `event`: cells physically born since the previous soma evaluation.
- `event_shuffle`: same tag count at wrong locations, matched in graph distance/youngness as closely as the current body permits.
- `competition`: for a natural reconnection, new bypass gets the reward sign and the pre-existing shortcut gets the opposite sign.
- `competition_shuffle`: same positive/negative sparsity at wrong locations.
- `timing`: current-event cells are signed by whether their A-only or B-only route currently needs more or less physical delay.
- `timing_shuffle`: same sparse signs, wrong locations.
- `no_credit`.

No arm contains an explicit useful detour operation or a task-specific structural accept/reject step.

## Self-test

```bat
python3.13 v09_causal_eligibility/selftest.py
```

The test requires:

- 70-cell connected body;
- exactly two mature conductivities;
- a real one-cell structural extension receives a birth-event mark;
- shuffled event tag has identical sparsity and no overlap in the self-test;
- signed timing semantics mark A-only and B-only event cells oppositely;
- retrograde first-arrival remains exactly one tick per graph edge (`r=1`, slope `1`);
- final mass returns to the fixed budget.

## Tag-matching instrument

```bat
python3.13 v09_causal_eligibility/tag_instrument.py --ticks 18 --out tag_instrument.json
```

The frozen instrument found:

```text
mean event/shuffle graph-distance mismatch   0.889 cells
mean event/shuffle age mismatch              7.278 ticks
```

Sparsity is exact and graph distance is close. Age matching is imperfect, especially in the first evaluation window where no alternate newborn cells yet exist. Therefore `event - event_shuffle` is **not** treated as a perfectly pure location test. `event - no_credit` is the cleaner sufficiency test.

## Hostile 8-seed screen

Mean final task contrast:

```text
activity              -0.0164
event                 +0.0851
event_shuffle         +0.0402
competition           +0.0671
competition_shuffle   +0.0505
timing                +0.0208
timing_shuffle        +0.0208
no_credit             +0.0208
```

Key paired effects:

```text
activity - no_credit
contrast -0.0371   p=.4688
edge50   -7.50     p=.0781

event - event_shuffle
contrast +0.0448   p=.5625
edge50   +1.12     p=.8750

event - no_credit
contrast +0.0643   p=.1875
edge50   +2.25     p=.6875

competition - competition_shuffle
contrast +0.0166   p=.8438
edge50   -1.75     p=.7891

competition - no_credit
contrast +0.0463   p=.4844
edge50   +0.88     p=.8594
```

Only the exact-event arm looked sufficiently suggestive to justify a larger run. No gain was changed before confirmation.

## 16-seed exact-event confirmation

Mean final values:

| arm | A-B path | edge50 | common25 | contrast |
|---|---:|---:|---:|---:|
| event | +1.4375 | +9.5625 | +10.9375 | +0.0598 |
| event shuffle | +0.5625 | +6.1250 | +5.6875 | +0.0157 |
| no credit | +0.4375 | +5.1250 | +4.3750 | +0.0188 |

Paired event minus shuffled event:

```text
edge50     +3.4375   p=.46216
contrast   +0.04403  p=.31439
```

Paired event minus no credit:

```text
edge50     +4.4375   p=.30493
contrast   +0.04094  p=.43445
```

So the 8-seed numerical trend does **not** survive as a defensible effect.

## Timing-tag warning

Do not read the timing arm as a clean failure of timing semantics.

It averaged only `1.6` tagged cells and `0.148` delivered credit mass, compared with roughly `27.9` tagged cells and `2.27` credit mass in the event arm. Many signed timing packets therefore had too little causal exposure or arrived too late to alter subsequent retraction. Its equality with `no_credit` means **under-exposed / inconclusive**, not killed.

## Verdict

**[V]** Retrograde transport remains calibrated and unchanged.

**[V]** Local structural birth events can be explicitly marked and carried back to distal anatomy.

**[K]** “Recent activity is sufficiently causal.” Still unsupported.

**[K]** “Remembering exactly which cells were born is sufficient.” Killed by the 16-seed null.

**[K]** “New bypass versus old shortcut identity is sufficient.” Unsupported in the matched 8-seed screen despite adequate credit exposure.

**[?]** Signed timing-event eligibility. Inconclusive because the implementation barely exercised it.

## What v0.9 points to

A structural event can be recent without being **the event that changed transport**.

The next clean eligibility candidate is therefore local before/after flow redistribution:

```text
structural event happens
       ↓
measure local route use before and after the event
       ↓
causal-flow tag ~ event_mask × (J_after - J_before)
       ↓
later soma consequence travels retrogradely
       ↓
stabilize only structural changes that actually changed current flow
```

A new branch that carries no new current should leave almost no tag. A useful bypass that steals current from an old shortcut should leave a positive mark on the new route and a complementary redistribution mark on the old route.

That is the clean v1.0 question. Do not add another carrier first.

## Run

```bat
python3.13 v09_causal_eligibility/selftest.py
python3.13 v09_causal_eligibility/tag_instrument.py --ticks 18 --out tag_instrument.json
python3.13 v09_causal_eligibility/train.py --seeds 8 --ticks 36 --drive-steps 40 --probe-steps 150 --arms activity,event,event_shuffle,competition,competition_shuffle,timing,timing_shuffle,no_credit --out v09_screen
python3.13 v09_causal_eligibility/train.py --seeds 16 --ticks 36 --drive-steps 40 --probe-steps 150 --arms event,event_shuffle,no_credit --out v09_event16
```

Compact canonical receipt: `examples/v09/ci_summary.json`.
Full ledger: `docs/LEDGER_V09.md`.
