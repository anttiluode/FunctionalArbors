# v0.3 mechanism ledger — geometry versus speed

## Registered question

v0.2 learned a physical A-minus-B wavefront delay near the requested +10 frames. v0.3 asks what changed physically.

Two candidate mechanisms:

1. **geometry** — reward changes route length/tortuosity;
2. **material speed** — reward changes local conductivity along the route.

The geometric-delay claim requires the learned geometry to move timing in the same sign as the task, not merely coexist with a delay produced by `K(M)`.

## Instrument repairs

### Even-grid source/soma bug

A first anatomy extractor used a single `argmax` pixel for each Gaussian input and soma mask. On an even grid the true centre is a half pixel, so tie-breaking gave one side a one-cell advantage.

Repair: source and soma are multi-cell threshold regions and the anatomy path is solved by multi-source / multi-goal Dijkstra. On a symmetric untrained body, both route lengths are exactly 6.0 pixels.

### Anatomy path is speed-blind

Path selection sees `M` only. It does not see conductivity `K` or quenched substrate disorder. This prevents the route extractor from baking the material-speed answer into the geometric measurement.

### Counterfactuals

- geometry-only keeps learned path shape with identical path conductivity;
- speed-only straightens each route while retaining its learned K profile;
- reconstructed-both uses extracted path plus learned K profile.

The isolated reconstructions are deliberately diagnostic rather than a complete substitute for the full network; distributed parallel paths are omitted. For that reason the exact path-level length/slowness decomposition is reported alongside the wave counterfactuals.

## Eight-seed receipt

Paired reward minus shuffled-credit:

| measure | mean | SD | exact sign-flip p | task sign |
|---|---:|---:|---:|---|
| actual edge50 delay | +10.375 frames | 5.397 | 0.0078125 | correct |
| actual common25 delay | +9.125 frames | 5.842 | 0.015625 | correct |
| anatomy length A-B | -1.864 px | 1.310 | 0.03125 | **wrong** |
| geometry-only edge50 | -11.000 frames | 7.856 | 0.03125 | **wrong** |
| speed-only edge50 | +15.500 frames | 10.198 | 0.0078125 | correct |
| path slowness difference | +3.281 | 2.116 | 0.015625 | correct |
| geometry component | -3.071 | 2.186 | 0.03125 | **wrong** |
| speed component | +6.353 | 3.990 | 0.015625 | correct |

## Verdict

**[V] Physical timing learned.** The full reward arm retains the requested positive wavefront delay relative to shuffled credit at eight paired seeds.

**[K] Geometric delay cable.** Killed in this version. Reward makes A anatomically shorter relative to B, and geometry-only counterfactuals move the wavefront in the wrong direction.

**[V] Material-speed mechanism.** The speed-only counterfactual and the independent path-slowness decomposition both move in the correct direction. Local conductivity differences are sufficient to explain the sign of the learned timing effect.

**[~] Exact distributed mechanism.** The isolated path-tube reconstruction does not reproduce the full network quantitatively. The real arbor has parallel routes and interference. The claim is therefore about the dominant geometry-vs-speed channel, not an assertion that one extracted path is the entire Green's function of the network.

## Consequence

`K(M)` was originally intended to let morphology reroute the field. It also gives the learner a much easier temporal degree of freedom: change speed without needing to grow a longer cable.

If geometric delay is the research target, graded `K(M)` has to be removed or sharply constrained in the next experiment.
