# Functional Arbor v0.8 — credit transport works; causal eligibility does not yet

v0.7 made extracellular guidance and persistent development more physical, but its delayed soma consequence did not reliably stabilize useful geometry. v0.8 freezes the **exact v0.7 wave, extracellular solve, bootstrap and persistent growth-cone mechanics** and changes one question only:

> **If consequence at the soma has an explicit physical return path to distant structure, does free credit assignment become reliable?**

The answer is **no — and the failure is informative**.

> **Retrograde and trophic carriers really transport credit, and retrograde consequence can strongly alter survival when the correct structural branch is deliberately tagged. But in free learning, no tested carrier reliably beats no credit. The bottleneck has moved from transport to causal eligibility: recent activity is not a specific enough mark of which structural event caused the soma improvement.**

The canonical receipts below were run by GitHub Actions on this repository's v0.7 implementation (workflow run `31210731500`).

## What is held fixed

`CreditTransportArbor` subclasses `v07_persistent_ephaptic.PersistentEphapticArbor` directly. Therefore v0.8 inherits without reimplementation:

- binary anatomy;
- fixed `K_arbor` / `K_bath` only;
- second-order damped wave transport;
- explicit current-source density and grounded quasi-static extracellular solve;
- persistent one-cell growth cones;
- separate branching, reconnection and connectivity-safe retraction.

Every learning arm uses the same **coherent v0.7 extracellular guidance**. Only the delayed stabilization carrier changes.

One developmental timing parameter is deliberately changed for *all* arms: `new_cell_grace = 18` slow ticks. A graph-retrograde carrier cannot be tested fairly if a distal newborn branch can be removed before its reward packet could physically arrive.

## Carriers

- `global`: fixed-delay scalar reward gated by current structural eligibility.
- `retrograde`: freezes eligibility at soma evaluation, then reward moves outward one arbor graph edge per slow tick.
- `scrambled_retrograde`: same graph latency and eligibility-value distribution, but spatial identity is shuffled.
- `trophic`: signed soma-origin credit diffuses in the 2-D bath and is gated locally by eligibility.
- `hybrid`: retrograde + trophic at reduced gain.
- `no_credit`: identical v0.7 growth/guidance/retraction with no returned consequence.

## Self-test

```bat
python3.13 v08_credit_transport/selftest.py
```

The GitHub CI self-test requires a 70-cell connected binary body, exactly two mature conductivities, nonzero solved extracellular field power, retrograde latency correlation `1.0` with slope `1.0 tick/graph edge`, persistent v0.7 structural events, and restored final mass.

## Carrier instrument — transport is real

Seed 2 with equal synthetic eligibility:

| carrier | delivered cells | corr(distance, first arrival) | latency slope |
|---|---:|---:|---:|
| global | 70 | flat | fixed delay |
| retrograde | 69 | **1.0000** | **1.000 tick/edge** |
| scrambled retrograde | 69 | **1.0000** | **1.000 tick/edge** |
| trophic | 49 | **0.9486** | **1.832 ticks/edge** |

A free-learning null therefore cannot be dismissed as “the retrograde signal never got there.”

## Positive control — if the eligibility tag is correct, credit changes anatomy

A removable off-task side branch is deliberately tagged. The same retrograde carrier receives positive, zero or negative consequence before four paired stochastic connectivity-safe retractions.

128 trials:

| consequence | tagged branch survival | mean support after credit |
|---|---:|---:|
| positive `+0.9` | **0.9875** | **0.7040** |
| zero | 0.9391 | 0.4500 |
| negative `-0.9` | **0.6328** | **0.1960** |

Paired differences:

```text
positive - zero      +0.0484   no Monte-Carlo sign-flip exceedance in 50,000 draws
positive - negative  +0.3547   no exceedance in 50,000 draws
zero - negative      +0.3063   no exceedance in 50,000 draws
```

This is a **mechanical positive control**, not a learning result. It establishes that transport + support + retraction can select anatomy when eligibility identifies the right branch.

## Free carrier screen — 8 paired seeds

Settings: lag `+20`, 70-cell bootstrap, 30 developmental ticks, 32 fast drive steps and 120-step probes.

