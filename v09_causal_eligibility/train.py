#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, math, os, sys, time
from pathlib import Path
import numpy as np

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
    from v07_persistent_ephaptic.task import DelayTask
else:
    from .eligibility_arbor import V09Config, CausalEligibilityArbor
    from ..v07_persistent_ephaptic.task import DelayTask

ARMS = (
    'activity',
    'event', 'event_shuffle',
    'competition', 'competition_shuffle',
    'timing', 'timing_shuffle',
    'no_credit',
)


def signflip(d):
    d = np.asarray(d, float); n = len(d); obs = abs(float(d.mean()))
    if not n: return float('nan')
    if n <= 16:
        vals = [abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.), repeat=n)]
    else:
        r = np.random.default_rng(0)
        vals = [abs(float(np.mean(d*r.choice([-1.,1.], n)))) for _ in range(50000)]
    return float(np.mean(np.asarray(vals) >= obs - 1e-12))


def launch_for_arm(m, arm, reward, since_tick, lag, measured_edge50):
    """Launch identical v0.8 retrograde packets with different eligibility semantics."""
    info = {'event_mass': 0.0, 'pos_mass': 0.0, 'neg_mass': 0.0, 'competition_events': 0, 'timing_error': 0.0}
    if arm == 'no_credit' or abs(reward) < 1e-12:
        return info

    if arm == 'activity':
        tag = m.activity_tag(); info['event_mass'] = float(tag.sum())
        # Exact v0.8 baseline: launch_credit snapshots current struct_elig.
        m.launch_credit(reward, 'retrograde')
        return info

    event = m.event_tag(since_tick); info['event_mass'] = float(event.sum())
    if arm == 'event':
        m.launch_tagged_retrograde(reward, event, 'event')
        return info
    if arm == 'event_shuffle':
        sh = m.shuffled_event_tag(event); info['event_mass'] = float(sh.sum())
        m.launch_tagged_retrograde(reward, sh, 'event_shuffle')
        return info

    if arm in ('competition', 'competition_shuffle'):
        new, old, n = m.competition_tags(since_tick); info['competition_events'] = int(n)
        if arm == 'competition_shuffle':
            new = m.shuffled_event_tag(new); old = m.shuffled_event_tag(old)
        info['pos_mass'] = float(new.sum()); info['neg_mass'] = float(old.sum())
        m.launch_tagged_retrograde(reward, new, arm + '_new', +1.0)
        m.launch_tagged_retrograde(reward, old, arm + '_old', -1.0)
        return info

    if arm in ('timing', 'timing_shuffle'):
        pos, neg, err = m.timing_tags(event, lag, measured_edge50); info['timing_error'] = float(err)
        if arm == 'timing_shuffle':
            pos = m.shuffled_event_tag(pos); neg = m.shuffled_event_tag(neg)
        info['pos_mass'] = float(pos.sum()); info['neg_mass'] = float(neg.sum())
        m.launch_tagged_retrograde(reward, pos, arm + '_helpful', +1.0)
        m.launch_tagged_retrograde(reward, neg, arm + '_harmful', -1.0)
        return info
    raise ValueError(arm)


def run_arm(base, arm, args, seed):
    m = base.copy(); m.prepare_development(); task = DelayTask(m, args.lag, args.probe_steps)
    pre_c, _, _ = task.contrast(); pre_d = task.delays(); pre_s = m.branch_stats()
    score = float(pre_c); last_eval_tick = 0; hist = []

    for tick in range(args.ticks):
        # Same pulse dose and same coherent extracellular guidance in every arm.
        m.drive_sequence(args.lag, 'coherent', args.drive_steps)
        events = m.structural_tick('coherent')
        raw = reward = 0.0; tag_info = {}
        if (tick + 1) % args.eval_interval == 0:
            new, _, _ = task.contrast(); now_delay = task.delays()
            raw = float(new - score); reward = math.tanh(args.reward_gain * raw)
            tag_info = launch_for_arm(m, arm, reward, last_eval_tick, args.lag, now_delay['edge50'])
            score = float(new); last_eval_tick = int(m.dev_tick)
        m.background_support_tick()
        # Carrier physics is frozen to v0.8 graph-retrograde for every credit arm.
        m.transport_credit_tick('retrograde')
        hist.append({
            'tick': tick, 'score': score, 'raw_delta': raw, 'reward': reward,
            'mass': m.mass(), 'events': events,
            'dL': m.path_length(0) - m.path_length(1), 'tag': tag_info,
        })

    m.settle_mass(); post_c, ta, ds = task.contrast(); post_d = task.delays(); stats = m.branch_stats()
    rec = m.state_receipt(); rec.update(m.credit_receipt()); rec.update(m.tag_receipt())
    return dict(
        arm=arm, seed=seed, pre_contrast=pre_c, contrast=post_c,
        target_peak=ta, distractor_peak=ds, pre_delay=pre_d, delay=post_d,
        pre_stats=pre_s, stats=stats, receipt=rec, history=hist,
    )


def metric(r, k):
    if k == 'length_diff': return r['stats']['length_A'] - r['stats']['length_B']
    if k == 'delta_length': return metric(r, 'length_diff') - (r['pre_stats']['length_A'] - r['pre_stats']['length_B'])
    if k == 'contrast': return r['contrast']
    if k == 'delta_contrast': return r['contrast'] - r['pre_contrast']
    if k == 'credit_mass': return r['receipt']['credit_mass']
    if k == 'credit_localization': return r['receipt']['mean_credit_localization']
    if k == 'tag_mass': return r['receipt']['tag_mass']
    if k == 'tag_launches': return r['receipt']['tag_launches']
    if k == 'competition_events': return r['receipt']['competition_events']
    return r['delay'][k]


