#!/usr/bin/env python3
import argparse,itertools,json,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v08_credit_transport.credit_arbor import V08Config,CreditTransportArbor,n4

def signflip(d):
    d=np.asarray(d,float);obs=abs(float(d.mean()));n=len(d)
    if n<=16:
        vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)]
    else:
        r=np.random.default_rng(808);vals=[abs(float(np.mean(d*r.choice([-1.,1.],n)))) for _ in range(50000)]
    return float(np.mean(np.asarray(vals)>=obs-1e-12))

def side_branch(m):
    main=set(m.path(0) or [])|set(m.path(1) or []);d=m.degree4();leaves=[(int(y),int(x)) for y,x in np.argwhere((m.body>0)&(d==1)&(~m.protect)) if (int(y),int(x)) not in main]
    if not leaves:return []
    p=leaves[0];out=[p];prev=None
    for _ in range(4):
        opts=[q for q in n4(*p,*m.body.shape) if m.body[q] and q!=prev]
        if not opts:break
        q=opts[0]
        if d[q]>=3 or q in main:break
        out.append(q);prev,p=p,q
    return out

def trial(base,tag,reward,seed,nremove=4):
    m=base.copy();m.prepare_development();m.rng=np.random.default_rng(seed);m.support[m.body>0]=.45;m.struct_elig.fill(0);m.age[m.body>0]=99
    for p in tag:m.struct_elig[p]=1
    m.launch_credit(reward,'retrograde')
    for _ in range(int(m.graph_distance_from_soma().max())+2):m.transport_credit_tick('retrograde')
    sup=float(np.mean([m.support[p] for p in tag]))
    for _ in range(nremove):m.retract_one()
    return sum(bool(m.body[p]) for p in tag)/len(tag),sup

def main():
    p=argparse.ArgumentParser();p.add_argument('--trials',type=int,default=64);p.add_argument('--seed',type=int,default=3);p.add_argument('--out',default='eligibility_control.json');a=p.parse_args();base=CreditTransportArbor(V08Config(seed=a.seed,bootstrap_mass=70));assert base.bootstrap()['ok'];tag=side_branch(base);assert tag
    out={'tag':tag,'trials':a.trials,'arms':{},'paired':{}};raw={}
    for name,r in [('positive',.9),('zero',0.),('negative',-.9)]:
        z=[trial(base,tag,r,a.seed*10000+k) for k in range(a.trials)];v=np.asarray([q[0] for q in z]);raw[name]=v;out['arms'][name]={'mean_survival':float(v.mean()),'sd_survival':float(v.std(ddof=1)),'mean_support':float(np.mean([q[1] for q in z])),'survival':v.tolist()}
    for aa,bb in [('positive','zero'),('positive','negative'),('zero','negative')]:
        d=raw[aa]-raw[bb];out['paired'][f'{aa}_minus_{bb}']={'mean':float(d.mean()),'sd':float(d.std(ddof=1)),'p':signflip(d),'values':d.tolist()}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='arms'}|{'arms':{k:{kk:vv for kk,vv in v.items() if kk!='survival'} for k,v in out['arms'].items()}},indent=2))
if __name__=='__main__':main()