| carrier | A-B path | edge50 delay | task contrast |
|---|---:|---:|---:|
| global | +1.75 | +7.50 | +0.0645 |
| retrograde | +0.125 | -1.875 | -0.0221 |
| trophic | 0.00 | -2.125 | -0.0259 |
| hybrid | +0.125 | +3.25 | +0.0021 |
| scrambled retrograde | +1.25 | +4.875 | +0.0038 |
| no credit | 0.00 | -2.125 | -0.0259 |

No carrier establishes a reliable advantage over `no_credit`. The largest apparent trend is global broadcast:

```text
global - no_credit
contrast   +0.0904   exact sign-flip p = 0.2891
edge50     +9.625    p = 0.1250
```

Retrograde is essentially identical to no credit:

```text
retrograde - no_credit
contrast   +0.0038   p = 0.9688
edge50     +0.25     p = 0.9375
```

The trophic arm is numerically identical to no credit in this short assay: the carrier spreads physically, but too little signed trophic signal overlaps still-relevant distal eligibility on this timescale to alter selected anatomy.

## Main confirmation — 16 paired retrograde vs no-credit seeds

```text
                         retrograde     no credit
mean A-B path               +1.00          +0.50
mean edge50                 +4.12          +2.06
mean task contrast          -0.0156        +0.0095
```

Paired retrograde minus no credit:

```text
path       +0.500    SD 1.366    exact p = 0.2500
edge50     +2.063    SD 11.018   exact p = 0.4839
common25   +2.063    SD 8.370    exact p = 0.3842
contrast   -0.0251   SD 0.2263   exact p = 0.6639
```

This is a functional null. Retrograde consequence reaches eligible distant material, but it does not reliably improve temporal discrimination.

## What the null isolates

```text
CAN SOMA CONSEQUENCE REACH DISTANT STRUCTURE?
    yes

CAN DELAYED CONSEQUENCE ALTER SURVIVAL OF A CORRECTLY TAGGED BRANCH?
    yes

DOES THE NATURAL ACTIVITY/STRUCTURAL ELIGIBILITY TRACE TAG
THE STRUCTURAL EVENT THAT CAUSED THE SOMA IMPROVEMENT?
    not shown
```

The current eligibility trace mostly says **“this material was recently active / recently structural.”** A route can be active without being the structural change responsible for making the temporal task better. A perfectly faithful retrograde carrier cannot fix a non-causal tag.

## Verdict

**[V] Explicit graph-retrograde credit transport.** First-arrival time is graph distance at one slow tick per edge.

**[V] Distinct diffusible trophic transport.** Soma-origin credit spreads through the bath with a slower distance/latency relation.

**[V] Credit can control anatomy when eligibility is causally correct.** Positive and negative retrograde consequence strongly separate survival of a deliberately tagged removable branch.

**[K] “v0.7 failed only because reward had no physical return path.”** Killed. Adding a return path does not repair free learning.

**[K] “Retrograde credit is sufficient.”** Killed for this implementation by the 16-seed paired null.

**[~] Biology.** Retrograde and trophic carriers are biologically inspired computational abstractions, not models of a particular molecular pathway.

## Run

```bat
python3.13 v08_credit_transport/selftest.py
python3.13 v08_credit_transport/credit_instrument.py --out credit_instrument.json
python3.13 v08_credit_transport/eligibility_control.py --trials 128 --out eligibility_control.json
python3.13 v08_credit_transport/train.py --seeds 8 --ticks 30 --drive-steps 32 --probe-steps 120 --arms global,retrograde,trophic,hybrid,scrambled_retrograde,no_credit --out screen8
python3.13 v08_credit_transport/train.py --seeds 16 --ticks 30 --drive-steps 32 --probe-steps 120 --arms retrograde,no_credit --out retro16
```

## Next wall — v0.9

Do **not** add another carrier. Freeze retrograde transport and change only what gets tagged before consequence returns:

```text
activity eligibility      recent use only                 v0.8 baseline
young-event tag           exact cells added by event
branch-competition tag    new bypass versus old shortcut
signed timing tag         local event × early/late soma error
shuffled event tag        same sparsity, wrong location
```

> **Can a purely local structural event leave a specific enough eligibility mark that a later soma consequence stabilizes the event that actually improved temporal computation?**
