# Functional Arbor — ChatGPT/Sol line

A pulse-driven morphogenetic medium that grows and remodels a body because parts of that body improve what happens at a soma.

The repo keeps every kill instead of rewriting the story after the fact.

## Version ladder

### v0.1 — function before appearance
Three-factor structural plasticity: local current eligibility × soma consequence × exposed growth front. Maturation exposed the “conductive soup” failure: a scaffold is not functional if the background routes around it.

### v0.2 — physical timing
Claude's two-pulse task was kept, but the diffusive substrate was replaced by a second-order wave. Independently measured wavefront timing, not only peak timing, moved toward the requested lag under reward.

### v0.3 — geometry vs speed
The timing effect was decomposed. The graded-material implementation learned mainly **local conduction speed**; its path geometry actually pushed timing the wrong way. This killed the claim that v0.3 had grown a geometric delay cable.

### v0.4 — geometry-only controlled capability
Mature material was made binary and fixed-speed. Two controlled cables could learn a delay only by structural detour/pruning. This proved geometry can carry the learned delay, but the cables and the useful local remodeling grammar were supplied.

### v0.5 — free branching arbor invents the detour location
`v05_free_arbor/` removes the pre-drawn cables. One soma cell grows into a branching tree through a PhaseStigmergy-style Laplacian/opportunity process. Every seed is then fixed at exactly 90 binary cells. A real pulse supplies local eligibility; a generic local detour/prune proposal may occur anywhere legal in the free body; soma credit decides whether it survives.

Sixteen paired reward-vs-shuffled-credit seeds at lag +20:

```text
unique path A-B         reward-shuffle +5.9375 cells   p=0.00659
edge50 wavefront A-B    reward-shuffle +19.875 frames  p=0.02826
common25 wavefront A-B  reward-shuffle +32.0625 frames p=0.00616
task contrast           reward-shuffle +0.3393         p=0.00073
```

Inside reward-grown organisms, the structural change predicts the independently measured timing change:

```text
corr(Δ path length, Δ edge50 delay) = 0.9645
slope                              = 4.97 frames / lattice edge
```

Delete every side branch and rebuild only the two learned unique paths: the paired timing effect remains (`edge50 +26.5`, p=0.00659). So side-branch loading is not required for the effect.

The honest v0.5 wall sentence is:

> **A free PhaseStigmergy-style branching arbor can use a generic local grow/prune operation, pulse eligibility, and soma credit to discover task-useful geometric delays inside anatomy it grew itself.**

The remaining caveat is the **plasticity grammar**: the model is given the generic U-detour/prune operation. It discovers where, which route, and how many; it does not invent the existence of that topological move.

See [`v05_free_arbor/README.md`](v05_free_arbor/README.md) and [`docs/LEDGER_V05.md`](docs/LEDGER_V05.md).

### v0.6 — remove the named detour shape; test ephaptic guidance
`v06_ephaptic_growth/` removes the U-shaped replacement primitive. A proposal now begins at an activity-used arbor site, grows one nearest-neighbour cell at a time, may reconnect to old arbor, and then uses connectivity-safe pruning to restore the same binary mass/tree. The branch trajectory is not prescribed.

A toy ephaptic-like extracellular field is computed from a spatially blurred analytic membrane-current proxy. The field can bias the growth-cone walk, while soma credit still decides whether a completed structural episode survives.

Sixteen paired seeds, sparse 70-cell bodies, lag +20:

```text
legal reconnect proposal yield
full ephaptic       0.760
no ephaptic         0.556
magnitude only      0.639
phase shuffle       0.802

full - no ephaptic       +0.2049   p=0.00156
full - magnitude only    +0.1215   p=0.00238
```

So the spatial field proxy **helps exploration**. But it does not improve final task performance over blind exploration:

```text
full - no ephaptic
path difference   +0.75     p=.646
edge50 delay      -0.75     p=.933
contrast          -0.0033   p=.955
```

And soma-locked phase is not specifically supported: phase-shuffling the reference does not hurt proposal yield or final learning.

Credit still matters. `full - no_credit` gives path `+2.6875` (p=.0461), edge50 `+14.125` (p=.0478), and contrast `+0.2025` (p=.000214).

The v0.6 wall sentence is:

