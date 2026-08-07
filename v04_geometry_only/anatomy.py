from __future__ import annotations
import heapq, math
import numpy as np


def _n8(y,x,h,w):
    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
        yy,xx=y+dy,x+dx
        if 0<=yy<h and 0<=xx<w:yield yy,xx,(math.sqrt(2) if dy and dx else 1.)


def binary_path(model,which,allow_bath=False,bath_penalty=50.0,patch_level=.35,root_level=.40):
    B=model.B>0.5;h,w=B.shape
    src=model.patches[which]>=patch_level*model.patches[which].max()
    goal=model.root>=root_level*model.root.max()
    sources=np.argwhere(src);dist=np.full((h,w),np.inf);prev=np.full((h,w,2),-1,np.int32);pq=[]
    for y,x in sources:
        dist[y,x]=0;heapq.heappush(pq,(0.,int(y),int(x)))
    end=None
    while pq:
        d,y,x=heapq.heappop(pq)
        if d!=dist[y,x]:continue
        if goal[y,x]:end=(y,x);break
        for yy,xx,ds in _n8(y,x,h,w):
            if not allow_bath and not B[yy,xx] and not goal[yy,xx] and not src[yy,xx]:continue
            cost=ds*(1.0 if B[yy,xx] or goal[yy,xx] or src[yy,xx] else bath_penalty)
            nd=d+cost
            if nd<dist[yy,xx]:dist[yy,xx]=nd;prev[yy,xx]=(y,x);heapq.heappush(pq,(nd,yy,xx))
    if end is None:return None
    p=[];cur=end
    while True:
        p.append(cur);py,px=prev[cur]
        if py<0:break
        cur=(int(py),int(px))
    p.reverse();return p


def arclength(path):
    if not path or len(path)<2:return float('nan') if path is None else 0.
    return float(sum(math.hypot(y1-y0,x1-x0) for (y0,x0),(y1,x1) in zip(path[:-1],path[1:])))


def straight_distance(path):
    if not path:return float('nan')
    a,b=path[0],path[-1];return float(math.hypot(b[0]-a[0],b[1]-a[1]))


def metrics(model,which):
    p=binary_path(model,which,allow_bath=False)
    soft=binary_path(model,which,allow_bath=True)
    L=arclength(p);Ls=arclength(soft)
    return {'connected':p is not None,'length':L,'tortuosity':(L/(straight_distance(p)+1e-12) if p else float('nan')),
            'soft_length':Ls,'path':p,'soft_path':soft}