def one_seed(seed, args, arms):
    cfg = V09Config(
        size=args.size, seed=seed, bootstrap_mass=args.bootstrap_mass, bootstrap_max=args.bootstrap_max,
        morph_disorder=args.disorder, probe_steps=args.probe_steps, development_ticks=args.ticks,
        eval_interval=args.eval_interval, developmental_drive_steps=args.drive_steps,
        developmental_lag=args.lag, cone_steer_beta=args.steer_beta, max_tips=args.max_tips,
        reward_gain=args.reward_gain,
    )
    base = CausalEligibilityArbor(cfg); boot = base.bootstrap()
    if not boot['ok']:
        return {'seed': seed, 'bootstrap': boot, 'arms': {}}
    return {'seed': seed, 'bootstrap': boot, 'arms': {a: run_arm(base, a, args, seed) for a in arms}}


def summarize(rows, arms):
    valid = [z for z in rows if z['arms']]
    keys = ('length_diff','delta_length','edge50','common25','contrast','delta_contrast',
            'credit_mass','credit_localization','tag_mass','tag_launches','competition_events')
    out = {}
    for a in arms:
        rr = [z['arms'][a] for z in valid]; out[a] = {}
        for k in keys:
            x = np.asarray([metric(r,k) for r in rr], float)
            out[a][k] = dict(mean=float(x.mean()), sd=float(x.std(ddof=1) if len(x)>1 else 0), values=x.tolist())

    pairs = [
        ('activity','no_credit'),
        ('event','event_shuffle'), ('event','no_credit'),
        ('competition','competition_shuffle'), ('competition','no_credit'),
        ('timing','timing_shuffle'), ('timing','no_credit'),
    ]
    for a,b in pairs:
        if a not in arms or b not in arms: continue
        A=[z['arms'][a] for z in valid]; B=[z['arms'][b] for z in valid]; q={}
        for k in ('length_diff','delta_length','edge50','common25','contrast','delta_contrast'):
            d=np.asarray([metric(x,k)-metric(y,k) for x,y in zip(A,B)],float)
            q[k]=dict(mean=float(d.mean()),sd=float(d.std(ddof=1) if len(d)>1 else 0),p=signflip(d),values=d.tolist())
        out[f'paired_{a}_minus_{b}']=q
    return out


def main():
    p=argparse.ArgumentParser(); p.add_argument('--seeds',type=int,default=8); p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--lag',type=int,default=20); p.add_argument('--size',type=int,default=31); p.add_argument('--ticks',type=int,default=36)
    p.add_argument('--eval-interval',type=int,default=3,dest='eval_interval'); p.add_argument('--drive-steps',type=int,default=48,dest='drive_steps'); p.add_argument('--probe-steps',type=int,default=170,dest='probe_steps')
    p.add_argument('--bootstrap-mass',type=int,default=70,dest='bootstrap_mass'); p.add_argument('--bootstrap-max',type=int,default=280,dest='bootstrap_max'); p.add_argument('--max-tips',type=int,default=6,dest='max_tips')
    p.add_argument('--steer-beta',type=float,default=1.85,dest='steer_beta'); p.add_argument('--disorder',type=float,default=.28); p.add_argument('--reward-gain',type=float,default=4.0,dest='reward_gain')
    p.add_argument('--arms',default=','.join(ARMS)); p.add_argument('--out',default='v09_out'); a=p.parse_args()
    arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    for x in arms:
        if x not in ARMS: raise ValueError(x)

    rows=[]; t0=time.time(); print(f'Functional Arbor v0.9 causal eligibility lag={a.lag} seeds={a.seeds} ticks={a.ticks}')
    for seed in range(a.seed_start,a.seed_start+a.seeds):
        z=one_seed(seed,a,arms); rows.append(z); print('seed',seed,'boot',z['bootstrap'].get('ok'),z['bootstrap'].get('mass'))
        for arm,r in z['arms'].items():
            dL=r['stats']['length_A']-r['stats']['length_B']; q=r['receipt']
            print(f"  {arm:20s} dL {dL:+4.0f} e50 {r['delay']['edge50']:+4d} C {r['contrast']:+.4f} tag {q['tag_mass']:.1f} credit {q['credit_mass']:.3f}")

    summary=summarize(rows,arms); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    payload={'args':vars(a),'summary':summary,'rows':rows}; (out/'v09_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('summary')
    for arm in arms:
        s=summary[arm]
        print(f" {arm:20s} dL {s['length_diff']['mean']:+.2f} e50 {s['edge50']['mean']:+.2f} C {s['contrast']['mean']:+.4f} tag {s['tag_mass']['mean']:.1f}")
    for key,q in summary.items():
        if not key.startswith('paired_'): continue
        print(f" {key:44s}: e50 {q['edge50']['mean']:+.2f} p={q['edge50']['p']:.4f} C {q['contrast']['mean']:+.4f} p={q['contrast']['p']:.4f}")
    print('elapsed',time.time()-t0,'wrote',out/'v09_results.json')

if __name__=='__main__': main()
