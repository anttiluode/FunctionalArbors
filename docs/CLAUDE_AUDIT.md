# What the Claude build taught this build

The parallel `Claude/` implementation was useful because it chose a task whose proposed solution is a physical transport geometry rather than a prettier morphology.

## Keep

1. **A task with a geometric answer.** Two pulses separated by `dt_lag` make a sharp hypothesis: if the arbor solves the task as a delay line, an independently measured route-delay difference must change with the required lag.
2. **Paint the answer in by hand before training.** Claude's selftest first imposed a fast lane and checked that its meters could see it. ChatGPT v0.2 keeps that order.
3. **Exact dose, exact centre, stability guard.** These are now permanent protocol requirements.
4. **A zero-mean teaching signal needs baseline development.** Claude discovered that `delta` alone could average to zero and grow no body. This build solves the same problem differently: every event receives a fixed material budget, so credit can only redistribute anatomy.
5. **The second meter gets veto power.** Claude's peak delay tracked `dt_lag`, but its leading edge moved with the wrong sign. That correctly killed its initial conduction-delay explanation.

## Do not inherit unchanged

Claude's current medium is first-order in the complex field, `dpsi/dt=(D+iC)Lpsi-...`, and its own audit shows an extremely broad diffusive impulse response. Peak timing is therefore an envelope statistic, not a clean propagation time.

Its reward rule also changes total body mass. In the pasted three-seed run the reward arm ended around 505--551 material units while shuffle was about 1027--1076 and Hebbian about 962--970. That does not erase the selectivity result, but it means reward-vs-control is not a matched-anatomy comparison.

Finally, the sentence "a passive medium has exactly one way to tell the orders apart" turned out too strong. A dispersive reciprocal medium can reshape envelopes, phase and resonance without implementing a clean group delay. The task is still good; the mechanism must be measured independently.

## ChatGPT v0.2 response

- second-order damped wave state (`psi`, `vel`) rather than a diffusive complex heat equation;
- an on-site restoring spring so an impulse has a finite response instead of leaving a static displacement mode;
- spatially localised input and soma masks so source tails do not fake early arrival;
- fixed material budget per growth event;
- independent delay meters: each route's 10/25/50% front plus **common absolute thresholds** shared by both routes;
- peak timing is printed but is explicitly barred from establishing the delay mechanism by itself.

The point of the dual build is not to pick a winner. Claude supplied the task and the autopsy that told this implementation what instrument it had to build.
