# Functional Arbor v0.6 — ephaptic-guided free growth

v0.5 removed the pre-drawn cables, but one important piece was still supplied: a named local U-shaped detour replacement.

v0.6 removes that shape primitive.

> **Can ordinary local branch extension, reconnection and pruning discover useful geometric delays — and does an ephaptic-like extracellular field help the growth cone find those structural opportunities?**

The result is deliberately mixed:

> **Generic local growth/prune is enough to discover delay geometry without a named U-detour. An ephaptic-like spatial field substantially increases the rate at which growth-cone walks find legal reconnecting routes, but it does not improve final learned timing over blind exploration in this experiment. Soma-locked phase is not specifically supported.**

That is the wall result. Do not turn it into “ephaptic fields teach dendrites their delays.”

## What was removed

There is no function that says:

```text
replace this straight segment with a U detour
```

The structural vocabulary is now:

```text
choose an activity-used branch site
        ↓
initiate an empty neighboring tip
        ↓
extend one lattice cell at a time
        ↓
possibly encounter/reconnect to old arbor
        ↓
prune connectivity-safe weak material
        ↓
return to the same total mass
```

The grown branch path can turn in any sequence of nearest-neighbour steps. Its length, shape, reconnect point and the old segment ultimately removed are not prescribed.

For computational tractability the reconnection + pruning is evaluated as one **developmental episode**. That is still an engineered macro-operation; v0.6 has removed the detour *shape*, not all supplied structural grammar.

## Invariants

The hard v0.5 geometry constraints remain:

- material is binary, `B(x) ∈ {0,1}`;
- every occupied-to-occupied bond has exactly `K_arbor = 2.5`;
- every other mature bond has exactly `K_bath = 0.0002`;
- no thickness, caliber, myelination proxy, graded `K(M)` or substrate-dependent speed exists;
- each seed grows to exactly **70 occupied cells** before learning;
- every accepted structural episode finishes at the same 70 cells;
- soma and both sensory terminals remain connected;
- the final body remains one 4-neighbour tree.

So timing changes still have to come from geometry.

## The ephaptic-like field

This is a **computational proxy**, not a biophysical volume-conductor model.

The intracellular wave state is the same second-order damped wave used since v0.2. During a source pulse, the code forms a spatially blurred analytic membrane-current proxy from velocity on the occupied arbor:

```text
V_e  ≈ smooth( v · B )
E_e  = -∇V_e
```

The extracellular field is compared with the instantaneous soma phase and accumulated slowly:

```text
G ← λG + (1-λ) Re( E_e · conj(soma_phase) )
H ← λH + (1-λ) |E_e|
```

`G` is a phase-referenced vector trace. `H` is a magnitude trace.

A growth-cone step from site `x` into direction `d` is sampled roughly as

```text
P(d) ∝ (epsilon + magnitude_gain · H) · exp(beta · Ghat·d)
```

The **start site** is chosen from ordinary intracellular eligibility, not from A/B identity or the task target.

See `ephaptic_arbor.py` for the exact implementation and `field_demo.py` for the instrument view.

## Ablations

All arms start from the same field-grown body for a given seed.

```text
full
    local eligibility + ephaptic magnitude + phase-referenced field vector + soma credit

no_ephaptic
    same local eligibility + same soma credit; branch walk is unguided

magnitude_only
    extracellular |E| remains, vector/phase direction removed

phase_shuffle
    field magnitude and directional structure remain, but soma phase reference is randomized

shuffle_credit
    full ephaptic proposal mechanism, but the sign of task credit is randomized

no_credit
    full ephaptic proposal mechanism, but survival is based only on local field support
```

The last two ask whether useful temporal structure requires the consequence at the soma.

## Self-test

```bat
python3.13 v06_ephaptic_growth/selftest.py
```

The self-test requires:

- field-grown body reaches both inputs and remains a tree;
- mature conductivity contains exactly two values;
- a real pulse produces intracellular eligibility plus nonzero `H` and `G`;
- a generic growth-cone episode can reconnect without a named detour shape;
- final mass is unchanged and connectivity/tree invariants survive;
- unguided exploration can also produce legal proposals, so the ephaptic arm is not the only arm capable by construction.

## Main receipt — 16 paired seeds

Settings:

```text
N                   31
requested lag       +20 frames
bootstrap mass      70 cells exactly
structural episodes 18
cone attempts        8 per episode
max cone walk        10 cells
```

### Does the ephaptic-like field help the growth cone find reconnections?

Yes, in this toy proxy.

Mean fraction of structural episodes that found a **legal reconnecting, same-mass tree proposal**:

| arm | legal proposal yield |
|---|---:|
| full | **0.760** |
| no ephaptic | 0.556 |
| magnitude only | 0.639 |
| phase shuffle | **0.802** |

Paired exact sign-flip tests:

