"""Functional Arbor — the SOMA TAP TEST (v0.9.2 audit).

Motivated by GeometricNeuronV21's tap result: in the ECG loop, *which pixels the
readout touches* decided whether the system lived or died. Functional Arbor has
used one fixed readout for nine versions:

    y(t) = |psi(soma)|^2                       <- a one-pixel power voltmeter

This script changes ONLY that operator. No growth. No credit. No learning.
Identical frozen bodies, identical wave physics, identical A/B pulse protocol.

Readout families (all restricted to body cells):

    incoherent   y = sum_x w_x |psi(x)|^2        spatial average of power
    coherent     y = |sum_x w_x psi(x)|^2        an INTERFERENCE measurement

The coherent/incoherent split is the point. An incoherent patch is a smoothed
voltmeter. A coherent patch is a different measurement of the field -- it is the
old "soma as a spatial/interference surface" idea, stated as an operator.

Registered questions:
  Q1  Does the readout change contrast at the trained lag?
  Q2  Does it change the SHAPE of the objective C(lag) -- peak location/width?
  Q3  Coherent vs incoherent at a MATCHED tap set (the interference question).
  Q4  Geometry vs count: chosen taps vs random taps, matched count (the control).

Everything is paired on seed and reported with per-seed sign counts, because the
v0.9.1 dose sweep showed an aggregate curve can be real-looking and not
seed-stable.
"""
from __future__ import annotations
import sys, json, math, argparse, itertools
from collections import deque
import numpy as np

sys.path.insert(0, '.')
from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
from v06_ephaptic_growth.ephaptic_arbor import n4


# ---------------------------------------------------------------- readouts
def graph_dist(body, soma):
    b = np.asarray(body, bool)
    d = np.full(b.shape, -1, int)
    if not b[soma]:
        return d
    d[soma] = 0
    q = deque([soma])
    while q:
        p = q.popleft()
        for r in n4(*p, *b.shape):
            if b[r] and d[r] < 0:
                d[r] = d[p] + 1
                q.append(r)
    return d


def build_taps(m, rng):
    """Weight maps for every readout. All weights are L1-normalised over the body
    so that no readout wins simply by summing more mass."""
    n = m.cfg.size
    body = m.body.astype(bool)
    sy, sx = m.soma
    D = graph_dist(m.body, m.soma)

    def norm(w):
        w = w * body
        s = w.sum()
        return (w / s).astype(np.float64) if s > 0 else w.astype(np.float64)

    taps = {}

    w = np.zeros((n, n)); w[sy, sx] = 1.0
    taps['point'] = norm(w)

    w = np.zeros((n, n)); w[sy, sx] = 1.0
    for r in n4(sy, sx, n, n):
        w[r] = 1.0
    taps['cross'] = norm(w)

    w = np.zeros((n, n))
    w[max(sy - 1, 0):sy + 2, max(sx - 1, 0):sx + 2] = 1.0
    taps['patch3'] = norm(w)

    yy, xx = np.mgrid[0:n, 0:n]
    taps['gauss'] = norm(np.exp(-((yy - sy) ** 2 + (xx - sx) ** 2) / (2 * 2.5 ** 2)))

    # V21's actual variable: taps placed OUT along the body, not around the soma.
    # Ring of body cells at graph distance 4 from the soma.
    w = np.zeros((n, n)); w[(D == 4)] = 1.0
    taps['ring4'] = norm(w) if w.sum() > 0 else taps['point'].copy()

    # Matched-count random control for ring4: same number of body cells, random
    # locations. Separates "readout geometry matters" from "more taps = more signal".
    k = int((D == 4).sum())
    cand = np.argwhere(body & (D > 0))
    w = np.zeros((n, n))
    if k > 0 and len(cand) >= k:
        pick = cand[rng.choice(len(cand), size=k, replace=False)]
        for p in pick:
            w[tuple(p)] = 1.0
        taps['shuffle4'] = norm(w)
    else:
        taps['shuffle4'] = taps['ring4'].copy()

    # Whole body, one coherent sum -- the maximal-aperture readout.
    taps['whole'] = norm(body.astype(float))
    return taps


def apply_readouts(psi, taps):
    """Return {name: value} for every readout, coherent and incoherent."""
    out = {}
    p2 = np.abs(psi) ** 2
    for name, w in taps.items():
        out[f'{name}_incoh'] = float((w * p2).sum())
        out[f'{name}_coh'] = float(abs((w * psi).sum()) ** 2)
    return out


READOUT_NAMES = None  # filled at runtime


# ---------------------------------------------------------------- probing
def trace_all(m, taps, lag, target=True, steps=None):
    """One wave simulation; every readout evaluated at every step.

    Identical physics for all readouts by construction -- they are different
    measurements of the SAME field evolution, never different simulations.
    """
    steps = int(steps or m.cfg.probe_steps)
    m.reset_fast(True)
    first, second = (0, 1) if target else (1, 0)
    acc = None
    for t in range(steps):
        a = m.pulse_source(first, t, False)
        b = m.pulse_source(second, t - lag, False)
        if isinstance(a, float):
            src = b
        elif isinstance(b, float):
            src = a
        else:
            src = a + b
        m.advance(src, False, True, 'none')
        vals = apply_readouts(m.psi, taps)
        if acc is None:
            acc = {k: [] for k in vals}
        for k, v in vals.items():
            acc[k].append(v)
    return {k: np.asarray(v, float) for k, v in acc.items()}


