#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from types import SimpleNamespace
from run_mechanism import build
from functional_arbor.decompose import route_metrics

root=Path('examples/v03')
root.mkdir(parents=True,exist_ok=True)
# Route picture: seed 0 reward.
args=SimpleNamespace(size=30,lag=10,pulse=6,trial_len=240,pairs=10,epochs=2,budget=.45,noise=.12,credit_strength=5.0)
m,t=build(0,'reward',args)
A=route_metrics(m,0,penalty=12);B=route_metrics(m,1,penalty=12)
fig,ax=plt.subplots(figsize=(6.2,5.4))
im=ax.imshow(m.M,origin='lower',interpolation='nearest')
pa=np.asarray([(x,y) for y,x in A['path']]);pb=np.asarray([(x,y) for y,x in B['path']])
ax.plot(pa[:,0],pa[:,1],'-o',ms=2,label=f"A anatomy L={A['length']:.2f}")
ax.plot(pb[:,0],pb[:,1],'-o',ms=2,label=f"B anatomy L={B['length']:.2f}")
ax.legend(loc='upper center',fontsize=8)
ax.set_title('Seed 0 reward arbor: anatomy-only routes')
ax.set_axis_off();fig.colorbar(im,ax=ax,fraction=.046,pad=.04,label='M')
fig.tight_layout();fig.savefig(root/'seed0_routes.png',dpi=180);plt.close(fig)

# Aggregate receipt from combined 8 seeds.
d=json.load(open('examples/mechanism8_combined.json'))
p=d['paired']
labels=['actual\nwavefront','geometry-only\nwavefront','speed-only\nwavefront']
means=[p['actual_edge50']['mean'],p['geometry_only_edge50']['mean'],p['speed_only_edge50']['mean']]
sds=[p['actual_edge50']['sd'],p['geometry_only_edge50']['sd'],p['speed_only_edge50']['sd']]
fig,ax=plt.subplots(figsize=(7.0,4.7))
xs=np.arange(len(labels));ax.bar(xs,means,yerr=sds,capsize=5)
ax.axhline(0,lw=1);ax.axhline(10,lw=1,ls='--',label='task-required +10 frames')
ax.set_xticks(xs,labels);ax.set_ylabel('reward − shuffle delay difference (frames)')
ax.set_title('Functional Arbor v0.3: what physically carries the learned delay?')
ax.legend();fig.tight_layout();fig.savefig(root/'mechanism_decomposition.png',dpi=180);plt.close(fig)
