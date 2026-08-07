#!/usr/bin/env python3
import numpy as np
from functional_arbor import Config, FunctionalArbor
from functional_arbor.delay_task import CoincidenceTask
from functional_arbor.decompose import anatomy_path, route_metrics, symmetric_length_speed_decomposition, counterfactual_fields

print('Functional Arbor v0.3 mechanism selftest')
c=Config(size=30,seed=0,n_patches=2,patch_radius_frac=.28,patch_sigma=1.25,root_sigma=1.25,
         mature_base_k=.10,mature_structure_k=2.6,substrate_noise=0.0)
m=FunctionalArbor(c,'credit');m.mature=True
# Paint one bent A route and one straight B route into M. Geometry extractor must see A as longer.
cc=(c.size-1)/2
m.M*=0
# root blob
for y in range(c.size):
    for x in range(c.size):
        if (x-cc)**2+(y-cc)**2<5:m.M[y,x]=1
# connect patch maxima with deterministic polylines
for which,bend in [(0,6),(1,0)]:
    sy,sx=np.unravel_index(np.argmax(m.patches[which]),m.patches[which].shape); gy,gx=np.unravel_index(np.argmax(m.root),m.root.shape)
    pts=[]
    midy=int(round((sy+gy)/2 + (bend if which==0 else 0))); midx=int(round((sx+gx)/2))
    for (a,b) in [((sy,sx),(midy,midx)),((midy,midx),(gy,gx))]:
        n=max(abs(b[0]-a[0]),abs(b[1]-a[1]))+1
        for y,x in zip(np.linspace(a[0],b[0],n),np.linspace(a[1],b[1],n)):
            yy,xx=int(round(y)),int(round(x));m.M[max(0,yy-1):min(c.size,yy+2),max(0,xx-1):min(c.size,xx+2)]=1
ra=route_metrics(m,0,penalty=30);rb=route_metrics(m,1,penalty=30)
print(f"  painted path lengths A {ra['length']:.2f} B {rb['length']:.2f}")
assert ra['length']>rb['length']+1.0
D=symmetric_length_speed_decomposition(ra,rb)
print(f"  closure error {D['closure_error']:.3e}")
assert abs(D['closure_error'])<1e-8
fields=counterfactual_fields(m,ra,rb)
for k,v in fields.items():
    if isinstance(v,np.ndarray): assert np.isfinite(v).all() and v.min()>0
# conductivity override must be honored exactly
K=np.full_like(m.M,.777,np.float32);m.K_override=K
assert np.max(np.abs(m.conductivity()-K))<1e-7
m.K_override=None
print('SELFTEST PASS')
