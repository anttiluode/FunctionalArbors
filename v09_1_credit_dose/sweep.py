#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, math, os, sys, time
from pathlib import Path
import numpy as np

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from v09_causal_eligibility.eligibility_arbor import V09Config, CausalEligibilityArbor
from v07_persistent_ephaptic.task import DelayTask

DEFAULT_MULTIPLIERS = (0.0, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0)


def signflip(d):
    d = np.asarray(d, float); n = len(d); obs = abs(float(d.mean()))
    if not n: return float('nan')
    if n <= 16:
        vals = [abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.), repeat=n)]
    else:
        r = np.random.default_rng(0)
        vals = [abs(float(np.mean(d*r.choice([-1.,1.], n)))) for _ in range(50000)]
    return float(np.mean(np.asarray(vals) >= obs - 1e-12))


def label(mult):
    return ('g' + ('%.3f' % float(mult)).rstrip('0').rstrip('.')).replace('.', 'p')


def launch_exact_event(m, reward, since_tick):
    tag=m.event_tag(since_tick)
    m.launch_tagged_retrograde(reward, tag, 'event')
    return {'event_mass': float(tag.sum())}


def run_dose(base, mult, args, seed):
    # The only experimental variable is v0.8's retrograde support gain.
    m = base.copy()
    m.cfg.retrograde_credit_gain = float(args.base_retro_gain) * float(mult)
    m.prepare_development()
    task = DelayTask(m, args.lag, args.probe_steps)
    pre_c, _, _ = task.contrast(); pre_d = task.delays(); pre_s = m.branch_stats()
    score = float(pre_c); last_eval_tick = 0; hist = []

    for tick in range(args.ticks):
        m.drive_sequence(args.lag, 'coherent', args.drive_steps)
        events = m.structural_tick('coherent')
        raw = reward = 0.0; tag_info = {}
        if (tick + 1) % args.eval_interval == 0:
            new, _, _ = task.contrast(); raw = float(new - score)
            reward = math.tanh(args.reward_gain * raw)
            # Exact v0.9 event-cell semantics; only retrograde gain differs.
            tag_info = launch_exact_event(m, reward, last_eval_tick)
            score = float(new); last_eval_tick = int(m.dev_tick)
        m.background_support_tick()
        m.transport_credit_tick('retrograde')
        hist.append(dict(tick=tick, score=score, raw_delta=raw, reward=reward,
                         mass=m.mass(), events=events,
                         dL=m.path_length(0)-m.path_length(1), tag=tag_info))

    m.settle_mass(); post_c, ta, ds = task.contrast(); post_d = task.delays(); stats = m.branch_stats()
    rec = m.state_receipt(); rec.update(m.credit_receipt()); rec.update(m.tag_receipt())
    return dict(seed=seed, multiplier=float(mult), retrograde_gain=float(m.cfg.retrograde_credit_gain),
                pre_contrast=pre_c, contrast=post_c, target_peak=ta, distractor_peak=ds,
                pre_delay=pre_d, delay=post_d, pre_stats=pre_s, stats=stats,
                receipt=rec, history=hist)


def metric(r, k):
    if k == 'length_diff': return r['stats']['length_A'] - r['stats']['length_B']
    if k == 'delta_length': return metric(r,'length_diff') - (r['pre_stats']['length_A'] - r['pre_stats']['length_B'])
    if k == 'contrast': return r['contrast']
    if k == 'delta_contrast': return r['contrast'] - r['pre_contrast']
    if k == 'credit_mass': return r['receipt']['credit_mass']
    if k == 'tag_mass': return r['receipt']['tag_mass']
    return r['delay'][k]


