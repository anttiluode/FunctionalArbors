# Functional Arbor v0.5 ledger — free geometric delay

## Question
Can the free dendrite-like field-grown arbor, rather than two pre-drawn cables, discover a useful delay through geometry alone?

## Construction invariants
- binary body B in {0,1}
- exactly one K for every occupied-occupied bond
- mature bath K fixed and nearly insulating
- 90 structural cells in every seed before learning
- every remodeling move preserves exactly 90 cells
- body remains one 4-neighbour tree connected to soma and both sources

## Instrument calibration
Seed-2 free body: one pulse-eligible generic detour increases A path 14->16, leaves B at 13, and moves edge50 A-B 7->17 while K set remains {0.0002, 2.5}.

## Main receipt
16 paired seeds, lag +20, 28 proposed remodels, same field-grown initial body for reward and shuffle.

- path length A-B reward-shuffle: +5.9375 cells, p=0.00659
- edge50 delay reward-shuffle: +19.875 frames, p=0.02826
- common25 delay reward-shuffle: +32.0625 frames, p=0.00616
- soma task contrast reward-shuffle: +0.33927, p=0.00073

Reward's within-organism structural change predicts its wavefront timing change:
- r = 0.96448
- slope = 4.9715 frames per lattice edge
- intercept = -0.993 frames

Accepted reward proposals: 31 A-path, 11 B-path, 5 off-path, 47 total.

## Path-only autopsy
Delete every side branch and reconstruct only each final unique A/B route.

- edge50 reward-shuffle +26.5 frames, p=0.00659
- common25 reward-shuffle +31.875 frames, p=0.00604

Therefore side-branch impedance is not required for the effect; route geometry alone is sufficient in the diagnostic reconstruction.

## Important failures/caveats
- One seed already scored well without the desired edge delay and therefore accepted no reward remodels.
- One highly asymmetric bootstrap body became task-degenerate.
- anti-credit is not a clean sign mirror in arbitrary free initial anatomy; v0.4 remains the clean controlled sign test.
- the generic U-detour/prune grammar is engineered. The system discovers location/route/count, not the existence of the topological move itself.

## Verdict
[V] The free branching arbor can discover functional geometric delay under fixed-speed, fixed-mass constraints.

[~] This is a computational morphogenesis result, not evidence for biological dendrite development.
