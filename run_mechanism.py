#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, itertools
from pathlib import Path
import numpy as np
from functional_arbor import Config, FunctionalArbor
from functional_arbor.delay_task import CoincidenceTask, RewardTrainer, route_delays
from functional_arbor.decompose import route_metrics, symmetric_length_speed_decomposition, counterfactual_fields


def exact_signflip_p(d):
    d=np.asarray(d,float); n=len(d)
    if not n:return float('nan')
    obs=abs(float(d.mean()))
    vals=[]
    if n<=16:
        for bits in itertools.product((-1.,1.),repeat=n): vals.append(abs(float(np.mean(d*np.asarray(bits)))))
    else:
        rng=np.random.default_rng(0)
        for _ in range(20000): vals.append(abs(float(np.mean(d*rng.choice([-1.,1.],size=n)))))
    return float(np.mean(np.asarray(vals)>=obs-1e-12))


def config_for(seed,args,condition='credit'):
    return Config(size=args.size,seed=seed,n_patches=2,patch_radius_frac=.28,patch_sigma=1.25,root_sigma=1.25,
             dt=.14,damping=.09,restoring=.04,source_amp=.95,carrier_omega=.20,
             train_cycles=max(1,args.epochs*args.pairs),material_budget_per_event=args.budget,
             dev_base_k=.20,dev_structure_k=1.20,dev_final_base_k=.12,dev_final_structure_k=2.2,
             mature_base_k=.10,mature_structure_k=2.6,substrate_noise=args.noise,
             eligibility_decay=.995,eligibility_gain=.85,credit_strength=args.credit_strength)


def build(seed,mode,args):
    cond='credit' if mode in ('reward','shuffle') else mode
    c=config_for(seed,args,cond)
    m=FunctionalArbor(c,cond);m.mature=True
    task=CoincidenceTask(m,lag=args.lag,pulse=args.pulse,trial_len=args.trial_len)
    RewardTrainer(task,mode=mode,seed=seed).train(args.pairs,args.epochs)
    return m,task


def measure_override(task, which, K):
    m=task.model; old=m.K_override
    m.K_override=np.asarray(K,np.float32)
    try:
        tr=task.single_trace(which)
        # Import locally to keep the receipt explicit.
        from functional_arbor.delay_task import first_fraction, _first_absolute
        weak=float(tr.max())
        return {'peak':int(np.argmax(tr)),'edge25':first_fraction(tr,.25),'edge50':first_fraction(tr,.50),
                'trace_peak':weak,'trace':tr}
    finally:
        m.K_override=old


def counterfactual_diff(task, fields, prefix):
    A=measure_override(task,0,fields[f'{prefix}_A'])
    B=measure_override(task,1,fields[f'{prefix}_B'])
    # Independent routes have separate amplitudes, so fractional fronts are the
    # primary counterfactual meter; common absolute thresholds are ill-defined
    # across two separately reconstructed media.
    return {'edge25':A['edge25']-B['edge25'],'edge50':A['edge50']-B['edge50'],'peak':A['peak']-B['peak'],
            'A_peak':A['trace_peak'],'B_peak':B['trace_peak']}


def one(seed,mode,args):
    m,task=build(seed,mode,args)
    actual=route_delays(task)
    ra=route_metrics(m,0,penalty=args.path_penalty); rb=route_metrics(m,1,penalty=args.path_penalty)
    dec=symmetric_length_speed_decomposition(ra,rb)
    fields=counterfactual_fields(m,ra,rb,tube_radius=args.tube_radius)
    geom=counterfactual_diff(task,fields,'geometry')
    speed=counterfactual_diff(task,fields,'speed')
    both=counterfactual_diff(task,fields,'both')
    return {'seed':seed,'mode':mode,'mass':float(m.M.sum()),'actual':actual,
            'A':{k:v for k,v in ra.items() if k!='path'},'B':{k:v for k,v in rb.items() if k!='path'},
            'decomposition':dec,'geometry_only':geom,'speed_only':speed,'reconstructed_both':both,
            'paths':{'A':ra['path'],'B':rb['path']}}


def ms(v):
    a=np.asarray(v,float);return float(a.mean()),float(a.std(ddof=1) if len(a)>1 else 0.)


