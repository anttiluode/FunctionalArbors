import numpy as np
from functional_arbor import Config,FunctionalArbor
from functional_arbor.operators import div_k_grad
from functional_arbor.delay_task import CoincidenceTask,route_delays

print('Functional Arbor selftest')

# 1. Conservative face-flux operator.
k=np.random.default_rng(0).random((24,24))+0.1
u=np.ones((24,24),np.complex64)
e=np.max(np.abs(div_k_grad(k,u)))
print('  [1] conservative constant-field error',e)
assert e<1e-7

# 2. Fixed material budget: zero-mean credit can never accidentally mean zero body.
cfg=Config(size=40,seed=2,train_cycles=3,opportunity_iters=6,settle_frames=24,probe_cycles=1)
ms=[]
for cond in ('blind','local','credit','anti_credit'):
    m=FunctionalArbor(cfg,cond);m.train(False);ms.append(float(m.M.sum()))
    assert np.isfinite(m.M).all() and np.isfinite(m.psi).all()
print('  [2] matched masses', ['%.3f'%x for x in ms])
assert max(ms)-min(ms)<1e-3

# 3. Maturation: the grown body must carry more than the mature bath alone.
m=FunctionalArbor(cfg,'credit');m.train(False);st=m.clone_slow_state()
q=FunctionalArbor(cfg,'credit');q.load_slow_state(st);p=q.probe_sequence(False)
b=FunctionalArbor(cfg,'credit');b.substrate=st['substrate'].copy();pb=b.probe_sequence(False)
ratio=p['root_energy']/(pb['root_energy']+1e-20)
print('  [3] mature structure/bath ratio',ratio)
assert p['root_energy']>pb['root_energy']

# 4. Wave-delay meter positive control.  Localised sources + second-order wave +
# restoring spring must give a finite front, and a hand-painted fast A lane must
# move several *independent* front estimators in the same direction.
wc=Config(size=30,seed=0,n_patches=2,patch_radius_frac=.28,patch_sigma=1.20,root_sigma=1.20,
          dt=.14,damping=.09,restoring=.04,source_amp=.95,carrier_omega=.20,
          mature_base_k=.10,mature_structure_k=2.8,substrate_noise=0.0)
w=FunctionalArbor(wc,'credit');w.mature=True
t=CoincidenceTask(w,lag=10,pulse=6,trial_len=220)
d0=route_delays(t)
# Paint a narrow high-conductivity lane from patch A to the soma.
py,px=np.unravel_index(np.argmax(w.patches[0]),w.patches[0].shape)
for a in np.linspace(0,1,80):
    y=(1-a)*py+a*w.cc; x=(1-a)*px+a*w.cc
    mask=(w.x-x)**2+(w.y-y)**2<=1.8**2
    w.M[mask]=1.0
d1=route_delays(t)
print('  [4] symmetric common25 diff',d0['diff']['common25'],
      'painted fast-A common25 diff',d1['diff']['common25'],
      'edge25',d1['diff']['edge25'])
assert abs(d0['diff']['common25'])<=1
assert d1['diff']['common25'] < -5 and d1['diff']['edge25'] < -5

print('SELFTEST PASS')
