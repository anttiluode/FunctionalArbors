# Functional Arbor v0.7 — persistent growth cones and a quasi-static extracellular solve

v0.6 removed the named U-shaped detour, but two major conveniences remained:

1. the extracellular field was a blurred analytic proxy;
2. branch growth, reconnection and compensating pruning were evaluated as one developmental episode.

v0.7 removes both.

The result is again mixed, and the negative is important:

> **A quasi-static extracellular field continues to improve structural search, and after longer development field-guided bodies can outperform no-field controls on the temporal task. But coherent soma-locked phase does not beat phase-scrambled guidance. The specific phase-arrow hypothesis is still not supported. The new slow trophic credit rule is also not yet a robust selector.**

## 1. Explicit extracellular source and solve

The intracellular body is still binary and fixed-speed. Every occupied bond has the same `K_arbor`; there is no caliber, thickness, myelination proxy or graded material speed.

The fast intracellular wave produces an explicit current-source density from the divergence of axial current plus imposed terminal current:

```text
I_tm = - div(J_axial) + I_terminal
```

The extracellular potential is then solved on the 2-D bath using

```text
(-sigma_e Laplacian + kappa^2) V_e = I_tm
```

with a grounded outer boundary, and

```text
E_e = -grad(V_e)
```

is the developmental field.

The solver uses a discrete sine-transform Dirichlet Poisson/Helmholtz solve. This is a **volume-conductor-like computational model**, not a detailed biophysical neuron: `I_tm` comes from the toy wave cable rather than Hodgkin-Huxley membrane currents, and the extracellular conductivity is homogeneous.

## 2. Persistent growth cones

There is no function that means “make a detour” or “reconnect then prune.”

A tip is a persistent object with a position, previous direction, age, stall count and trail. Across separate developmental ticks it can:

```text
initiate
extend exactly one nearest-neighbour cell
stall
branch
naturally reconnect if the next cell touches old arbor
```

Reconnection does **not** trigger pruning.

A separate homeostatic retraction process later removes at most one low-support connectivity-safe cell when growth has incurred material debt.

Thus a useful bypass can take many ticks to appear and an old shortcut can disappear later through an independent process.

## 3. Slow chemistry and delayed consequence

Extracellular field magnitude writes a slow chemistry-like trace. This trace is deliberately **phase blind** so phase controls have matched chemistry.

New cells receive temporary support. Intracellular use writes structural eligibility. At task-evaluation times the change in soma discrimination becomes a delayed trophic signal:

```text
support += activity support
support += slow magnitude chemistry on young material
support += soma reward * recent structural eligibility
```

Negative consequence destabilizes recently eligible material; positive consequence stabilizes it. Retraction acts later on weak safe material.

This is no longer the v0.5/v0.6 accept/reject hill-climber.

## 4. Clean phase controls

All arms receive exactly the same intracellular A-then-B pulse dose.

For a fixed anatomy, `coherent`, `phase_scramble`, `phase_reverse` and `magnitude_only` use the **same solved extracellular field magnitude and therefore the same slow chemistry**. Only directional phase information changes:

```text
coherent
    project E_e against the actual soma analytic phase

phase_scramble
    rotate E_e by a random global phase before the same projection
    |E_e| is unchanged

phase_reverse
    reverse the phase-referenced field vector
    |E_e| is unchanged

magnitude_only
    same |E_e| chemistry, no phase vector

no_field
    no extracellular chemistry or vector guidance
```

Once structures diverge, their future field powers naturally diverge too; matching is exact for the same anatomy/stimulus, not forced after causal anatomical divergence.

## Self-test

```bat
python3.13 v07_persistent_ephaptic/selftest.py
```

The test requires:

- 70-cell binary fixed-speed arbor reaches both sources;
- only two mature bond conductivities exist;
- a balanced current dipole produces nonzero `V_e` with zero grounded boundary;
- coherent and phase-reversed representations have identical `|E|^2` and identical slow chemistry on the same body;
- persistent tips extend one cell at a time;
- retraction is a separate operation;
- final material returns to the original mass while both sources remain connected.

## Main receipt — 16 paired seeds, 24 developmental ticks

Settings:

```text
N                     31
bootstrap body         70 cells
requested lag          +20 frames
persistent ticks       24
evaluation interval    3 ticks
field drive             48 fast steps / tick
```

Mean final values:

| arm | A-B shortest path | edge50 delay | task contrast | reconnections / extension |
|---|---:|---:|---:|---:|
| coherent | +0.750 | +0.562 | +0.0617 | 0.439 |
| phase scramble | +0.250 | +3.312 | +0.0603 | 0.430 |
| phase reverse | -0.500 | -1.562 | -0.0332 | 0.520 |
| magnitude only | +0.438 | +2.062 | -0.0272 | 0.437 |
| no field | +0.188 | +2.188 | -0.0807 | 0.374 |
| no credit | +0.188 | -1.875 | +0.0138 | 0.399 |

### Phase-specific claim: still null

Paired coherent minus phase-scramble:

