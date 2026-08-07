# Functional Arbor v0.4 — geometry only

v0.3 answered the previous mechanism question: the learned physical timing shift was real, but it lived mainly in **local material speed**, not in a longer grown route.

That is not biologically silly — axon caliber and myelination really are ways nervous systems tune conduction velocity — but it leaves the stricter Geometric Neuron question open:

> **Can a pulse-driven body learn a temporal delay when every occupied piece of cable has exactly the same conduction speed?**

v0.4 removes the speed channel completely.

## The restriction

The structural state is binary:

```text
B(x) = 0   empty / bath
B(x) = 1   arbor
```

and transport has only two constants:

```text
occupied-occupied bond   K = K_arbor
anything else            K = K_bath
```

There is no `M**p`, thickness, graded conductivity, substrate multiplier, or local material quality. Quenched disorder is allowed to bias **morphogenesis only** in the free-interface prototype; it never changes K.

The controlled cable assay is stricter still: the bath is nearly insulating (`K_bath = 2e-4`) and every arbor bond is exactly `K_arbor = 2.5`.

## Why structural turnover is necessary

A connected shortest path cannot be made longer by merely adding material beside it: the old shortcut remains the shortest path.

So geometry-only delay learning needs a local operation of the form

```text
straight segment
      ↓
grow a plaquette detour
      +
prune the shortcut
```

The controlled assay implements exactly that. Two cells are transferred from a disconnected reserve into each detour, so **total structural mass is constant**. Removing a detour returns the cells to the reserve.

This is structural remodeling, not a speed change.

## Task

Two fixed-speed binary cables connect source A and source B to one soma.

```text
TARGET      A pulse, then B pulse after lag
DISTRACTOR  B pulse, then A pulse after lag
```

The soma's scalar score is target-vs-distractor peak coincidence contrast.

The mutation operator is **not told** that A should become longer, how many cells to add, or what delay to produce. At each step:

1. a source pulse creates local eligibility on one randomly chosen cable;
2. a local detour-add/remove proposal is made on that cable;
3. the soma measures whether discrimination improved;
4. `reward` keeps improvements and rejects harms;
5. `shuffle` randomizes the sign of that credit;
6. `anti` reverses it.

The transport equation remains the second-order damped wave from v0.2/v0.3.

## Meter calibration

Before learning, two straight equal cables give exactly zero delay.

Three hand-painted, separated detours on A give:

```text
path-length difference A-B   +6 lattice edges
edge50 wavefront delay       +32 frames
common25 wavefront delay     +33 frames
```

The meter therefore sees geometry before training is allowed to claim it.

Run:

```bat
python3.13 v04_geometry_only/cable_selftest.py
```

## Main result — lag 10, 16 paired seeds

`reward` converged in every seed to **one A-side detour**:

```text
A-B path-length difference    +2 cells
edge50 physical delay         +11 frames
common25 physical delay       +11 frames
coincidence contrast          +0.2343
```

`shuffle` wandered among positive, zero, and negative detours.

Paired reward-minus-shuffle:

| measure | mean | SD | exact sign-flip p |
|---|---:|---:|---:|
| path length A-B | **+1.375 cells** | 1.893 | **0.02393** |
| edge50 delay | **+7.688 frames** | 10.038 | **0.00513** |
| common25 delay | **+7.563 frames** | 10.411 | **0.02393** |
| task contrast | **+0.1969** | 0.1758 | **0.00037** |

The stronger causal control is `anti`: eight of eight seeds grow the detour on **B** instead:

```text
A-B path length   -2
A-B edge50 delay  -11
contrast           -0.2343
```

So the sign of the teaching signal controls the sign of the grown geometry and the sign of the physical delay.

## Lag sweep — geometry is quantized

The structural move adds two lattice edges at a time, so the learned delay cannot vary continuously.

Reward-only exploratory sweep:

| requested lag | mean grown A-B path | mean edge50 delay |
|---:|---:|---:|
| 5 | +2.0 | +11.0 |
| 10 | +2.0 | +11.0 |
| 15 | +3.5 | +18.5 |
| 20 | +3.5 | +18.5 |

This is not slope-1 continuous tuning; it is a **coarse structural code**. The body chooses one or two detours because those are the available geometric quanta.

## Verdict

**[V] Geometry can carry the learned delay.** In the controlled binary-cable assay, local speed variation is mathematically unavailable, while path length, measured wavefront delay, and task selectivity all move together.

**[V] Sign control.** Reverse credit grows the opposite delay.

**[V] Constant material.** Detours move existing binary material from/to a disconnected reserve; total occupied-cell count never changes.

**[K] “Addition-only is sufficient.”** It is not. Once a shortest connection exists, adding side branches cannot lengthen that path without pruning its shortcut.

**[~] Free-form morphogenesis.** The more general binary interface prototype (`binary_arbor.py`, `run_geometry.py`) does not yet robustly discover this solution de novo. The positive result uses a deliberately local plaquette-remodeling grammar so the mechanism is exposed rather than hidden.

**[~] Learning sophistication.** The controlled soma rule is a local structural hill-climber: propose a pulse-eligible remodeling move, keep it if task contrast improves. It is a capability proof, not a claim that biological dendrites perform this exact algorithm.

## Run

Quick:

```bat
python3.13 v04_geometry_only/cable_selftest.py
python3.13 v04_geometry_only/cable_train.py --lag 10 --seeds 4 --mutations 12 --arms reward,shuffle,anti
```

Main receipt:

```bat
python3.13 v04_geometry_only/cable_train.py --lag 10 --seeds 16 --mutations 12 --arms reward,shuffle
python3.13 v04_geometry_only/cable_train.py --lag 10 --seeds 8 --mutations 12 --arms anti
```

## What this earns

The sentence that v0.3 could not support is now true **for this controlled remodeling system**:

> **A pulse-driven structural learner can grow a physical delay by changing path geometry alone, with local conduction speed held fixed.**

The next step is not another timing meter. It is to transfer the local grow-detour/prune-shortcut operation back into the free field-grown arbor and ask whether a dendrite-like branching body can discover the same geometric delay without being handed two pre-existing cables.
