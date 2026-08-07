# Functional Arbor v0.5 — the free arbor invents the detour

v0.4 proved a controlled capability: if two fixed-speed binary cables are already present, a local grow-detour/prune-shortcut operation can learn a physical delay with geometry alone.

v0.5 removes the pre-drawn cables.

> **Can a PhaseStigmergy-style branching body grow first, then discover the required geometric delay inside its own free anatomy?**

For this build, the answer is **yes, with a deliberately narrow meaning**:

> A free field-grown binary tree can be remodeled by pulse-eligible, soma-selected local detours so that unique source-to-soma path length and independently measured wavefront delay move together toward a temporal discrimination task.

The local remodeling *operation* is still hand-designed. The location, side, source route, number of accepted detours, and final delay are not.

---

## Four invariants

All four restrictions requested after v0.4 are construction invariants.

### 1. Binary material

```text
B(x) = 0  empty
B(x) = 1  arbor
```

No thickness variable exists.

### 2. Identical material speed

Every occupied-to-occupied lattice bond has exactly one conductivity:

```text
K_arbor = 2.5
```

Every other bond has the same tiny mature bath value:

```text
K_bath = 0.0002
```

There is no graded `K(M)`, myelination analogue, caliber analogue, substrate multiplier, or hidden local speed code.

### 3. Fixed total mass

Every seed reaches exactly **90 occupied cells** before learning begins. Remodeling can only move those cells.

A detour replaces one shortcut cell with three detour cells, so two weak terminal leaves elsewhere are pruned to pay the +2-cell cost.

### 4. Connectivity-aware pruning

The body is kept as one 4-neighbour tree. Every proposed remodeling must preserve:

- soma connectivity;
- connection to both sensory source regions;
- total mass;
- `edges = vertices - 1`.

Disconnected debris and hidden parallel shortcuts are rejected.

---

## How the free body grows

The organism begins as **one soma cell**.

It is not given two cables.

During bootstrap, a Laplacian opportunity field runs from the currently active sensory region toward the absorbing body. Only empty cells adjacent to exactly one existing arbor cell are eligible for deposition. Growth is stochastic, flux-biased, and modulated by a quenched *morphogenesis-only* landscape.

A real source pulse is also propagated through the permissive developmental bath; its local use trace biases the exposed interface.

A and B are alternated until both sensory regions are reached. Then a continuous outer reservoir grows spare side branches until every seed reaches the same 90-cell budget.

Typical bootstrap bodies at `N=31` have roughly 17–24 leaves and 15–21 junction cells. They are branching trees, not two lines.

---

## How the free body remodels

The generic local operation is transferred from v0.4 but is no longer attached to a named cable.

After a real pulse, any sufficiently used straight degree-2 segment anywhere in the body may be proposed for replacement:

```text
----X----        ----   ----
     \              \___/
```

More exactly, the central shortcut cell is replaced by a three-cell U-shaped plaquette bypass. Two low-use leaves elsewhere pay for the extra cells.

The proposal code does **not** ask whether the segment belongs to A or B. It only sees local eligibility and legal local geometry.

The soma then evaluates the two-pulse task:

```text
TARGET      A, then B after lag
DISTRACTOR  B, then A after lag
```

`reward` keeps a structural proposal only if target-vs-distractor soma contrast improves.

`shuffle` sees the same proposed moves but randomizes the sign of the credit.

This is a structural hill-climber with pulse-local eligibility. It is a capability mechanism, not a claim that dendrites use this exact accept/reject algorithm.

---

# Meter self-test

Before the ensemble, the free-body meter has to see one generic detour.

Seed 2 smoke body:

```text
field-grown mass          70
leaves                    19
junctions                 16
tree                      yes
A/B path lengths          14 / 13
```

A real A pulse selects a legal generic detour on the free body. The move gives:

```text
A path length             14 -> 16
B path length             13 -> 13
edge50 A-B delay           7 -> 17 frames
common25 A-B delay         1 -> 12 frames
mass                      unchanged
body                      still one tree
bond K values             {0.0002, 2.5} only
```

Run:

```bat
python3.13 v05_free_arbor/selftest.py
```

---

# Main experiment — 16 paired seeds, lag 20

Settings:

```text
N                         31
bootstrap mass            90 cells, every seed
requested A-B task lag    +20 frames
remodel proposals         28
reward vs shuffled credit paired from the same initial body
```

## Final reward versus shuffle

| measurement | reward mean | shuffle mean | paired reward−shuffle | exact sign-flip p |
|---|---:|---:|---:|---:|
| unique path length A−B | **+3.188 cells** | −2.750 | **+5.938** | **0.00659** |
| edge50 wavefront A−B | **+13.375 frames** | −6.500 | **+19.875** | **0.02826** |
| common25 wavefront A−B | **+16.875 frames** | −15.188 | **+32.063** | **0.00616** |
| task contrast | **+0.4132** | +0.0739 | **+0.3393** | **0.00073** |

The ensemble does not land at exactly +20 in every body because the starting free trees have different path lengths, branch loads, and a coarse +2-edge remodeling quantum. The relevant paired result is that correct soma credit pushes both **physical route length** and **physical wavefront delay** in the task-required direction relative to shuffled credit.

---

## The strongest mechanism receipt

