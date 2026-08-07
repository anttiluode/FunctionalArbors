#!/usr/bin/env python3
import argparse,matplotlib.pyplot as plt
from functional_arbor import Config,FunctionalArbor

def main():
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=0);p.add_argument('--size',type=int,default=96);p.add_argument('--cycles',type=int,default=18);p.add_argument('--condition',default='credit');a=p.parse_args();m=FunctionalArbor(Config(size=a.size,seed=a.seed,train_cycles=a.cycles),a.condition)
 plt.ion();fig,ax=plt.subplots(1,4,figsize=(12,3));order=[0,1,2,3]
 for cy in range(a.cycles):
  for pch in order:m.visit(pch,True)
  for aa in ax:aa.clear();aa.axis('off')
  ax[0].imshow(m.M,origin='lower');ax[0].set_title('structure M');ax[1].imshow(abs(m.psi),origin='lower');ax[1].set_title('|psi|');ax[2].imshow(m.E,origin='lower');ax[2].set_title('eligibility');ax[3].imshow(m.front,origin='lower');ax[3].set_title('last deposition');fig.suptitle(f'{a.condition} cycle {cy+1}/{a.cycles}');plt.pause(.03)
 plt.ioff();plt.show()
if __name__=='__main__':main()
