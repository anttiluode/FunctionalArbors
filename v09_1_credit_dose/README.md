# Functional Arbor v0.9.1 — credit-dose autopsy

This is an **instrument audit**, not a new learning mechanism.

v0.9 compared several eligibility semantics, but the arms also delivered very different total amounts of structural credit. Claude noticed that the arm-level means were compatible with an inverted-U in delivered credit mass. v0.9.1 tests that directly.

The exact v0.9 `event` eligibility semantics are frozen. Only `retrograde_credit_gain` changes.

Canonical GitHub Actions run: `31238081016`, 16 paired seeds.

## Registered sweep

The v0.9/v0.8 default retrograde gain is `0.48`. Multipliers:

```text
0, 0.125, 0.25, 0.5, 1, 2, 4
```

All doses use the same 70-cell bootstrap body per seed, fixed-speed binary material, v0.7 wave/extracellular solve, coherent guidance, persistent structural dynamics, exact v0.9 birth-event tag, reward schedule, and one-edge-per-tick retrograde carrier.

The primary x-axis is **actually delivered credit mass**.

## Result

Mean values:

| gain | delivered credit | contrast | edge50 | A-B path |
|---:|---:|---:|---:|---:|
| 0x | 0.000 | +0.0188 | +5.12 | +0.44 |
| 0.125x | 0.247 | +0.0249 | +8.12 | +0.44 |
| 0.25x | 0.493 | +0.0185 | +7.31 | +0.44 |
| 0.5x | 0.980 | +0.0155 | +7.19 | +0.94 |
| 1x | 1.992 | +0.0598 | +9.56 | +1.44 |
| 2x | 3.941 | +0.0752 | +5.62 | +0.56 |
| 4x | 7.786 | +0.0391 | +3.88 | +0.69 |

The arm-level mean is visually non-monotone, with its highest mean contrast at 2x. But the **registered paired falsification does not support a robust inverted-U dose law**:

```text
1x - 0x
contrast +0.04094   p=.43445
edge50   +4.4375    p=.30493

1x - 4x
contrast +0.02067   p=.74756
edge50   +5.6875    p=.13263

4x - 0x
contrast +0.02026   p=.64478
edge50   -1.2500    p=.66235
```

The descriptive per-seed quadratic coefficient against actual delivered credit mass has mean `-0.01020`, but its exact sign-flip p is `.17905`; 7/16 seed fits are concave and 9/16 convex. So the mean curve is not a seed-stable dose response.

An unregistered check of the mean-optimal 2x dose also remains null:

```text
2x - 0x contrast  +0.05633   p=.16669
2x - 4x contrast  +0.03607   p=.41406
```

## Verdict

> **Delivered credit dose is a real confound that must be reported, but it does not explain away the v0.8/v0.9 carrier/tag results in this 16-seed audit. The apparent inverted-U exists mainly at the aggregate-mean level and is not reproducible enough across seeds to serve as the mechanism.**

This clears the specific objection that the v0.9 table was *only* a plasticity-temperature curve. It does **not** prove tag semantics are correct; v0.9 remains a null on causal eligibility.

The next instrument audit is the **soma/readout tap test**: freeze anatomy and transport, vary only how the soma samples the distributed wave field.

## Run

```bat
python3.13 v09_1_credit_dose/selftest.py
python3.13 v09_1_credit_dose/sweep.py --seeds 16 --ticks 36 --drive-steps 40 --probe-steps 150 --out v091_dose16
```

Compact receipt: `examples/v091/ci_summary.json`.
Full ledger: `docs/LEDGER_V091.md`.
