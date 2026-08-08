# Functional Arbor v0.9 — causal eligibility

v0.8 showed that soma consequence can physically return to distant structure and can strongly alter survival when the **correct branch is deliberately tagged**. Yet free learning remained null.

v0.9 therefore freezes v0.8 retrograde transport and changes only the eligibility mark carried by reward.

## Arms

- `activity`: exact v0.8 baseline — recent structural/activity eligibility.
- `event`: exact cells physically added since the previous soma evaluation.
- `event_shuffle`: same tag count, moved to wrong cells while matching graph distance/youngness as closely as possible.
- `competition`: when a persistent tip naturally reconnects, tag the newly grown bypass positively and the pre-existing shortcut negatively.
- `competition_shuffle`: same positive/negative tag counts, wrong locations.
- `timing`: event cells are signed by current A-vs-B early/late transport error. Shared trunk is ignored.
- `timing_shuffle`: same positive/negative sparsity, wrong locations.
- `no_credit`: same growth/guidance/retraction with no returned soma consequence.

Every credit arm uses the same v0.8 graph-retrograde carrier: one arbor edge per slow tick. The wave, extracellular solve, fixed-speed binary cable, persistent growth cones, coherent ephaptic guidance, material budget and task are inherited unchanged.

The core question is now:

> **Can a local structural event leave a specific enough mark that a later soma consequence stabilizes the event that actually changed temporal computation?**

## Run

```bat
python3.13 v09_causal_eligibility/selftest.py
python3.13 v09_causal_eligibility/tag_instrument.py --out tag_instrument.json
python3.13 v09_causal_eligibility/train.py --seeds 8 --ticks 36 --arms activity,event,event_shuffle,competition,competition_shuffle,timing,timing_shuffle,no_credit --out v09_screen
```

The README will be updated from canonical GitHub Actions receipts after the first hostile screen. Do not infer a positive result from the architecture alone.
