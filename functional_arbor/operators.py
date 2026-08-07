import numpy as np


def shift(a, dy, dx):
    out=np.zeros_like(a)
    h,w=a.shape
    ys0=max(0,dy); ys1=min(h,h+dy); yd0=max(0,-dy); yd1=min(h,h-dy)
    xs0=max(0,dx); xs1=min(w,w+dx); xd0=max(0,-dx); xd1=min(w,w-dx)
    out[ys0:ys1,xs0:xs1]=a[yd0:yd1,xd0:xd1]
    return out


def div_k_grad(k,u):
    """Conservative nearest-neighbour face flux with zero normal flux at edges."""
    ur=np.roll(u,-1,axis=1); ul=np.roll(u,1,axis=1)
    ud=np.roll(u,-1,axis=0); uu=np.roll(u,1,axis=0)
    kr=0.5*(k+np.roll(k,-1,axis=1)); kl=0.5*(k+np.roll(k,1,axis=1))
    kd=0.5*(k+np.roll(k,-1,axis=0)); ku=0.5*(k+np.roll(k,1,axis=0))
    fr=kr*(ur-u); fl=kl*(u-ul); fd=kd*(ud-u); fu=ku*(u-uu)
    fr[:,-1]=0; fl[:,0]=0; fd[-1,:]=0; fu[0,:]=0
    return (fr-fl)+(fd-fu)

def grad(a):
    gx=0.5*(shift(a,0,-1)-shift(a,0,1))
    gy=0.5*(shift(a,-1,0)-shift(a,1,0))
    return gx,gy


def max_filter(a, radius=1):
    out=np.array(a,copy=True)
    for dy in range(-radius,radius+1):
        for dx in range(-radius,radius+1):
            out=np.maximum(out,shift(a,dy,dx))
    return out


def smooth(a, rounds=2):
    x=np.array(a,copy=True)
    for _ in range(rounds):
        x=(x+shift(x,1,0)+shift(x,-1,0)+shift(x,0,1)+shift(x,0,-1))/5.0
    return x
