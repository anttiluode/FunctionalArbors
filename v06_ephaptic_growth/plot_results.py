#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('receipt');ap.add_argument('--seed0');ap.add_argument('--out',default='v06_plots');a=ap.parse_args()
    d=load(a.receipt);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    arms=['full','no_ephaptic','magnitude_only','phase_shuffle']
    aa=d.get('arms',d.get('arm_means'))
    means=[aa[x]['yield']['mean'] for x in arms];sds=[aa[x]['yield']['sd'] for x in arms]
    fig,ax=plt.subplots(figsize=(8,4.5));ax.bar(range(len(arms)),means,yerr=sds,capsize=4);ax.set_xticks(range(len(arms)),[x.replace('_','\n') for x in arms]);ax.set_ylabel('legal reconnecting proposals / attempts');ax.set_ylim(0,1.05);ax.set_title('v0.6: field guidance changes exploration yield');fig.tight_layout();fig.savefig(out/'proposal_yield.png',dpi=170);plt.close(fig)
    q=d['geometry_timing_full'];x=np.asarray(q['delta_length']);y=np.asarray(q['delta_edge50']);
    fig,ax=plt.subplots(figsize=(6,5));ax.scatter(x,y);xx=np.linspace(x.min()-1,x.max()+1,100);ax.plot(xx,q['slope_frames_per_edge']*xx+q['intercept']);ax.axhline(0,lw=.8);ax.axvline(0,lw=.8);ax.set_xlabel('change in A-B unique path length (edges)');ax.set_ylabel('change in A-B edge50 delay (frames)');ax.set_title(f"full arm: geometry vs timing, r={q['corr']:.3f}");fig.tight_layout();fig.savefig(out/'geometry_vs_timing.png',dpi=170);plt.close(fig)
    if a.seed0:
        z=load(a.seed0);pan=[('bootstrap',np.asarray(z['base']['base_body']) if 'base_body' in z['base'] else np.asarray(z['base_body']) if 'base_body' in z else None)]
        # input seed0 file format from generator: base contains bootstrap/base_body
        base=np.asarray(z['base']['base_body']) if isinstance(z.get('base'),dict) and 'base_body' in z['base'] else np.asarray(z['base']['bootstrap']) if False else np.asarray(z['base_body']) if 'base_body' in z else None
        if base is None and isinstance(z.get('base'),dict):base=np.asarray(z['base'].get('body',[]))
        if base is not None and base.size:
            items=[('field-grown start',base,None),('full ephaptic + credit',np.asarray(z['full']['body']),z['full']),('no ephaptic + credit',np.asarray(z['no_ephaptic']['body']),z['no_ephaptic'])]
            fig,axs=plt.subplots(1,3,figsize=(12,4))
            for ax,(title,b,r) in zip(axs,items):
                ax.imshow(b,origin='lower',cmap='gray_r',vmin=0,vmax=1)
                if r:
                    for key in ('pathA','pathB'):
                        p=np.asarray(r[key]);ax.plot(p[:,1],p[:,0],lw=1.6)
                ax.set_title(title);ax.axis('off')
            fig.tight_layout();fig.savefig(out/'seed0_bodies.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
