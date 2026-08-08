# v0.9.1 ledger — credit-dose autopsy

Canonical execution: GitHub Actions run `31238081016`, Python 3.12, 16 paired seeds.

## Question

Can the v0.9 between-arm pattern be explained mainly by **how much structural credit was delivered**, rather than by what the eligibility tags meant?

## Frozen machinery

Exact v0.9 `event` tag; exact v0.8 graph-retrograde carrier; v0.7 wave/extracellular solve/persistent growth; coherent guidance; binary fixed-speed 70-cell body; same reward computation and evaluation schedule.

Only `retrograde_credit_gain` changes: 0, .06, .12, .24, .48, .96, 1.92.

## Mean receipt

```text
mult   delivered credit   contrast   edge50   A-B path
0      0.000              +.0188     +5.12    +.44
.125   .247               +.0249     +8.12    +.44
.25    .493               +.0185     +7.31    +.44
.5     .980               +.0155     +7.19    +.94
1      1.992              +.0598     +9.56    +1.44
2      3.941              +.0752     +5.62    +.56
4      7.786              +.0391     +3.88    +.69
```

## Registered paired tests

```text
1x - 0x: contrast +.04094 p=.43445; edge50 +4.4375 p=.30493
1x - 4x: contrast +.02067 p=.74756; edge50 +5.6875 p=.13263
4x - 0x: contrast +.02026 p=.64478; edge50 -1.2500 p=.66235
```

Per-seed quadratic fit of contrast against actually delivered credit: mean q2 `-.01020`, exact sign-flip `p=.17905`; 7/16 concave, 9/16 convex.

Unregistered descriptive checks:

```text
2x - 0x contrast +.05633 p=.16669
2x - 4x contrast +.03607 p=.41406
```

## Verdict

**[V]** Delivered credit mass varies materially across arms and should always be reported.

**[K]** “The v0.9 table is simply an inverted-U plasticity-temperature curve.” Not supported by the paired 16-seed dose sweep.

**[~]** Aggregate mean contrast is non-monotone and peaks at 2x, so dose sensitivity exists descriptively; it is not seed-stable enough to explain the lineage results.

**[ ]** Causal eligibility remains unresolved. This audit neither rescues nor kills v1.0 causal-flow tagging.

## Next

Soma/readout tap test: freeze learned/fixed anatomy and propagation, vary only the spatial readout operator (one cell, cross, patch, weighted field, separated taps). Determine whether readout geometry changes the temporal-response regime before adding new credit machinery.