```text
path       +0.500   p=0.2578
edge50     -2.750   p=0.5265
contrast   +0.0014  p=0.9847
```

The correctly soma-phase-locked field is **not** better than a power- and chemistry-matched scrambled phase field.

Coherent minus phase-reverse has a path-length shift (`+1.25`, `p=0.0352`) but not a corresponding reliable timing or task shift (`edge50 p=0.5767`, contrast p=0.2806). That is not enough to claim a phase arrow.

### Search effect survives the mechanistic upgrade

Coherent reconnects more efficiently than no-field:

```text
reconnections / extension difference  +0.0644
exact sign-flip p                      0.0373
```

But coherent and magnitude-only have essentially identical reconnection rate (`+0.001`, `p=0.973`). Therefore the short-run search advantage is best attributed to **extracellular magnitude/slow chemistry**, not the phase vector.

### Slow soma credit is not established

Coherent minus no-credit:

```text
path       +0.562   p=0.449
edge50     +2.438   p=0.497
contrast   +0.0479  p=0.473
```

So unbundling the old accept/reject episode exposed a weakness: this particular delayed trophic rule does not yet reliably select better bodies.

That is a real v0.7 result, not a parameter to hide.

### Geometry still affects timing

Within the coherent arm:

```text
corr(delta shortest-path length, delta edge50 timing) = 0.682
slope                                                   = 8.02 frames / edge
```

The relation is noisier than v0.5 because persistent bodies may contain temporary/lasting loops and side branches, so shortest path is not the complete Green-function geometry.

## Longer-development check — 8 paired seeds, 36 ticks

Persistent chemistry should be allowed time to act, so a smaller paired run was repeated at 36 ticks.

Mean task contrast:

```text
coherent        +0.0957
phase_scramble  +0.0955
phase_reverse   -0.0673
magnitude_only  -0.0300
no_field        -0.0478
no_credit       +0.0358
```

Paired coherent differences:

```text
vs phase_scramble   +0.0002   p=1.0000
vs phase_reverse    +0.1630   p=0.0391
vs magnitude_only   +0.1257   p=0.0469
vs no_field         +0.1435   p=0.0078
vs no_credit        +0.0599   p=0.3750
```

This is intriguing but still does **not** rescue the coherent-phase hypothesis: scrambling phase leaves final performance essentially identical. Reversing the vector hurts, and having directional field guidance can beat magnitude/no-field after longer development, but the correct absolute phase lock itself is not required.

The longer coherent bodies again show geometry-timing coupling:

```text
corr(delta path, delta edge50) = 0.949
slope                          = 12.31 frames / edge
```

## Verdict

**[V] Explicit extracellular solve.** v0.7 uses a grounded quasi-static field solve driven by explicit current-source density rather than spatial smoothing.

**[V] Persistent developmental primitives.** Extension, branching, stabilization and retraction are temporally separate. No named detour and no reconnect+prune atomic operation exists.

**[V] Extracellular information can improve structural search.** In the 16-seed receipt, field-bearing chemistry increases reconnect efficiency over no-field.

**[~] Directional field guidance may matter over longer development.** Coherent beats magnitude/no-field on task contrast in the 8-seed 36-tick check, but this needs replication at larger N/seeds.

**[K] “Correct soma-locked ephaptic phase is the teacher.”** Killed again. Coherent and phase-scramble are indistinguishable on final task contrast.

**[K] “The new delayed soma-credit chemistry is already sufficient.”** Not supported. Coherent does not reliably beat no-credit.

**[~] Biology.** The solver is materially closer to a volume conductor, but membrane currents, growth-cone transduction, chemistry and trophic credit are still abstract computational mechanisms.

## Run

Main short receipt:

```bat
python3.13 v07_persistent_ephaptic/train.py --seeds 16 --lag 20 --ticks 24 --eval-interval 3 --drive-steps 48 --probe-steps 170 --arms coherent,phase_scramble,phase_reverse,magnitude_only,no_field,no_credit --out v07_main
```

Longer check:

```bat
python3.13 v07_persistent_ephaptic/train.py --seeds 8 --lag 20 --ticks 36 --eval-interval 3 --drive-steps 48 --probe-steps 170 --arms coherent,phase_scramble,phase_reverse,magnitude_only,no_field,no_credit --out v07_long
```

Field instrument:

```bat
python3.13 v07_persistent_ephaptic/field_demo.py --seed 0 --out quasistatic_field.png
```

Included frozen receipts are in `examples/v07/`.

## Next wall

Do **not** tune the phase coefficient until coherent wins.

The result points somewhere else: extracellular structure can help exploration, but delayed consequence is currently too weak to reliably stabilize the right branch. The next clean question is therefore about **credit transport**, not more field physics.

A v0.8 should keep the v0.7 extracellular solver and persistent tips fixed, then compare explicit biologically-inspired delayed-credit carriers: retrograde eligibility along the active path, a diffusible trophic field from the soma, and purely global scalar reward. The field should remain a proposal/guidance channel; credit should become a separately measurable stabilization channel.