Within the 16 reward-grown organisms, compare the change caused by remodeling:

```text
Δ(A-B path length)
versus
Δ(A-B edge50 wavefront delay)
```

Measured:

```text
Pearson r        0.9645
slope            4.97 simulation frames / added lattice edge
intercept        -0.99 frames
```

So the timing change is tightly predicted by the geometric route change.

This also catches an important non-hardcoded case. One seed began with A **far too slow** (`dL=+8`, edge50 `+47`). Reward did not blindly add more A detours. It accepted B-side detours instead, ending near `dL=+2`, edge50 `+15`. The local move is not “always lengthen A”; soma consequence decides which free route is worth altering.

Across all accepted reward moves:

```text
on the current A functional path     31
on the current B functional path     11
off both functional paths             5
total accepted                        47
```

---

# Path-only reconstruction

A free tree has side branches, so perhaps timing changed because those branches altered impedance rather than because the source-to-soma route got longer.

To test that, `path_only.py` rebuilds each learned organism using **only** its unique A→soma and B→soma paths. Every side branch is deleted. Conductivity remains fixed.

Sixteen paired seeds:

| path-only measurement | reward mean | shuffle mean | paired difference | p |
|---|---:|---:|---:|---:|
| edge50 A−B | **+17.0** | −9.5 | **+26.5** | **0.00659** |
| common25 A−B | **+17.75** | −14.125 | **+31.875** | **0.00604** |

The unique learned routes alone preserve the timing effect.

This is the cleanest evidence in v0.5 that the relevant mechanism is **route geometry**, not graded material speed and not merely side-branch loading.

Run:

```bat
python3.13 v05_free_arbor/path_only.py ^
  examples/v05/main8_mass90/free_results.json ^
  examples/v05/main8c_mass90/free_results.json ^
  --lag 20 --out examples/v05/path_only16.json
```

---

# What failed / remains imperfect

### The free task is not a perfect pure-delay meter

One seed already had strong target/distractor contrast despite an edge50 delay near zero, so reward made no structural move. Another highly asymmetric bootstrap body reached a degenerate near-zero task response. A free wave tree has phase, reflections and branch loading in addition to its unique path delay.

That is why v0.5 does **not** infer the mechanism from task score alone. It requires the independent path-length, wavefront, and path-only receipts above.

### Anti-credit is not a clean mirror in a random starting body

In the controlled v0.4 cables, reversing credit cleanly reversed the detour. In the free arbor, arbitrary initial asymmetry means “make the discrimination worse” can be achieved by overshooting, moving either route, or driving the task toward zero. The 8-seed anti run mostly moves negative, but one heavily over-delayed starting body goes the other way. Keep v0.4 as the clean sign-control; use shuffled credit as the primary v0.5 null.

### The local remodeling grammar is still supplied

The organism invents **where** to detour, **which route** to change, and **how many** detours survive. But we supplied the generic operation “replace a straight segment with a U-shaped bypass and pay for it by pruning weak leaves.”

So the strongest honest sentence is not yet “arbitrary morphogenesis invented structural plasticity itself.” It is:

> **A free PhaseStigmergy-style branching arbor can use a generic local grow/prune operation, pulse eligibility, and soma credit to discover task-useful geometric delays inside its own anatomy.**

That is a substantial step beyond the two pre-drawn cables of v0.4.

---

# Run

Main experiment can be run in one long call:

```bat
python3.13 v05_free_arbor/train.py --seeds 16 --lag 20 --mutations 28 --bootstrap-mass 90 --arms reward,shuffle --out free16
```

Or in two chunks like the committed receipt:

```bat
python3.13 v05_free_arbor/train.py --seeds 8 --seed-start 0 --lag 20 --mutations 28 --bootstrap-mass 90 --arms reward,shuffle --out examples/v05/main8_mass90
python3.13 v05_free_arbor/train.py --seeds 8 --seed-start 8 --lag 20 --mutations 28 --bootstrap-mass 90 --arms reward,shuffle --out examples/v05/main8c_mass90
```

Plot the receipt:

```bat
python3.13 v05_free_arbor/plot_results.py --results examples/v05/free16_combined.json --outdir examples/v05
```

---

# Wall verdict

**[V] Free morphogenesis.** One soma cell grows into a branching binary tree connecting two sensory regions by a Laplacian/opportunity field process; no source-to-soma cable is drawn in advance.

**[V] Fixed-speed geometry-only transport.** Mature arbor bonds all have identical K; total material is exactly 90 cells per seed and is conserved through learning.

**[V] Functional geometric remodeling.** Reward versus shuffled credit changes unique path length and independently measured wavefront delay together across 16 paired seeds.

**[V] Route sufficiency.** Delete every side branch and retain only the two learned unique paths: the paired timing effect survives.

**[~] Credit algorithm.** The accept/reject hill-climber is an engineered global teaching rule, not biological evidence.

**[~] Local grammar.** The U-detour/prune operation is supplied. The next frontier is to let more general local turnover primitives compete rather than giving the model one useful topological move.

**[K] “The free system merely tuned conduction speed.”** Impossible by construction in v0.5.

The phrase that v0.4 only earned in a controlled two-cable toy now survives in a free branching body:

> **The arbor can grow its own physical delay operator inside anatomy it grew itself.**
