#!/usr/bin/env python3
import argparse,json,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v08_credit_transport.credit_arbor import V08Config,CreditTransportArbor

def one(carrier,seed,ticks):
    m=CreditTransportArbor(V08Config(seed=seed,bootstrap_mass=70));assert m.bootstrap()['ok'];m.prepare_development();m.struct_elig[m.body>0]=1;m.support[m.body>0]=.2
    base=m.support.copy();dist=m.graph_distance_from_soma();arrival=np.full(dist.shape,-1,np.int16);m.launch_credit(.8,carrier)
    for t in range(ticks):
        m.transport_credit_tick(carrier);new=(arrival<0)&(np.abs(m.support-base)>1e-6)&(m.body>0);arrival[new]=t+1
    ok=(m.body>0)&(arrival>0);corr=slope=float('nan')
    if ok.sum()>2 and np.std(arrival[ok])>0:corr=float(np.corrcoef(dist[ok],arrival[ok])[0,1]);slope=float(np.polyfit(dist[ok],arrival[ok],1)[0])
    return dict(delivered_cells=int(ok.sum()),corr_distance_latency=corr,slope_ticks_per_edge=slope,distance=dist[m.body>0].astype(int).tolist(),arrival=arrival[m.body>0].astype(int).tolist())

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=2);p.add_argument('--ticks',type=int,default=35);p.add_argument('--out',default='credit_instrument.json');a=p.parse_args()
    d={x:one(x,a.seed,a.ticks) for x in ('global','retrograde','scrambled_retrograde','trophic')};Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(d,indent=2))
    for k,v in d.items():print(k,v['delivered_cells'],v['corr_distance_latency'],v['slope_ticks_per_edge'])
if __name__=='__main__':main()
