#!/usr/bin/env python3
import argparse,csv,json
from pathlib import Path
import numpy as np
from functional_arbor import Config
from functional_arbor.protocol import functional_assay

def main():
 p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--size',type=int,default=64);p.add_argument('--cycles',type=int,default=18);p.add_argument('--conditions',nargs='+',default=['blind','local','credit','anti_credit','open_loop']);p.add_argument('--out',default='assay_out');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 rows=[]
 for sd in range(a.seeds):
  for cond in a.conditions:
   cfg=Config(size=a.size,seed=sd,train_cycles=a.cycles)
   r=functional_assay(cfg,cond,False); row={'seed':sd,'condition':cond,'mass':float(r['M'].sum()),'signed_pref':r['train']['signed_preference'],'gain':r['gain'],'target_drop':r['target_drop'],'lowuse_drop':r['lowuse_drop'],'removed':r['removed'],'low_removed':r['low_removed']};rows.append(row);print(sd,cond,'pref %.4f gain %.3f lesion %.3f low %.3f'%(row['signed_pref'],row['gain'],row['target_drop'],row['lowuse_drop']))
 with open(out/'results.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 summary={}
 for cond in a.conditions:
  z=[r for r in rows if r['condition']==cond];summary[cond]={k:float(np.mean([x[k] for x in z])) for k in ('signed_pref','gain','target_drop','lowuse_drop','mass')}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
