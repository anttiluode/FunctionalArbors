#!/usr/bin/env python3
from __future__ import annotations
import argparse,os,sys
import numpy as np
import matplotlib.pyplot as plt
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v07_persistent_ephaptic.persistent_arbor import V07Config,PersistentEphapticArbor
else:from .persistent_arbor import V07Config,PersistentEphapticArbor

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=0);p.add_argument('--out',default='v07_field.png');a=p.parse_args()
    m=PersistentEphapticArbor(V07Config(seed=a.seed,bootstrap_mass=70));assert m.bootstrap()['ok'];m.prepare_development()
    m.drive_sequence(20,'coherent',64)
    # Recompute one explicit field snapshot from current state.
    lap=m._lap(m.psi,True);itm=(-m.cfg.stiffness*lap)*m.body;ve=m.solve_extracellular(itm);ex,ey=m.field_from_potential(ve)
    fig=plt.figure(figsize=(13,4));
    ax=fig.add_subplot(1,3,1);ax.imshow(m.body,cmap='gray_r');ax.set_title('binary arbor');ax.axis('off')
    ax=fig.add_subplot(1,3,2);im=ax.imshow(np.real(ve));fig.colorbar(im,ax=ax,fraction=.046);ax.set_title('Re quasi-static Ve');ax.axis('off')
    ax=fig.add_subplot(1,3,3);mag=np.sqrt(np.abs(ex)**2+np.abs(ey)**2);ax.imshow(mag);skip=2;Y,X=np.mgrid[0:m.cfg.size:skip,0:m.cfg.size:skip];ax.quiver(X,Y,np.real(ex)[::skip,::skip],-np.real(ey)[::skip,::skip]);ax.set_title('|E| + Re field vectors');ax.axis('off')
    fig.tight_layout();fig.savefig(a.out,dpi=170);print(a.out)
if __name__=='__main__':main()