```text
full - no_ephaptic      +0.2049   p = 0.00156
full - magnitude_only   +0.1215   p = 0.00238
magnitude - no_ephaptic +0.0833   p = 0.0232
```

So spatial field information makes generic growth-cone exploration more efficient than a blind random walk.

### Does the correctly soma-phase-locked field matter?

**No evidence here.**

`phase_shuffle` had proposal yield `0.802`, slightly above `full = 0.760`, and the final task contrast was also not worse:

```text
full contrast          +0.2612
phase-shuffle contrast +0.3291
full - phase_shuffle   -0.0679   p = 0.07495
```

That is not a phase-arrow result. Randomizing the soma phase did not kill the effect.

The safe conclusion is:

> the spatial extracellular-field proxy helps exploration; its particular soma-locked phase coding has **not** earned a role.

### Does ephaptic guidance improve final learning over blind exploration?

No.

```text
                        full       no_ephaptic
final A-B path          +1.06       +0.31 edges
final edge50 delay      +5.38       +6.13 frames
final task contrast     +0.261      +0.264
```

Paired `full - no_ephaptic`:

```text
path difference   +0.75     p = 0.646
edge50 delay      -0.75     p = 0.933
contrast          -0.0033   p = 0.955
```

Given enough generic proposals, soma credit can select useful geometry even without the ephaptic field. In v0.6 the field improves **search efficiency**, not the final optimum reached.

### Is soma credit still doing real work?

Yes.

Against a field-guided arm with **no soma credit**:

```text
full - no_credit
A-B path difference    +2.6875 edges   p = 0.0461
edge50 delay           +14.125 frames  p = 0.0478
task contrast          +0.2025         p = 0.000214
```

Against shuffled task credit:

```text
full - shuffle_credit task contrast +0.1765   p = 0.0104
```

So the extracellular field by itself does not know which geometry is useful. The global consequence remains the selector.

## Geometry still carries timing

Within the 16 `full` organisms, structural change and independently measured timing change remain tightly linked:

```text
corr(Δ A-B path length, Δ A-B edge50 delay) = 0.9219
slope                                             3.71 frames / edge
```

This is not a new proof of the geometry mechanism — v0.5 already had the stronger path-only reconstruction — but it confirms that removing the U-detour shape primitive did not reopen a speed channel.

## What v0.6 earns

**[V] No named detour shape.** New routes are nearest-neighbour growth-cone walks of variable shape and length.

**[V] Generic structural vocabulary can still find useful delays.** Branch extension + reconnection + connectivity-safe pruning is sufficient for task-selectable geometric remodeling.

**[V] Ephaptic-like spatial guidance improves proposal efficiency.** Legal reconnection yield rises substantially over blind exploration.

**[K] “Soma-locked ephaptic phase is the developmental arrow.”** Killed for this implementation. Phase shuffle does not destroy exploration or learning.

**[K] “Ephaptic guidance is necessary for the temporal task.”** Killed. The no-ephaptic arm reaches comparable final task performance with enough proposals.

**[V] Soma consequence remains necessary for reliable useful structure.** No-credit and shuffled-credit controls lose task contrast.

**[~] Biology.** The extracellular field is a blurred analytic proxy, and the growth episode is an engineered computational developmental move. None of this establishes that biological dendrites use this mechanism.

## Run

Quick:

```bat
python3.13 v06_ephaptic_growth/selftest.py
python3.13 v06_ephaptic_growth/train.py --seeds 4 --arms full,no_ephaptic,magnitude_only,phase_shuffle,shuffle_credit,no_credit --out v06_quick
```

Main receipt settings:

```bat
python3.13 v06_ephaptic_growth/train.py --seeds 16 --lag 20 --mutations 18 --bootstrap-mass 70 --cone-attempts 8 --cone-max-steps 10 --arms full,no_ephaptic,magnitude_only,phase_shuffle,shuffle_credit,no_credit --out v06_main
```

Field instrument:

```bat
python3.13 v06_ephaptic_growth/field_demo.py --seed 0 --out ephaptic_field.png
```

Plots from the included receipt:

```bat
python3.13 v06_ephaptic_growth/plot_results.py examples/v06/receipt16.json --seed0 examples/v06/seed0.json --out examples/v06/plots
```

## Next wall

The most important next improvement is **not** to tune `beta` until `full` beats every ablation.

The current experiment says the field is useful mainly as an exploration aid. To ask a stronger biological-looking question, v0.7 should remove two remaining abstractions:

1. replace the blurred `V_e` proxy with a quasi-static extracellular solve driven by explicit transmembrane-current sources;
2. stop bundling reconnection + pruning into one proposal episode. Let persistent growth cones extend one cell at a time, stabilize through a slow chemistry-like trace, and retract through a separate trophic/credit process.

Then test coherence properly: matched field power and matched chemistry, differing only in meaningful phase relationships.

If phase matters there, it will have earned it rather than inheriting it from the code.
