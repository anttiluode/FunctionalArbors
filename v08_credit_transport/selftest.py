#!/usr/bin/env python3
import os,sys,numpy as np
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v08_credit_transport.credit_arbor import V08Config,CreditTransportArbor

def main():
    c=V08Config(size=31,seed=2,bootstrap_mass=70,bootstrap_max=280,probe_steps=150,developmental_drive_steps=40)
    m=CreditTransportArbor(c);b=m.bootstrap();print('bootstrap',b);assert b['ok'] and m.mass()==70 and m.both_connected()
    fields=m.bond_fields(True);vals=np.sort(np.unique(np.concatenate([f.ravel() for f in fields])));print('K values',vals.tolist());assert vals.size==2 and np.allclose(vals,[c.k_mature_bath,c.k_arbor],rtol=1e-5,atol=1e-8)
    m.prepare_development();m.drive_sequence(c.developmental_lag,'coherent',40);print('field solves',m.field_solves,'power',np.mean(m.field_power));assert m.field_solves>0 and np.mean(m.field_power)>0
    # Retrograde latency law with equal synthetic eligibility.
    m.struct_elig[m.body>0]=1.0;m.support[m.body>0]=0.2;before=m.support.copy();dist=m.graph_distance_from_soma();arrival=np.full(dist.shape,-1,np.int16);m.launch_credit(.8,'retrograde')
    for t in range(int(dist.max())+2):
        m.transport_credit_tick('retrograde');new=(arrival<0)&(np.abs(m.support-before)>1e-6)&(m.body>0);arrival[new]=t+1
    ok=(m.body>0)&(dist>0)&(arrival>0);corr=float(np.corrcoef(dist[ok],arrival[ok])[0,1]);slope=float(np.polyfit(dist[ok],arrival[ok],1)[0]);print('retro latency corr',corr,'slope',slope);assert corr>0.999 and abs(slope-1)<1e-6
    # Persistent development still comes from v0.7, not a v0.8 structural macro-operation.
    mass0=m.mass();ev=m.structural_tick('coherent');print('events',ev,'mass',mass0,'->',m.mass());assert m.both_connected()
    m.settle_mass();assert m.mass()==m.material_target
    print('SELFTEST PASS')
if __name__=='__main__':main()
