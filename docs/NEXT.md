# Next: force geometry to earn the delay

v0.3 answered the previous question: the learned delay is carried mainly by local material speed, while the extracted geometry pushes timing in the opposite direction.

The next model should therefore remove speed tuning as an available solution.

## Binary mature material

During development, continuous `M` may still be useful for smooth interface growth. At maturation, quantize it:

```text
M < threshold  -> K = K_bath
M >= threshold -> K = K_arbor
```

`K_arbor` is one fixed number everywhere. Thickness may affect robustness/branch competition but not local propagation speed unless explicitly tested in a separate arm.

## Primary task

Keep the same two-pulse coincidence task and exact-dose protocol.

Required result:

1. reward beats shuffled credit in frozen target-vs-distractor contrast;
2. independent wavefront delay moves toward requested lag;
3. anatomy path-length/tortuosity difference moves with the same sign;
4. geometry-only reconstruction preserves the learned delay;
5. straightened-route control destroys it.

## Stronger sweep

Use requested lags `4, 7, 10, 13` and ask whether learned path length grows monotonically with requested delay. Do not tune a separate geometry parameter for each lag.

## Kill condition

If performance remains possible but path length does not track lag, the system has found another wave-geometric trick (resonance, branching impedance, loops, interference). Measure that mechanism rather than calling it a delay cable.
