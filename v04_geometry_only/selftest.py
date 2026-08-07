#!/usr/bin/env python3
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from v04_geometry_only.binary_arbor import BinaryConfig,BinaryGeometryArbor
from v04_geometry_only.task import GeometryDelayTask,route_delays
from v04_geometry_only.anatomy import metrics

print('Functional Arbor v0.4 geometry-only selftest')
c=BinaryConfig(size=31,seed=3)
m=BinaryGeometryArbor(c,'reward')
K=m.conductivity(False)
vals=np.unique(K)
print('  developmental K values',vals)
assert len(vals)<=2
m.mature=True; vals=np.unique(m.conductivity(True)); print('  mature K values',vals);assert len(vals)<=2
assert np.all((m.B==0)|(m.B==1))
# symmetric painted straight routes should have equal geometry and timing sign ~0
cy=int(round(m.cc)); ax=int(np.argmax(m.patches[0][cy])); bx=int(np.argmax(m.patches[1][cy]))
for x in range(min(ax,cy),max(ax,cy)+1):m.B[cy,x]=1
for x in range(min(bx,cy),max(bx,cy)+1):m.B[cy,x]=1
ma,mb=metrics(m,0),metrics(m,1)
print(f"  symmetric painted length A/B {ma['length']:.3f}/{mb['length']:.3f}")
assert abs(ma['length']-mb['length'])<1e-9
# force a geometric detour on A by deleting direct cells and drawing a U-ish route
m.B[:]=0;m.B[(m.rr<=c.root_radius)]=1
# B straight
for x in range(cy,bx+1):m.B[cy,x]=1
# A detour: from soma up, left, down to patch
ay=cy; ytop=cy-5
for y in range(ytop,cy+1):m.B[y,cy]=1
for x in range(ax,cy+1):m.B[ytop,x]=1
for y in range(ytop,ay+1):m.B[y,ax]=1
ma,mb=metrics(m,0),metrics(m,1)
print(f"  detour painted length A/B {ma['length']:.3f}/{mb['length']:.3f} dL {ma['length']-mb['length']:+.3f}")
assert ma['length']>mb['length']+5
# meter should see A later in a nearly insulating bath
m.mature=True;t=GeometryDelayTask(m,lag=10,trial_len=300);d=route_delays(t)
print('  painted detour wavefront A-B',d['diff'])
assert d['diff']['edge50']>0 and d['diff']['common25']>0
print('SELFTEST PASS')