def main():
    p=argparse.ArgumentParser(description='Functional Arbor v0.3: geometry-vs-speed mechanism decomposition.')
    p.add_argument('--size',type=int,default=30);p.add_argument('--seeds',type=int,default=6)
    p.add_argument('--seed-start',type=int,default=0,dest='seed_start');p.add_argument('--lag',type=int,default=10)
    p.add_argument('--pulse',type=int,default=6);p.add_argument('--trial-len',type=int,default=240,dest='trial_len')
    p.add_argument('--pairs',type=int,default=10);p.add_argument('--epochs',type=int,default=2)
    p.add_argument('--budget',type=float,default=.45);p.add_argument('--noise',type=float,default=.12)
    p.add_argument('--credit-strength',type=float,default=5.0,dest='credit_strength')
    p.add_argument('--path-penalty',type=float,default=12.0,dest='path_penalty')
    p.add_argument('--tube-radius',type=float,default=1.25,dest='tube_radius')
    p.add_argument('--arms',default='reward,shuffle');p.add_argument('--out',default='mechanism_out')
    a=p.parse_args(); arms=[x.strip() for x in a.arms.split(',') if x.strip()]
    seeds=range(a.seed_start,a.seed_start+a.seeds); allr={}
    print(f'Functional Arbor v0.3 mechanism assay  lag={a.lag} N={a.size} seeds={list(seeds)}')
    for mode in arms:
        rows=[]
        for seed in seeds:
            r=one(seed,mode,a);rows.append(r)
            A,B=r['A'],r['B'];d=r['decomposition'];act=r['actual']['diff']
            print(f" {mode:7s} s{seed}: actual e50 {act['edge50']:+4d} c25 {act['common25']:+4d} | "
                  f"L A/B {A['length']:.1f}/{B['length']:.1f} dL {A['length']-B['length']:+.1f} | "
                  f"geom {r['geometry_only']['edge50']:+4d} speed {r['speed_only']['edge50']:+4d} both {r['reconstructed_both']['edge50']:+4d}")
        allr[mode]=rows
    print('\nsummary')
    summary={}
    for mode,rows in allr.items():
        x={}
        for key,vals in {
            'actual_edge50':[r['actual']['diff']['edge50'] for r in rows],
            'actual_common25':[r['actual']['diff']['common25'] for r in rows],
            'length_diff':[r['A']['length']-r['B']['length'] for r in rows],
            'tortuosity_diff':[r['A']['tortuosity']-r['B']['tortuosity'] for r in rows],
            'slowness_diff':[r['decomposition']['predicted_slowness_diff'] for r in rows],
            'geometry_component':[r['decomposition']['geometry_component'] for r in rows],
            'speed_component':[r['decomposition']['speed_component'] for r in rows],
            'geometry_only_edge50':[r['geometry_only']['edge50'] for r in rows],
            'speed_only_edge50':[r['speed_only']['edge50'] for r in rows],
            'both_edge50':[r['reconstructed_both']['edge50'] for r in rows],
        }.items():
            x[key+'_mean'],x[key+'_sd']=ms(vals)
        summary[mode]=x
        print(f" {mode:7s}: actual e50 {x['actual_edge50_mean']:+.2f} | dL {x['length_diff_mean']:+.2f} | "
              f"geom-only {x['geometry_only_edge50_mean']:+.2f} | speed-only {x['speed_only_edge50_mean']:+.2f} | both {x['both_edge50_mean']:+.2f}")
    if 'reward' in allr and 'shuffle' in allr:
        pair={}
        for key,fun in {
            'actual_edge50':lambda r:r['actual']['diff']['edge50'],
            'length_diff':lambda r:r['A']['length']-r['B']['length'],
            'geometry_only_edge50':lambda r:r['geometry_only']['edge50'],
            'speed_only_edge50':lambda r:r['speed_only']['edge50'],
            'slowness_diff':lambda r:r['decomposition']['predicted_slowness_diff'],
        }.items():
            d=np.asarray([fun(r) for r in allr['reward']],float)-np.asarray([fun(r) for r in allr['shuffle']],float)
            pair[key]={'mean':float(d.mean()),'sd':float(d.std(ddof=1) if len(d)>1 else 0.),'signflip_p':exact_signflip_p(d)}
        summary['paired_reward_shuffle']=pair
        print('\npaired reward-shuffle')
        for k,v in pair.items(): print(f" {k:22s} {v['mean']:+.3f} +- {v['sd']:.3f}  p={v['signflip_p']:.5f}")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    serial={'args':vars(a),'summary':summary,'rows':allr}
    (out/'mechanism_results.json').write_text(json.dumps(serial,indent=2),encoding='utf-8')
    print('\nInterpretation rule: geometry earns the delay-cable claim only if learned length/tortuosity and geometry-only wavefront delay move with the required sign beyond shuffle. If speed-only carries the effect while geometry-only does not, the body learned material speed, not a geometric delay line.')

if __name__=='__main__':main()
