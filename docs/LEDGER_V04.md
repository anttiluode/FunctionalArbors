# v0.4 ledger — fixed-speed geometry

## Question

v0.3 learned timing through material speed. v0.4 forbids that channel and asks whether geometry itself can store the delay.

## Construction invariants

- structural state is binary;
- every arbor bond has one identical conductivity;
- bath has one identical conductivity;
- no thickness, graded M, substrate-dependent K, or route-specific speed;
- structural mass is constant during controlled remodeling;
- source dose and carrier waveform are identical between target/distractor classes.

## Kill before result

The first strict free-interface attempt exposed a structural limitation: addition-only growth cannot make an already-existing shortest connection longer. A geometric delay requires turnover — grow a detour and remove the shortcut. The controlled assay therefore adds local plaquette remodeling at fixed total material.

## Main receipt

Lag 10, 16 reward vs shuffled-credit seeds.

Reward converged 16/16 to one A detour: dL=+2, edge50=+11, common25=+11.

Paired reward-shuffle:

- dL +1.375 ±1.893 cells, exact sign-flip p=.02393
- edge50 +7.688 ±10.038 frames, p=.00513
- common25 +7.563 ±10.411 frames, p=.02393
- contrast +.1969 ±.1758, p=.00037

Anti-credit, 8/8:

- dL=-2
- edge50=-11
- contrast=-.2343

## Interpretation

[V] The timing can be learned by geometry alone in the controlled binary-cable system.

[V] The sign of the teaching signal controls the sign of the morphology and timing.

[K] The stronger addition-only claim: false / structurally blocked once the shortcut exists.

[~] The free-field dendritic morphology has not yet learned this de novo. The plaquette remodeling grammar is deliberately supplied.

[~] The lag code is quantized by the allowed structural move; lag 5 and 10 both choose one detour, while 15 and 20 mostly choose two.

## Wall sentence

> **When local conduction speed is fixed, soma-level credit can still write time into a binary body by moving material into a longer route and pruning the shortcut; reversing credit reverses the grown delay.**
