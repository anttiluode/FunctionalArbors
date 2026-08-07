# Next after v0.6

Do not optimize v0.6 until the full arm wins. The null against no-ephaptic learning is informative.

The next experiment should make the ephaptic hypothesis physically and developmentally sharper.

## 1. Replace the blurred field proxy

Use explicit membrane-current sources and a quasi-static extracellular solve, for example

`div(sigma_e grad V_e) = -I_m`

with absorbing/ground boundary conditions. Then `E_e = -grad V_e` is an actual field solution rather than repeated smoothing.

## 2. Unbundle the developmental episode

Keep persistent growth-cone tips. Each simulation event allows only one primitive:

- extend one cell;
- stabilize one cell;
- retract one weak terminal / connectivity-safe segment;
- branch one tip.

No routine should contain “reconnect and then prune.” Reconnection should simply happen when a growing tip reaches old arbor.

A slow chemistry-like trace can stabilize neutral exploratory growth long enough for later credit to act.

## 3. Test phase information cleanly

Construct stimuli with matched spatial field power and matched activity dose, but controlled coherence:

- coherent phase relation;
- reversed relation;
- phase-scrambled relation;
- magnitude-matched no-phase control.

Ask whether the structural statistics or learning sample efficiency follow phase after every other cue is matched.

## 4. Only then scale to multiple delay coordinates

If the phase-specific mechanism survives, give four sensory inputs four temporal requirements and ask whether one self-grown arbor creates a bank of physical delays.
