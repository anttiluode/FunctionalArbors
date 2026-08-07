# Functional Arbor ledger — v0.2

## What is established in this codebase

**[V] Continuous function-bearing scaffold exists.** In v0.1, maturation lowers the background bath and makes deposited structure carry a measurable fraction of soma transfer. `open_loop` removes that structural transport effect.

**[V] Material budget is matched by construction.** `blind`, `local`, `credit` and `anti_credit` receive the same material per event. A zero-mean reward cannot accidentally produce a zero-body null.

**[V] The wave-delay instrument sees a hand-painted route.** The v0.2 selftest starts from a symmetric two-patch medium (`common25` delay difference 0) and paints a fast A lane. Independent front meters then move strongly in the same direction (`common25` about -56 frames, `edge25` about -39 in the packaged selftest).

## New v0.2 pilot: reward can select a physical front delay

Wave-like two-pulse task, `N=30`, requested lag `+10` frames, 20 target/distractor pairs per seed (2 epochs x 10 pairs), fixed material budget 0.45 per trial. Reward and shuffle use the same substrate seed and end with the same mass (~47.45).

Six paired seeds were run in two chunks (0--3, then 4--5):

- reward contrast: all six positive;
- paired reward-minus-shuffle contrast per seed: `+0.0845, +0.0711, +0.0490, +0.0307, +0.0491, +0.0030`;
- paired mean `+0.0479`, SD `0.0290`, effect/seed-SD `1.65`, exact two-sided sign-flip `p=0.03125`;
- reward `edge50` delay difference: mean `+11.5` frames (requested `+10`);
- shuffle `edge50`: mean `+1.17` frames;
- paired reward-minus-shuffle `edge50`: `+10.33` frames, positive in all six seeds;
- reward `edge25`: mean `+8.17`; shuffle `+1.0`;
- reward common-threshold `common10`: mean `+7.17`; shuffle `+0.5`.

This is materially stronger than the earlier diffusive result because **front timing**, not only the late peak, moves in the task-required direction while total material is matched.

### What is not established

- n=6 is still small.
- Not every front definition lands exactly at 10 frames; the medium is dispersive.
- A two-seed lag sweep is monotone but not a calibrated slope: for required lags 6, 10, 14, reward `edge50` was approximately 9, 11--14, 14 frames depending on the seed set. It begins to saturate.
- This is a synthetic transport system, not evidence that biological dendrites learn by this exact rule.

Therefore the current wall sentence is deliberately narrow:

> **In a second-order wave substrate with matched material mass, reward-modulated eligibility can select an arbor whose independently measured wavefront delay shifts toward the temporal lag required by the task; shuffled credit does not show the same paired shift in this six-seed pilot.**

## Lesions and repair

Lesioning remains a causal engineering test: if removing a used branch does not hurt function, the branch was decorative. It is **not** being used as a claim that adult neural tissue robustly rebuilds severed arbors.

The earlier regrowth assay is retained as exploratory code, but v0.2 does not promote "self repair" to a biological milestone. If revisited, it must use a conserved material pool or equal-mass pruning/reallocation rather than simply adding new material after injury.