def trace_single(m, taps, which, steps=None):
    steps = int(steps or m.cfg.probe_steps)
    m.reset_fast(True)
    acc = None
    for t in range(steps):
        m.advance(m.pulse_source(which, t, False), False, True, 'none')
        vals = apply_readouts(m.psi, taps)
        if acc is None:
            acc = {k: [] for k in vals}
        for k, v in vals.items():
            acc[k].append(v)
    return {k: np.asarray(v, float) for k, v in acc.items()}


def contrast_from(tg, ds):
    a, b = float(tg.max()), float(ds.max())
    return (a - b) / (a + b + 1e-12)


def first_fraction(x, frac):
    m = float(x.max())
    if m <= 0:
        return -1
    q = np.flatnonzero(x >= frac * m)
    return int(q[0]) if q.size else -1


# ---------------------------------------------------------------- stats
def sign_test_p(d):
    d = np.asarray(d, float)
    d = d[np.abs(d) > 1e-12]
    n = len(d)
    if n == 0:
        return 1.0, 0, 0
    pos = int((d > 0).sum())
    k = min(pos, n - pos)
    tail = sum(math.comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2 * tail / (2 ** n)), pos, n


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=12)
    ap.add_argument('--lag', type=int, default=20)
    ap.add_argument('--lags', type=str, default='0,4,8,12,16,20,24,28,32,40')
    ap.add_argument('--out', type=str, default='soma_tap_test.json')
    a = ap.parse_args()

    lags = [int(x) for x in a.lags.split(',')]
    rows = []
    for seed in range(a.seeds):
        cfg = V09Config(seed=seed)
        m = CausalEligibilityArbor(cfg)
        boot = m.bootstrap()
        if not boot.get('ok'):
            print(f'seed {seed} bootstrap FAILED'); continue
        m.mature = True
        rng = np.random.default_rng(seed + 424242)
        taps = build_taps(m, rng)

        # --- objective landscape C(lag) for every readout
        land = {}
        for lg in lags:
            tg = trace_all(m, taps, lg, True)
            ds = trace_all(m, taps, lg, False)
            for k in tg:
                land.setdefault(k, {})[lg] = contrast_from(tg[k], ds[k])

        # --- single-source delays for every readout
        A = trace_single(m, taps, 0)
        B = trace_single(m, taps, 1)
        delays = {k: first_fraction(A[k], .5) - first_fraction(B[k], .5) for k in A}
        peaks = {k: int(np.argmax(A[k])) - int(np.argmax(B[k])) for k in A}

        rows.append(dict(seed=seed, boot=boot,
                         tap_counts={k: int((v > 0).sum()) for k, v in taps.items()},
                         landscape={k: {str(l): float(v) for l, v in d.items()} for k, d in land.items()},
                         delay_edge50=delays, delay_peak=peaks))
        print(f'seed {seed:2d}  lenA {boot["length_A"]} lenB {boot["length_B"]}  '
              f'point C@{a.lag} {land["point_incoh"][a.lag]:+.4f}  '
              f'whole_coh C@{a.lag} {land["whole_coh"][a.lag]:+.4f}  '
              f'ring4_coh {land["ring4_coh"][a.lag]:+.4f}', flush=True)

    names = sorted(rows[0]['landscape'].keys())
    L = a.lag

    def col(name, lg=L):
        return np.array([r['landscape'][name][str(lg)] for r in rows])

    print('\n' + '=' * 92)
    print(f'SOMA TAP TEST — {len(rows)} frozen bodies, no growth, no credit, no learning')
    print('=' * 92)
    print(f'{"readout":16s} {"taps":>5s} {"|C|@lag20":>9s} {"argmax|C|":>11s} '
          f'{"edge50":>8s} {"d|C| vs pt":>12s} {"flips":>6s} {"corr":>7s} {"p":>8s}')
    print('-' * 100)
    base = col('point_incoh')
    summary = {}
    for nm in names:
        v = col(nm)
        am = [max(((abs(float(r['landscape'][nm][str(lg)])), lg) for lg in lags))[1] for r in rows]
        e50 = np.array([r['delay_edge50'][nm] for r in rows], float)
        d = np.abs(v) - np.abs(base)                      # selectivity MAGNITUDE
        pv, pos, n = sign_test_p(d)
        flips = int(((np.sign(v) * np.sign(base)) < 0).sum())
        rho = float(np.corrcoef(v, base)[0, 1]) if len(v) > 2 and v.std() > 0 else float('nan')
        summary[nm] = dict(absC_mean=float(np.abs(v).mean()), contrast_mean=float(v.mean()),
                           argmax_absC_lag_median=float(np.median(am)),
                           edge50_mean=float(e50.mean()),
                           dAbsC_vs_point=float(d.mean()), p=float(pv), pos=int(pos), n=int(n),
                           sign_flips_vs_point=flips, corr_with_point=rho,
                           taps=int(rows[0]['tap_counts'][nm.rsplit('_', 1)[0]]))
        st = summary[nm]
        print(f'{nm:16s} {st["taps"]:5d} {np.abs(v).mean():9.4f} {np.median(am):11.0f} '
              f'{e50.mean():+8.1f} {d.mean():+12.4f} {flips:6d} {rho:+7.3f} {pv:8.4f}')

    # ---- Q3 coherent vs incoherent at matched tap sets
    print('\nQ3  COHERENT vs INCOHERENT at matched tap set (the interference question)')
    print('-' * 92)
    q3 = {}
    for stem in ['cross', 'patch3', 'gauss', 'ring4', 'whole']:
        d = np.abs(col(f'{stem}_coh')) - np.abs(col(f'{stem}_incoh'))
        p, pos, n = sign_test_p(d)
        q3[stem] = dict(mean=float(d.mean()), p=float(p), pos=int(pos), n=int(n))
        print(f'  {stem:10s} coh-incoh  d|C| {d.mean():+.4f}   {pos}/{n} positive   p={p:.4f}')

    # ---- Q4 geometry vs count
    print('\nQ4  GEOMETRY vs COUNT: chosen ring taps vs random taps, matched count')
    print('-' * 92)
    q4 = {}
    for suf in ['coh', 'incoh']:
        d = np.abs(col(f'ring4_{suf}')) - np.abs(col(f'shuffle4_{suf}'))
        p, pos, n = sign_test_p(d)
        q4[suf] = dict(mean=float(d.mean()), p=float(p), pos=int(pos), n=int(n))
        print(f'  ring4-shuffle4 ({suf:5s})  d|C| {d.mean():+.4f}   {pos}/{n} positive   p={p:.4f}')

    # ---- Q2 shape: does the objective peak move?
    print('\nQ2  SHAPE of mean|C|(lag): does the objective landscape move, not just scale?')
    print('-' * 92)
    for nm in names:
        curve = [float(np.mean([abs(r['landscape'][nm][str(lg)]) for r in rows])) for lg in lags]
        print(f'  {nm:16s} ' + ' '.join(f'{c:+.3f}' for c in curve))
    print('  lags:            ' + ' '.join(f'{lg:6d}' for lg in lags))

    out = dict(seeds=len(rows), lag=L, lags=lags, summary=summary, q3=q3, q4=q4, rows=rows)
    with open(a.out, 'w') as f:
        json.dump(out, f)
    print(f'\nwrote {a.out}')


