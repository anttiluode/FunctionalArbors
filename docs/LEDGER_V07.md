# Functional Arbor v0.7 ledger — explicit extracellular field, persistent tips

## Question

Can the v0.6 ephaptic-development idea survive after replacing both remaining shortcuts: the blurred extracellular proxy and the atomic reconnect+prune developmental episode?

## Construction changes

- `I_tm` is an explicit current-source density from axial-current divergence plus terminal injection.
- `V_e` is solved with a grounded quasi-static discrete Poisson/Helmholtz solve.
- growth cones persist across developmental ticks;
- one tick extends at most one cell per selected tip;
- branching and natural reconnection occur during extension;
- chemistry stabilizes young material slowly;
- soma consequence updates structural support only at delayed evaluation times;
- retraction is separate and connectivity-safe;
- body mass returns to the same 70-cell budget;
- mature material remains binary/fixed-speed.

## Instrument kill tests

Self-test:

- fixed-speed K values only: pass;
- grounded nonzero `V_e` from a balanced current dipole: pass;
- coherent/reversed `|E|^2` equal on identical body: pass;
- coherent/reversed magnitude chemistry equal: pass;
- persistent one-cell extension: pass;
- separate retraction and mass restoration: pass.

## 16-seed / 24-tick receipt

Coherent vs phase scramble:

- contrast `+0.0014`, exact p `0.9847` -> null.

Coherent vs phase reverse:

- path `+1.25`, p `0.0352`;
- edge50 `+2.125`, p `0.5767`;
- contrast `+0.0949`, p `0.2806`.

Do not call this a phase arrow.

Coherent vs no-field:

- reconnection/extension `+0.0644`, p `0.0373`;
- final contrast `+0.1424`, p `0.0956`.

Coherent vs magnitude-only:

- reconnection rate effectively equal (`+0.001`, p `0.973`).

Thus the robust short-run extracellular benefit is magnitude/chemistry-aided structural search, not coherent phase.

Coherent vs no-credit:

- contrast `+0.0479`, p `0.4728` -> null.

The new slow trophic credit rule has not replaced the older structural hill-climber successfully yet.

## 8-seed / 36-tick check

Final mean contrast:

- coherent `+0.0957`
- phase scramble `+0.0955`
- phase reverse `-0.0673`
- magnitude only `-0.0300`
- no field `-0.0478`
- no credit `+0.0358`

Paired coherent:

- minus phase scramble: `+0.0002`, p `1.0`;
- minus phase reverse: `+0.1630`, p `0.0391`;
- minus magnitude only: `+0.1257`, p `0.0469`;
- minus no field: `+0.1435`, p `0.0078`;
- minus no credit: `+0.0599`, p `0.375`.

Interpretation: with longer development, directional field guidance can help final structure, and reversing it can hurt. But randomizing absolute phase does not hurt. Therefore the specific soma-phase lock is still not the useful variable.

## Geometry receipt

Short16 coherent: `corr(delta L, delta edge50)=0.682`, slope `8.02 frames/edge`.

Long8 coherent: `corr=0.949`, slope `12.31 frames/edge`.

Timing remains geometry-linked, but persistent loops/side branches make shortest path an incomplete descriptor.

## Wall sentence

> v0.7 turns the ephaptic idea into a real solved extracellular field and turns detours into persistent developmental histories. The field can improve structural exploration, and longer development suggests directional guidance can improve task performance, but correct soma-locked phase is still unnecessary and the new delayed trophic credit mechanism is not yet sufficient.