> **An ephaptic-like spatial field can make generic growth-cone exploration more efficient, but this implementation does not show a phase-specific ephaptic learning rule and does not need the field to reach the temporal solution. Soma consequence remains the selector that turns exploration into function.**

See [`v06_ephaptic_growth/README.md`](v06_ephaptic_growth/README.md), [`docs/LEDGER_V06.md`](docs/LEDGER_V06.md), and [`docs/NEXT_V07.md`](docs/NEXT_V07.md).

### v0.7 — explicit extracellular field + persistent development
`v07_persistent_ephaptic/` replaces the blurred v0.6 field with a grounded quasi-static extracellular solve driven by explicit current-source density, and replaces atomic growth/reconnect/prune episodes with persistent one-cell growth cones plus separate slow stabilization and retraction.

The 16-seed short receipt preserves a useful negative: coherent soma-locked phase is indistinguishable from phase-scrambled guidance on final task contrast (`+0.0014`, p=.9847). Extracellular information still improves reconnection search versus no-field (`+0.0644 reconnections/extension`, p=.0373), but coherent and magnitude-only search rates are the same.

An 8-seed longer-development check suggests directional field guidance can improve final task contrast over no-field (`+0.1435`, p=.0078) and magnitude-only (`+0.1257`, p=.0469), while phase-scramble remains identical to coherent and phase reversal is harmful. So **field geometry/direction may matter; correct absolute phase still has not earned a role**.

The slow delayed soma-credit rule itself is not yet robust against no-credit. See `v07_persistent_ephaptic/README.md` and `docs/LEDGER_V07.md`.

### v0.8 — physical credit transport works, free assignment does not
`v08_credit_transport/` freezes the v0.7 wave, extracellular solve and persistent growth, then adds explicit delayed return channels from soma to structure. Graph-retrograde credit moves exactly one arbor edge per slow tick; a separate trophic carrier diffuses through the bath.

The carrier itself is calibrated and a deliberately correct branch tag is a strong positive control: positive consequence keeps the tagged branch alive much more often than negative consequence. But free retrograde learning remains null. In 16 paired seeds, retrograde minus no-credit gives contrast `-0.0251` (`p=.6639`) and edge50 `+2.063` (`p=.4839`).

So v0.8 moves the bottleneck from **transport** to **eligibility**: reward can get back to a branch, but recent activity is not a causal enough mark of which structural change made the soma better.

See `v08_credit_transport/README.md` and `docs/LEDGER_V08.md`.

### v0.9 — exact structural-event tags are still too coarse
`v09_causal_eligibility/` freezes the v0.8 retrograde carrier and varies only what is tagged before delayed consequence returns: broad activity, exact newly born cells, reconnect bypass-vs-shortcut competition, and a sparse signed timing-event mark, each with appropriate shuffled/no-credit controls where possible.

The 8-seed screen gave a suggestive event-cell trend, so it was expanded without gain changes. In the 16-seed confirmation:

```text
                         event     shuffled-event    no-credit
mean contrast            +0.0598       +0.0157        +0.0188
mean edge50              +9.5625       +6.1250        +5.1250

paired event - shuffled
contrast                 +0.0440   p=.3144
edge50                   +3.4375   p=.4622

paired event - no-credit
contrast                 +0.0409   p=.4344
edge50                   +4.4375   p=.3049
```

So **remembering exactly which cells were born is still not sufficient for robust free credit assignment**. Reconnect competition tags also fail their matched screen. The signed timing tag is not counted as killed because it was too sparse/late to deliver enough credit to exercise the mechanism.

The next mark should be closer to causation itself: measure local transport before and after a structural event and tag the **flow redistribution** it actually caused, e.g. `event_mask × (J_after - J_before)`, rather than simply activity or birth identity.

See `v09_causal_eligibility/README.md`, `docs/LEDGER_V09.md`, and `examples/v09/ci_summary.json`.

## Run examples

```bat
python3.13 v07_persistent_ephaptic/selftest.py
python3.13 v08_credit_transport/selftest.py
python3.13 v09_causal_eligibility/selftest.py
python3.13 v09_causal_eligibility/train.py --seeds 16 --ticks 36 --drive-steps 40 --probe-steps 150 --arms event,event_shuffle,no_credit --out v09_event16
```

MIT. Experimental computational morphogenesis; not a model of literal neuronal development.