if __name__ == '__main__' and '--analyze' not in sys.argv:
    main()


def analyze(path):
    """Post-hoc: how well does each readout report the body's own path asymmetry?

    dL = length_A - length_B is a fixed property of the frozen body. A readout
    that is a good delay-difference detector should track it. This is the
    quantity the whole lineage is trying to grow, so it is the right thing to
    score a detector on.
    """
    d = json.load(open(path))
    rows = d['rows']; L = str(d['lag']); lags = d['lags']
    names = sorted(rows[0]['landscape'].keys())
    dL = np.array([r['boot']['length_A'] - r['boot']['length_B'] for r in rows], float)
    rng = np.random.default_rng(7)
    n = len(rows)

    def corr(v):
        return float(np.corrcoef(v, dL)[0, 1]) if v.std() > 0 else float('nan')

    base = np.array([r['landscape']['point_incoh'][L] for r in rows])
    r_base = corr(base)
    print(f'\n{"="*88}\nHOW WELL DOES EACH READOUT REPORT THE BODY\'S OWN PATH ASYMMETRY (dL)?')
    print(f'n = {n} frozen bodies.  point_incoh (the v0.9 readout) is the baseline.\n')
    print(f'{"readout":16s} {"corr(C,dL)":>11s} {"vs point":>9s} {"boot 95% CI of diff":>26s} {"P(better)":>10s}')
    print('-' * 88)
    res = {}
    for nm in names:
        v = np.array([r['landscape'][nm][L] for r in rows])
        rv = corr(v)
        diffs = []
        for _ in range(4000):
            i = rng.integers(0, n, n)
            if dL[i].std() == 0 or v[i].std() == 0 or base[i].std() == 0:
                continue
            diffs.append(abs(np.corrcoef(v[i], dL[i])[0, 1]) - abs(np.corrcoef(base[i], dL[i])[0, 1]))
        diffs = np.array(diffs)
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        pb = float((diffs > 0).mean())
        res[nm] = dict(corr=rv, diff=float(abs(rv) - abs(r_base)), ci=[float(lo), float(hi)], p_better=pb)
        print(f'{nm:16s} {rv:+11.3f} {abs(rv)-abs(r_base):+9.3f} '
              f'[{lo:+.3f}, {hi:+.3f}]'.rjust(26) + f'{pb:10.3f}')
    return res


if __name__ == '__main__' and '--analyze' in sys.argv:
    analyze(sys.argv[sys.argv.index('--analyze') + 1])
