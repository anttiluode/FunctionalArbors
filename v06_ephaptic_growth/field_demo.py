#!/usr/bin/env python3
from __future__ import annotations
import argparse,os,sys
import numpy as np
import matplotlib.pyplot as plt
if __package__ in (None,''):
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from v06_ephaptic_growth.ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from v06_ephaptic_growth.task import DelayTask
else:
    from .ephaptic_arbor import EphapticConfig,EphapticFreeArbor
    from .task import DelayTask

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--out',default='ephaptic_field.png');a=ap.parse_args()
    c=EphapticConfig(seed=a.seed);m=EphapticFreeArbor(c);b=m.bootstrap()
    if not b['ok']:raise RuntimeError(b)
    m.mature=True;t=DelayTask(m,20);t.single(0,True,'full',steps=c.train_trace_steps)
    g=np.sqrt(m.Gx*m.Gx+m.Gy*m.Gy);fig,axs=plt.subplots(1,3,figsize=(12,4))
    axs[0].imshow(m.body,origin='lower',cmap='gray_r');axs[0].set_title('free-grown binary arbor')
    im=axs[1].imshow(m.H,origin='lower');axs[1].set_title('extracellular-field magnitude trace H')
    fig.colorbar(im,ax=axs[1],fraction=.046)
    axs[2].imshow(m.body,origin='lower',cmap='gray_r',alpha=.35);step=2;Y,X=np.mgrid[0:c.size:step,0:c.size:step]
    axs[2].quiver(X,Y,m.Gx[::step,::step],m.Gy[::step,::step],angles='xy',scale_units='xy',scale=1.6,width=.004)
    axs[2].set_title('soma-phase-referenced guidance vector G')
    for ax in axs:ax.axis('off')
    fig.suptitle('v0.6 ephaptic-like guidance proxy after one A pulse');fig.tight_layout();fig.savefig(a.out,dpi=170);plt.close(fig)
if __name__=='__main__':main()