def summarize(rows, mults):
    valid = [z for z in rows if z['doses']]
    out = {'dose': {}, 'paired_vs_zero': {}, 'quadratic': {}}
    keys = ('credit_mass','tag_mass','length_diff','delta_length','edge50','common25','contrast','delta_contrast')
    for mult in mults:
        lab = label(mult); rr = [z['doses'][lab] for z in valid]; out['dose'][lab] = {'multiplier': float(mult)}
        for k in keys:
            x = np.asarray([metric(r,k) for r in rr], float)
            out['dose'][lab][k] = dict(mean=float(x.mean()), sd=float(x.std(ddof=1) if len(x)>1 else 0), values=x.tolist())

    zero = label(0.0)
    if zero in out['dose']:
        Z = [z['doses'][zero] for z in valid]
        for mult in mults:
            lab = label(mult)
            if lab == zero: continue
            R = [z['doses'][lab] for z in valid]; q = {}
            for k in ('edge50','common25','contrast','delta_contrast','length_diff'):
                d = np.asarray([metric(r,k)-metric(z,k) for r,z in zip(R,Z)], float)
                q[k] = dict(mean=float(d.mean()), sd=float(d.std(ddof=1) if len(d)>1 else 0), p=signflip(d), values=d.tolist())
            out['paired_vs_zero'][lab] = q

    q2=[]; peaks=[]
    for z in valid:
        x=np.asarray([metric(z['doses'][label(m)],'credit_mass') for m in mults],float)
        y=np.asarray([metric(z['doses'][label(m)],'contrast') for m in mults],float)
        if len(np.unique(np.round(x,9))) >= 3:
            c=np.polyfit(x,y,2); q2.append(float(c[0]))
            peaks.append(float(-c[1]/(2*c[0])) if c[0] < -1e-12 else float('nan'))
    out['quadratic'] = dict(q2_values=q2, q2_mean=float(np.mean(q2)) if q2 else float('nan'),
                            q2_p=signflip(q2) if q2 else float('nan'), peak_credit_values=peaks)

    for a,b,name in ((1.0,0.0,'one_vs_zero'),(1.0,4.0,'one_vs_four'),(4.0,0.0,'four_vs_zero')):
        la,lb=label(a),label(b)
        if la in out['dose'] and lb in out['dose']:
            A=[z['doses'][la] for z in valid]; B=[z['doses'][lb] for z in valid]; q={}
            for k in ('contrast','edge50','length_diff'):
                d=np.asarray([metric(x,k)-metric(y,k) for x,y in zip(A,B)],float)
                q[k]=dict(mean=float(d.mean()),sd=float(d.std(ddof=1) if len(d)>1 else 0),p=signflip(d),values=d.tolist())
            out[name]=q
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',type=int,default=16); p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--multipliers',default=','.join(str(x) for x in DEFAULT_MULTIPLIERS))
    p.add_argument('--base-retro-gain',type=float,default=0.48,dest='base_retro_gain')
    p.add_argument('--lag',type=int,default=20); p.add_argument('--size',type=int,default=31); p.add_argument('--ticks',type=int,default=36)
    p.add_argument('--eval-interval',type=int,default=3,dest='eval_interval'); p.add_argument('--drive-steps',type=int,default=40,dest='drive_steps'); p.add_argument('--probe-steps',type=int,default=150,dest='probe_steps')
    p.add_argument('--bootstrap-mass',type=int,default=70,dest='bootstrap_mass'); p.add_argument('--bootstrap-max',type=int,default=280,dest='bootstrap_max'); p.add_argument('--max-tips',type=int,default=6,dest='max_tips')
    p.add_argument('--steer-beta',type=float,default=1.85,dest='steer_beta'); p.add_argument('--disorder',type=float,default=.28); p.add_argument('--reward-gain',type=float,default=4.0,dest='reward_gain')
    p.add_argument('--out',default='v091_out'); a=p.parse_args()
    mults=[float(x.strip()) for x in a.multipliers.split(',') if x.strip()]

    rows=[]; t0=time.time(); print('Functional Arbor v0.9.1 credit-dose autopsy', 'multipliers', mults)
    for seed in range(a.seed_start,a.seed_start+a.seeds):
        cfg=V09Config(size=a.size,seed=seed,bootstrap_mass=a.bootstrap_mass,bootstrap_max=a.bootstrap_max,
                      morph_disorder=a.disorder,probe_steps=a.probe_steps,development_ticks=a.ticks,
                      eval_interval=a.eval_interval,developmental_drive_steps=a.drive_steps,developmental_lag=a.lag,
                      cone_steer_beta=a.steer_beta,max_tips=a.max_tips,reward_gain=a.reward_gain,
                      retrograde_credit_gain=a.base_retro_gain)
        base=CausalEligibilityArbor(cfg); boot=base.bootstrap()
        if not boot['ok']:
            rows.append({'seed':seed,'bootstrap':boot,'doses':{}}); continue
        doses={}
        print('seed',seed,'boot mass',boot.get('mass'))
        for mult in mults:
            r=run_dose(base,mult,a,seed); doses[label(mult)]=r
            print(f"  {mult:5.3g}x gain {r['retrograde_gain']:.4f} credit {r['receipt']['credit_mass']:.3f} dL {metric(r,'length_diff'):+.0f} e50 {metric(r,'edge50'):+.0f} C {r['contrast']:+.4f}")
        rows.append({'seed':seed,'bootstrap':boot,'doses':doses})

    summary=summarize(rows,mults); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    payload={'args':vars(a),'multipliers':mults,'summary':summary,'rows':rows}
    (out/'credit_dose_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('\nMEANS BY DELIVERED DOSE')
    for mult in mults:
        s=summary['dose'][label(mult)]
        print(f" {mult:5.3g}x delivered {s['credit_mass']['mean']:.3f} C {s['contrast']['mean']:+.4f} e50 {s['edge50']['mean']:+.2f} dL {s['length_diff']['mean']:+.2f}")
    for name in ('one_vs_zero','one_vs_four','four_vs_zero'):
        if name in summary:
            q=summary[name]
            print(f" {name}: C {q['contrast']['mean']:+.4f} p={q['contrast']['p']:.5f}; e50 {q['edge50']['mean']:+.2f} p={q['edge50']['p']:.5f}")
    q=summary['quadratic']; print(' quadratic q2 mean',q['q2_mean'],'p',q['q2_p'])
    print('elapsed',time.time()-t0,'wrote',out/'credit_dose_results.json')

if __name__=='__main__': main()
