#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import matplotlib.pyplot as plt
from functional_arbor import Config
from functional_arbor.protocol import regrowth_assay
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=0);p.add_argument('--size',type=int,default=64);p.add_argument('--cycles',type=int,default=18);p.add_argument('--regrow-cycles',type=int,default=8);p.add_argument('--condition',default='credit');p.add_argument('--out',default='regrow_out');a=p.parse_args()
o=Path(a.out);o.mkdir(parents=True,exist_ok=True);cfg=Config(size=a.size,seed=a.seed,train_cycles=a.cycles,regrow_cycles=a.regrow_cycles);r=regrowth_assay(cfg,a.condition)
print(json.dumps({k:r[k] for k in ('intact','before','after','recovery')},indent=2));(o/'result.json').write_text(json.dumps({k:r[k] for k in ('intact','before','after','recovery')},indent=2))
plt.imshow(r['M'],origin='lower');plt.title(f"regrown arbor recovery={r['recovery']:.3f}");plt.axis('off');plt.savefig(o/'regrown.png',dpi=160,bbox_inches='tight')
