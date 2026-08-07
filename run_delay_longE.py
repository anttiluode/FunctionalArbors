#!/usr/bin/env python3
from __future__ import annotations
import argparse, math, json
import numpy as np
from functional_arbor import Config, FunctionalArbor
from functional_arbor.delay_task import CoincidenceTask, RewardTrainer, route_delays


def build(seed,mode,args):
    cond={'reward':'credit','shuffle':'credit','local':'local','blind':'blind','open_loop':'open_loop','anti':'anti_credit'}[mode]
    c=Config(size=args.size,seed=seed,n_patches=2,patch_radius_frac=.30,patch_sigma=2.5,root_sigma=2.0,
             dt=.12,damping=.08,source_amp=.70,carrier_omega=.36,
             train_cycles=max(1,args.epochs*args.pairs*2//2),material_budget_per_event=args.budget,
             dev_base_k=.24,dev_structure_k=.95,dev_final_base_k=.025,dev_final_structure_k=2.0,
             mature_base_k=.008,mature_structure_k=2.8,substrate_noise=args.noise,
             eligibility_decay=.995,eligibility_gain=.75,credit_strength=args.credit_strength)
    m=FunctionalArbor(c,cond); task=CoincidenceTask(m,lag=args.lag,pulse=args.pulse,trial_len=args.trial_len)
    m.mature=True
    pre=route_delays(task)
    tr=RewardTrainer(task,mode=mode,seed=seed); tr.train(args.pairs,args.epochs)
    m.mature=True
    post=route_delays(task)
    st=task.run(True,record=False); sd=task.run(False,record=False)
    contrast=(st-sd)/(st+sd+1e-12)
    return {'seed':seed,'mode':mode,'mass':float(m.M.sum()),'pre':pre,'post':post,
            'target':st,'distractor':sd,'contrast':float(contrast)}


def stats(v):
    a=np.asarray(v,float); return float(a.mean()),float(a.std(ddof=1) if len(a)>1 else 0)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--size',type=int,default=40);p.add_argument('--seeds',type=int,default=3)
    p.add_argument('--lag',type=int,default=16);p.add_argument('--pulse',type=int,default=6)
    p.add_argument('--trial-len',type=int,default=190,dest='trial_len')
    p.add_argument('--pairs',type=int,default=12);p.add_argument('--epochs',type=int,default=2)
    p.add_argument('--budget',type=float,default=.34);p.add_argument('--noise',type=float,default=.12)
    p.add_argument('--credit-strength',type=float,default=3.2,dest='credit_strength')
    p.add_argument('--arms',default='reward,shuffle,local')
    a=p.parse_args(); arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    print(f'Functional Arbor wave-delay experiment  N={a.size} lag={a.lag} seeds={a.seeds}')
    allr={}
    for mode in arms:
        rows=[]
        for seed in range(a.seeds):
            r=build(seed,mode,a);rows.append(r)
            d=r['post']['diff']
            print(f" {mode:8s} s{seed}: mass {r['mass']:6.2f} contrast {r['contrast']:+.5f}  "
                  f"delay peak {d['peak']:+4d} e10 {d['edge10']:+4d} e25 {d['edge25']:+4d} e50 {d['edge50']:+4d} xc {d['xcorr']:+4d}")
        allr[mode]=rows
    print('\nsummary')
    for mode,rows in allr.items():
        cm,cs=stats([r['contrast'] for r in rows]); print(f' {mode:8s} contrast {cm:+.5f} +- {cs:.5f}',end='')
        for k in ('peak','edge10','edge25','edge50','xcorr'):
            m,s=stats([r['post']['diff'][k] for r in rows]); print(f'  {k} {m:+.1f}',end='')
        print()
    if 'reward' in allr and 'shuffle' in allr:
        paired=np.array([r['contrast'] for r in allr['reward']])-np.array([r['contrast'] for r in allr['shuffle']])
        print(f" paired reward-shuffle contrast {paired.mean():+.5f} +- {paired.std(ddof=1) if len(paired)>1 else 0:.5f}")
    print('\nMechanism bar: peak alone does NOT count. At least two of edge10/edge25/edge50/xcorr must move toward the requested lag with the same sign.')

if __name__=='__main__': main()
