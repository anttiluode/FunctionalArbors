# Functional Arbor v0.6 ledger — 2026-08-07

## Question

Can the free binary arbor remove the v0.5 U-detour shape primitive, and can an ephaptic-like extracellular field supply local guidance for the resulting growth-cone exploration?

## Build

v0.6 keeps binary fixed-speed material and exact final mass. The named U replacement is removed. A proposal now starts from an activity-used arbor site, grows a nearest-neighbour tip one cell at a time, may reconnect to the existing tree, and then uses connectivity-safe pruning to return to the original mass/tree state.

A toy extracellular field is formed by spatially smoothing the analytic velocity on the active arbor, differentiating it, and accumulating both magnitude `H` and soma-phase-referenced vector `G`.

This is a computational proxy, not a volume-conductor model.

## Main 16-seed receipt

Sparse bodies were used deliberately: 70 cells, 8 cone attempts per structural episode. In the earlier dense 90-cell/large-search version blind random exploration already found reconnections almost every time, making ephaptic guidance uninformative.

### Search efficiency

- full legal proposal yield: 0.7604
- no ephaptic: 0.5556
- magnitude only: 0.6389
- phase shuffle: 0.8021

Paired exact sign-flip:

- full - no ephaptic: +0.2049, p=0.00156
- full - magnitude only: +0.1215, p=0.00238
- magnitude - no ephaptic: +0.0833, p=0.0232

Interpretation: the field proxy helps growth-cone walks find reconnecting topology. Directional spatial structure helps beyond magnitude alone.

### Phase kill

Phase shuffle does not reduce yield or final task performance. Therefore v0.6 does not support the stronger claim that the soma-referenced phase sign is the useful developmental variable.

### Final learning

Full and no-ephaptic reward arms reach statistically indistinguishable final task states:

- path difference paired full-no: +0.75, p=.646
- edge50 paired full-no: -0.75, p=.933
- contrast paired full-no: -0.0033, p=.955

Thus ephaptic guidance is not necessary for the final solution when blind exploration receives the same number of developmental episodes.

### Credit survives

Full versus no-credit:

- path +2.6875, p=.0461
- edge50 +14.125, p=.0478
- contrast +0.2025, p=.000214

Full versus shuffled credit:

- contrast +0.1765, p=.0104

So local field guidance does not itself know which route is useful; the soma consequence remains the selector.

### Geometry/timing

Within full:

- corr(delta path length, delta edge50) = .9219
- slope = 3.71 frames/edge

## Wall sentence

> **An ephaptic-like spatial field can make generic growth-cone exploration more efficient, but this v0.6 does not show a phase-specific ephaptic learning rule and does not need the field to reach the temporal solution. The global soma consequence remains the part that turns exploration into function.**

## What died

- “phase-referenced ephaptic vector is the missing detour instruction” — not supported.
- “without ephaptic field the free arbor cannot discover delay geometry” — false in this implementation.

## What survived

- no named detour shape is required;
- local extension/reconnection/pruning can generate task-useful topology;
- extracellular spatial structure can improve proposal efficiency;
- binary fixed-K geometry still controls timing;
- credit assignment remains essential.
