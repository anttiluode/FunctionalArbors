#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--out',default='v07_plots');a=p.parse_args();d=json.loads(Path(a.receipt).read_text());s=d['summary'];out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    arms=[x for x in ('coherent','phase_scramble','phase_reverse','magnitude_only','no_field') if x in s]
    vals=[s[x]['reconnect_rate']['mean'] for x in arms];sd=[s[x]['reconnect_rate']['sd'] for x in arms]
    fig,ax=plt.subplots(figsize=(8,4.6));ax.bar(range(len(arms)),vals,yerr=sd,capsize=4);ax.set_xticks(range(len(arms)),[x.replace('_','\n') for x in arms]);ax.set_ylabel('reconnections / extension');ax.set_title('v0.7 persistent-tip search efficiency');fig.tight_layout();fig.savefig(out/'reconnect_rate.png',dpi=170);plt.close(fig)
    if 'coherent_geometry_timing' in s:
        q=s['coherent_geometry_timing'];x=np.asarray(q['delta_length']);y=np.asarray(q['delta_edge50']);fig,ax=plt.subplots(figsize=(6,5));ax.scatter(x,y);xx=np.linspace(x.min()-1,x.max()+1,100);ax.plot(xx,q['slope']*xx+q['intercept']);ax.axhline(0,lw=.8);ax.axvline(0,lw=.8);ax.set_xlabel('change A-B shortest path (edges)');ax.set_ylabel('change edge50 delay (frames)');ax.set_title(f"coherent: geometry vs timing r={q['corr']:.3f}");fig.tight_layout();fig.savefig(out/'geometry_vs_timing.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
