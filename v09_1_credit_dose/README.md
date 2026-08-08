# Functional Arbor v0.9.1 — credit-dose autopsy

This is an **instrument audit**, not a new learning mechanism.

v0.9 compared several eligibility semantics, but the arms also delivered very different total amounts of structural credit. Claude noticed that the arm-level means are compatible with an inverted-U in delivered credit mass: zero credit near baseline, roughly 2–3 units somewhat better, and the high-dose activity arm worse.

v0.9.1 freezes the exact v0.9 `event` eligibility semantics and changes **one parameter only**: `retrograde_credit_gain`.

## Registered sweep

The v0.9/v0.8 default retrograde gain is `0.48`. Multipliers:

```text
0, 0.125, 0.25, 0.5, 1, 2, 4
```

so nominal gains are:

```text
0, .06, .12, .24, .48, .96, 1.92
```

All doses use the same:

- 70-cell bootstrap body per seed;
- fixed-speed binary material;
- v0.7 wave and extracellular solve;
- coherent guidance;
- persistent structural dynamics;
- v0.9 exact birth-event tag;
- reward computation and schedule;
- one-edge-per-tick retrograde carrier.

The primary x-axis is **actually delivered credit mass**, because clipping, packet timing and structural divergence can make nominal gain differ from effective dose.

## Main falsification

A dose-only explanation predicts a reproducible non-monotone curve in final contrast versus delivered credit mass. In particular, if the v0.9 default sits near the apparent optimum, `1x` should beat both `0x` and `4x` across paired seeds.

The sweep also records a per-seed descriptive quadratic fit against actual delivered mass. The quadratic coefficient is secondary; paired extreme comparisons are primary.

## Run

```bat
python3.13 v09_1_credit_dose/selftest.py
python3.13 v09_1_credit_dose/sweep.py --seeds 16 --ticks 36 --drive-steps 40 --probe-steps 150 --out v091_dose16
```

Do not infer an inverted-U from a plotted mean alone. Compare paired seed effects and seed spread.
