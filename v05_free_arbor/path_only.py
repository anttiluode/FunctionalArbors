#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v05_free_arbor.free_arbor import FreeBinaryArbor,FreeConfig
from v05_free_arbor.task import DelayTask


def signflip(d):
    d=np.asarray(d,float);obs=abs(float(d.mean()));n=len(d)
    vals=[abs(float(np.mean(d*np.asarray(s)))) for s in itertools.product((-1.,1.),repeat=n)] if n<=16 else []
    return float(np.mean(np.asarray(vals)>=obs-1e-12)) if vals else float('nan')


def rebuild(row,seed,lag):
    m=FreeBinaryArbor(FreeConfig(seed=seed,bootstrap_mass=90));m.body[:]=0
    for p in row['pathA']+row['pathB']:m.body[tuple(p)]=1
    m.mature=True
    return DelayTask(m,lag).delays(),m


def main():
    p=argparse.ArgumentParser();p.add_argument('results',nargs='+');p.add_argument('--lag',type=int,default=20);p.add_argument('--out',default='path_only.json');a=p.parse_args()
    rows=[]
    for f in a.results:rows.extend(json.load(open(f,encoding='utf-8'))['rows'])
    outrows=[]
    for z in rows:
        if not z.get('arms') or 'reward' not in z['arms'] or 'shuffle' not in z['arms']:continue
        rd,_=rebuild(z['arms']['reward'],z['seed'],a.lag);sd,_=rebuild(z['arms']['shuffle'],z['seed'],a.lag)
        outrows.append({'seed':z['seed'],'reward':rd,'shuffle':sd})
    summary={}
    for k in ('edge50','common25'):
        rv=np.asarray([x['reward'][k] for x in outrows],float);sv=np.asarray([x['shuffle'][k] for x in outrows],float);d=rv-sv
        summary[k]={'reward_mean':float(rv.mean()),'shuffle_mean':float(sv.mean()),'paired_mean':float(d.mean()),'paired_sd':float(d.std(ddof=1)),'p':signflip(d),'values':d.tolist()}
        print(k,summary[k])
    Path(a.out).write_text(json.dumps({'lag':a.lag,'summary':summary,'rows':outrows},indent=2),encoding='utf-8')
if __name__=='__main__':main()
