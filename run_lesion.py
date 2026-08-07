#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from functional_arbor import Config
from functional_arbor.protocol import functional_assay

def main():
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=0);p.add_argument('--size',type=int,default=64);p.add_argument('--cycles',type=int,default=18);p.add_argument('--condition',default='credit');p.add_argument('--out',default='lesion_out');a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
 r=functional_assay(Config(size=a.size,seed=a.seed,train_cycles=a.cycles),a.condition); data={k:r[k] for k in ('intact','bath','lesion','lowuse','gain','target_drop','lowuse_drop','removed','low_removed')};print(json.dumps(data,indent=2));(o/'result.json').write_text(json.dumps(data,indent=2))
 fig,ax=plt.subplots(1,4,figsize=(12,3)); ims=[r['M'],r['usage'],r['lesion_mask'],r['lowuse_mask']];tt=['grown M','mature use','high-use lesion','low-use matched lesion']
 for aa,im,t in zip(ax,ims,tt):aa.imshow(im,origin='lower');aa.set_title(t);aa.axis('off')
 fig.tight_layout();fig.savefig(o/'lesion_assay.png',dpi=160)
if __name__=='__main__':main()
