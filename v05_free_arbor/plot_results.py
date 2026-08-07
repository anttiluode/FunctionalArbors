#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--results',default='examples/v05/free16_combined.json');p.add_argument('--outdir',default='examples/v05');a=p.parse_args()
d=json.load(open(a.results,encoding='utf-8'));rows=d['rows'];out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
# seed 0 morphology
z=next(x for x in rows if x['seed']==0)
fig,axs=plt.subplots(1,3,figsize=(12,4))
for ax,title,body,paths in [
 (axs[0],'field-grown body before credit',np.array(z['base_body']),None),
 (axs[1],'reward-remodeled body',np.array(z['arms']['reward']['body']),[z['arms']['reward']['pathA'],z['arms']['reward']['pathB']]),
 (axs[2],'shuffled-credit body',np.array(z['arms']['shuffle']['body']),[z['arms']['shuffle']['pathA'],z['arms']['shuffle']['pathB']])]:
    ax.imshow(body,origin='lower',cmap='gray_r',interpolation='nearest')
    if paths:
        for path in paths:
            q=np.asarray(path);ax.plot(q[:,1],q[:,0],linewidth=2)
    n=body.shape[0];cy=n//2
    ax.scatter([cy],[cy],marker='o',s=30);ax.scatter([4,n-5],[cy,cy],marker='x',s=45)
    ax.set_title(title);ax.set_xticks([]);ax.set_yticks([])
fig.suptitle('Functional Arbor v0.5 · seed 0 · binary fixed-speed tree')
fig.tight_layout();fig.savefig(out/'free_arbor_seed0.png',dpi=180);plt.close(fig)
# mechanism scatter
R=[x['arms']['reward'] for x in rows]
x=np.asarray([(r['stats']['length_A']-r['stats']['length_B'])-(r['pre_stats']['length_A']-r['pre_stats']['length_B']) for r in R],float)
y=np.asarray([r['delay']['edge50']-r['pre_delay']['edge50'] for r in R],float)
A=np.vstack([x,np.ones_like(x)]).T;m,b=np.linalg.lstsq(A,y,rcond=None)[0];xx=np.linspace(x.min()-1,x.max()+1,100)
fig,ax=plt.subplots(figsize=(6,5));ax.scatter(x,y,s=45);ax.plot(xx,m*xx+b)
for seed,(xx0,yy0) in enumerate(zip(x,y)):ax.annotate(str(rows[seed]['seed']),(xx0,yy0),xytext=(4,4),textcoords='offset points',fontsize=8)
ax.axhline(0,linewidth=.8);ax.axvline(0,linewidth=.8);ax.set_xlabel('change in A−B unique path length (lattice edges)');ax.set_ylabel('change in A−B edge50 wavefront delay (frames)')
ax.set_title(f'Geometry predicts timing: r={np.corrcoef(x,y)[0,1]:.3f}, slope={m:.2f} frames/edge')
fig.tight_layout();fig.savefig(out/'path_change_vs_delay_change.png',dpi=180);plt.close(fig)
print('wrote',out/'free_arbor_seed0.png',out/'path_change_vs_delay_change.png')
