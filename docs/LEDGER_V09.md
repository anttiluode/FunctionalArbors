# v0.9 ledger — causal eligibility

Canonical execution:

- hostile 8-seed screen: GitHub Actions run `31236823133`;
- 16-seed event confirmation: run `31236949078`;
- Python 3.12;
- exact repository v0.8 retrograde transport inherited.

## Question

v0.8 established that delayed soma consequence can travel back through the arbor and can control survival when the correct branch is manually tagged. Does a more causal local tag make free credit assignment reliable?

## Frozen machinery

v0.9 does **not** change:

- fixed-speed binary cable;
- second-order wave transport;
- explicit quasi-static extracellular solve;
- coherent extracellular guidance;
- persistent one-cell growth cones;
- independent retraction and fixed material budget;
- reward schedule;
- graph-retrograde carrier speed and decay.

Only the eligibility snapshot attached to retrograde reward changes.

## Eligibility arms

- `activity`: v0.8 recent-use baseline.
- `event`: cells physically born since the previous soma evaluation.
- `event_shuffle`: same number of event tags at wrong locations, approximately matched in graph distance and youngness.
- `competition`: new reconnect bypass receives the reward sign; pre-existing shortcut receives the opposite sign.
- `competition_shuffle`: same positive/negative tag counts at wrong locations.
- `timing`: current-event cells are signed by whether their source-specific route currently needs more or less delay.
- `timing_shuffle`: same sparse signed counts, wrong locations.
- `no_credit`.

## Instrument status

Selftest passes:

- 70-cell connected body;
- exactly two mature conductivities;
- a real one-cell structural extension receives a birth-event mark;
- shuffled event tag has identical sparsity and no spatial overlap in the selftest;
- timing tag signs A-only and B-only event cells oppositely;
- retrograde first arrival remains exactly one tick per graph edge (`r=1`, slope `1`);
- mass restoration and source connectivity survive.

Tag-matching instrument:

- mean event/shuffle graph-distance mismatch: `0.889` cells;
- mean age mismatch: `7.278` ticks.

The age match is imperfect, especially at the first evaluation because no alternative newborn cells yet exist. Therefore event-vs-shuffle is **not** treated as a perfectly pure spatial-location null. Event-vs-no-credit is the cleaner sufficiency test.

## Hostile 8-seed screen

Mean final temporal contrast:

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

Key paired differences:

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

The event arm was the only candidate with a sufficiently suggestive trend to justify a larger paired run. No gain was changed before confirmation.

### Timing-tag exposure warning

The timing arm is **not a valid negative test of timing semantics** in this implementation. It produced only `1.6` tagged cells on average and delivered only `0.148` credit mass, versus `27.9` tags / `2.27` credit mass for event eligibility. Many timing-tag packets were launched too sparsely or too late to alter anatomy before the run ended. Its exact numerical identity to `no_credit` therefore means **under-exposed/inconclusive**, not killed.

## 16-seed event confirmation

Means:

```text
                     event      shuffled event     no credit
A-B path             +1.4375       +0.5625          +0.4375
edge50               +9.5625       +6.1250          +5.1250
common25            +10.9375       +5.6875          +4.3750
contrast             +0.0598       +0.0157          +0.0188
```

Paired:

```text
event - event_shuffle
edge50     +3.4375    p=.46216
contrast   +0.04403   p=.31439

event - no_credit
edge50     +4.4375    p=.30493
contrast   +0.04094   p=.43445
```

The apparent 8-seed event trend does not survive as a defensible effect at 16 seeds.

## Verdict

- `[V]` v0.8 retrograde transport remains calibrated and unchanged.
- `[V]` exact structural birth events can be tagged and carried distally.
- `[K]` broad activity eligibility is sufficient for free learning — still unsupported.
- `[K]` birth-event identity alone is sufficient — killed by the 16-seed null.
- `[K]` reconnect competition identity alone is sufficient — unsupported in the 8-seed matched screen despite adequate tag/credit exposure.
- `[?]` signed timing-event eligibility — inconclusive because the tag was too sparse/late to exercise the mechanism.
- `[~]` event-vs-shuffle spatial-location claim — control has exact sparsity and close graph distance but imperfect age matching.

## What v0.9 actually isolates

The remaining problem is not merely **where reward travels**, and it is not solved by remembering **which cells were born**.

A structural event can be recent without being causally important. The more local candidate for the next build is the **change in transport caused by the event**:

```text
before structural change: local current / route use J_before
after structural change:  local current / route use J_after

causal-flow tag ~ event_mask * (J_after - J_before)
```

A newly grown process that does not change flow should leave almost no causal tag. A bypass that genuinely steals current from an old shortcut should create a positive tag on the new route and a corresponding negative redistribution mark on the old route.

That is the clean v1.0 question. Do not add another reward carrier first.
