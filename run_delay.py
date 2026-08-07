#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json
from pathlib import Path
import numpy as np
from functional_arbor import Config, FunctionalArbor
from functional_arbor.delay_task import CoincidenceTask, RewardTrainer, route_delays


def exact_signflip_p(d):
    d=np.asarray(d,float); n=len(d)
    if n==0:return float('nan')
    obs=abs(float(d.mean()))
    if n<=16:
        vals=[]
        for bits in itertools.product((-1.0,1.0),repeat=n):
            vals.append(abs(float(np.mean(d*np.asarray(bits)))))
        return float(np.mean(np.asarray(vals)>=obs-1e-12))
    rng=np.random.default_rng(0)
    vals=[abs(float(np.mean(d*rng.choice([-1.0,1.0],size=n)))) for _ in range(20000)]
    return float(np.mean(np.asarray(vals)>=obs))


def build(seed,mode,args):
    cond={'reward':'credit','shuffle':'credit','local':'local','blind':'blind','open_loop':'open_loop','anti':'anti_credit'}[mode]
    c=Config(size=args.size,seed=seed,n_patches=2,patch_radius_frac=.28,patch_sigma=1.25,root_sigma=1.25,
             dt=.14,damping=.09,restoring=.04,source_amp=.95,carrier_omega=.20,
             train_cycles=max(1,args.epochs*args.pairs),material_budget_per_event=args.budget,
             dev_base_k=.20,dev_structure_k=1.20,dev_final_base_k=.12,dev_final_structure_k=2.2,
             mature_base_k=.10,mature_structure_k=2.6,substrate_noise=args.noise,
             eligibility_decay=.995,eligibility_gain=.85,credit_strength=args.credit_strength)
    m=FunctionalArbor(c,cond)
    task=CoincidenceTask(m,lag=args.lag,pulse=args.pulse,trial_len=args.trial_len)
    # The delay experiment runs in the transport regime throughout: structure is
    # allowed to alter the wave while it is being selected.
    m.mature=True
    pre=route_delays(task)
    RewardTrainer(task,mode=mode,seed=seed).train(args.pairs,args.epochs)
    post=route_delays(task)
    st=task.run(True); sd=task.run(False)
    contrast=(st-sd)/(st+sd+1e-12)
    return {'seed':seed,'mode':mode,'mass':float(m.M.sum()),'pre':pre,'post':post,
            'target':float(st),'distractor':float(sd),'contrast':float(contrast)}


def stats(v):
    a=np.asarray(v,float)
    return float(a.mean()),float(a.std(ddof=1) if len(a)>1 else 0.0)


def main():
    p=argparse.ArgumentParser(description='Wave-like Functional Arbor coincidence/delay experiment.')
    p.add_argument('--size',type=int,default=30)
    p.add_argument('--seeds',type=int,default=6)
    p.add_argument('--seed-start',type=int,default=0,dest='seed_start')
    p.add_argument('--lag',type=int,default=10)
    p.add_argument('--pulse',type=int,default=6)
    p.add_argument('--trial-len',type=int,default=240,dest='trial_len')
    p.add_argument('--pairs',type=int,default=10)
    p.add_argument('--epochs',type=int,default=2)
    p.add_argument('--budget',type=float,default=.45)
    p.add_argument('--noise',type=float,default=.12)
    p.add_argument('--credit-strength',type=float,default=5.0,dest='credit_strength')
    p.add_argument('--arms',default='reward,shuffle,local')
    p.add_argument('--out',default=None)
    a=p.parse_args(); arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    seeds=list(range(a.seed_start,a.seed_start+a.seeds))
    print(f'Functional Arbor wave-delay experiment  N={a.size} lag={a.lag} seeds={seeds}')
    allr={}
    for mode in arms:
        rows=[]
        for seed in seeds:
            r=build(seed,mode,a);rows.append(r)
            d=r['post']['diff']
            print(f" {mode:8s} s{seed}: mass {r['mass']:6.2f} contrast {r['contrast']:+.5f}  "
                  f"peak {d['peak']:+4d} e10 {d['edge10']:+4d} e25 {d['edge25']:+4d} "
                  f"e50 {d['edge50']:+4d} c10 {d['common10']:+4d} c25 {d['common25']:+4d}")
        allr[mode]=rows
    print('\nsummary')
    summary={}
    for mode,rows in allr.items():
        cm,cs=stats([r['contrast'] for r in rows])
        sm={'contrast_mean':cm,'contrast_sd':cs,'mass_mean':stats([r['mass'] for r in rows])[0]}
        print(f' {mode:8s} contrast {cm:+.5f} +- {cs:.5f}',end='')
        for k in ('peak','edge10','edge25','edge50','common10','common25'):
            m,s=stats([r['post']['diff'][k] for r in rows]);sm[k+'_mean']=m;sm[k+'_sd']=s
            print(f'  {k} {m:+.1f}',end='')
        print();summary[mode]=sm
    if 'reward' in allr and 'shuffle' in allr:
        rc=np.array([r['contrast'] for r in allr['reward']]);sc=np.array([r['contrast'] for r in allr['shuffle']]);dc=rc-sc
        de50=np.array([r['post']['diff']['edge50'] for r in allr['reward']],float)-np.array([r['post']['diff']['edge50'] for r in allr['shuffle']],float)
        print(f"\n paired reward-shuffle contrast {dc.mean():+.5f} +- {dc.std(ddof=1) if len(dc)>1 else 0:.5f}  "
              f"effect/seedSD {dc.mean()/(dc.std(ddof=1)+1e-12):+.2f}  exact signflip p={exact_signflip_p(dc):.5f}")
        print(f" paired edge50 shift {de50.mean():+.2f} frames  exact signflip p={exact_signflip_p(de50):.5f}")
        summary['paired_reward_shuffle']={'contrast_mean':float(dc.mean()),'contrast_sd':float(dc.std(ddof=1) if len(dc)>1 else 0),
                                          'contrast_effect_seed_sd':float(dc.mean()/(dc.std(ddof=1)+1e-12)),
                                          'contrast_signflip_p':exact_signflip_p(dc),
                                          'edge50_mean':float(de50.mean()),'edge50_signflip_p':exact_signflip_p(de50)}
    print('\nMechanism bar: peak timing alone does NOT count. A delay-line reading requires fractional-front and common-absolute-threshold estimators to move with the same sign; shuffle is the null.')
    if a.out:
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        serial={'args':vars(a),'summary':summary,'rows':{k:v for k,v in allr.items()}}
        (out/'delay_results.json').write_text(json.dumps(serial,indent=2),encoding='utf-8')

if __name__=='__main__': main()
