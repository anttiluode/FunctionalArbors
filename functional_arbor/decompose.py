from __future__ import annotations
import heapq, math
import numpy as np


def patch_center(model, which: int):
    iy, ix = np.unravel_index(int(np.argmax(model.patches[which])), model.patches[which].shape)
    return int(iy), int(ix)


def root_center(model):
    iy, ix = np.unravel_index(int(np.argmax(model.root)), model.root.shape)
    return int(iy), int(ix)


def _neighbors8(y, x, h, w):
    for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
        yy, xx = y+dy, x+dx
        if 0 <= yy < h and 0 <= xx < w:
            yield yy, xx, (math.sqrt(2.0) if dy and dx else 1.0)


def anatomy_path(model, which: int, penalty: float = 12.0, floor: float = 0.02, patch_level: float = 0.45, root_level: float = 0.45):
    """Least-cost path defined by anatomy only, not by conductivity/substrate.

    The source and soma are *regions*, not one rounded cell.  This is important on
    even grids: choosing ``argmax`` of a half-pixel-centred Gaussian gives one side
    an artificial one-cell head start.  Multi-source/multi-goal Dijkstra preserves
    the mirror symmetry of the actual drive/readout masks.
    """
    M = np.asarray(model.M, float)
    h, w = M.shape
    source_mask = np.asarray(model.patches[which],float) >= patch_level*float(np.max(model.patches[which]))
    goal_mask = np.asarray(model.root,float) >= root_level*float(np.max(model.root))
    sources=np.argwhere(source_mask); goals=np.argwhere(goal_mask)
    if not len(sources) or not len(goals): raise RuntimeError('empty source/goal region')
    mn, mx = float(M.min()), float(M.max())
    q = np.clip((M-mn)/(mx-mn+1e-12), 0.0, 1.0)
    cell = 1.0 + penalty * np.square(1.0 - np.maximum(q, floor))
    dist = np.full((h,w), np.inf, float)
    prev = np.full((h,w,2), -1, np.int32)
    pq=[]
    for sy,sx in sources:
        sy,sx=int(sy),int(sx); dist[sy,sx]=0.0; heapq.heappush(pq,(0.0,sy,sx))
    end=None
    while pq:
        d,y,x = heapq.heappop(pq)
        if d != dist[y,x]: continue
        if goal_mask[y,x]: end=(y,x); break
        for yy,xx,ds in _neighbors8(y,x,h,w):
            nd = d + ds * 0.5 * (cell[y,x] + cell[yy,xx])
            if nd < dist[yy,xx]:
                dist[yy,xx] = nd; prev[yy,xx] = (y,x); heapq.heappush(pq,(nd,yy,xx))
    if end is None: raise RuntimeError('no anatomy path')
    path=[]; cur=end
    while True:
        path.append(cur)
        py,px = prev[cur[0],cur[1]]
        if py < 0: break  # reached one of the source-region cells
        cur=(int(py),int(px))
    path.reverse()
    return path


def path_arclength(path):
    if len(path) < 2: return 0.0
    s=0.0
    for (y0,x0),(y1,x1) in zip(path[:-1],path[1:]):
        s += math.hypot(y1-y0,x1-x0)
    return float(s)


def path_profile(field, path):
    f=np.asarray(field,float)
    return np.asarray([f[y,x] for y,x in path],float)


def route_metrics(model, which: int, penalty: float = 12.0, solid_threshold: float = 0.30):
    path=anatomy_path(model,which,penalty=penalty)
    K=np.asarray(model.conductivity(mature=True),float)
    L=path_arclength(path)
    if len(path)<2:
        return {'path':path,'length':0.0,'straight':0.0,'tortuosity':1.0,'slowness':0.0,'mean_slowness':0.0,
                'mean_K':float(K[path[0]]),'solid_fraction':0.0}
    start=path[0]; goal=path[-1]
    straight=math.hypot(goal[0]-start[0],goal[1]-start[1])
    S=0.0; k_weight=0.0; solid_len=0.0
    for (y0,x0),(y1,x1) in zip(path[:-1],path[1:]):
        ds=math.hypot(y1-y0,x1-x0)
        k=0.5*(K[y0,x0]+K[y1,x1])
        # c ~ sqrt(diffusion*K); diffusion is common to both routes and retained.
        c=math.sqrt(max(model.cfg.diffusion*k,1e-12))
        S += ds/c
        k_weight += ds*k
        if 0.5*(model.M[y0,x0]+model.M[y1,x1]) >= solid_threshold:
            solid_len += ds
    return {
        'path':path,
        'length':float(L),
        'straight':float(straight),
        'tortuosity':float(L/(straight+1e-12)),
        'slowness':float(S),
        'mean_slowness':float(S/(L+1e-12)),
        'mean_K':float(k_weight/(L+1e-12)),
        'solid_fraction':float(solid_len/(L+1e-12)),
    }


def symmetric_length_speed_decomposition(a, b):
    """Exact two-route decomposition of S_A-S_B = L_A*s_A - L_B*s_B."""
    LA,LB=float(a['length']),float(b['length'])
    sA,sB=float(a['mean_slowness']),float(b['mean_slowness'])
    geom=(LA-LB)*0.5*(sA+sB)
    speed=(sA-sB)*0.5*(LA+LB)
    return {'predicted_slowness_diff':float(a['slowness']-b['slowness']),
            'geometry_component':float(geom),'speed_component':float(speed),
            'closure_error':float((geom+speed)-(a['slowness']-b['slowness']))}


def _disk_indices(shape, cy, cx, radius):
    h,w=shape; r=int(math.ceil(radius)); out=[]
    for y in range(max(0,int(round(cy))-r),min(h,int(round(cy))+r+1)):
        for x in range(max(0,int(round(cx))-r),min(w,int(round(cx))+r+1)):
            if (y-cy)**2+(x-cx)**2 <= radius*radius:
                out.append((y,x))
    return out


def path_tube(shape, path, radius=1.25, values=None, background=0.08, fill_value=1.6):
    """Rasterize a path to a conductivity tube.

    If values are supplied they are sampled along normalized path index.  The
    maximum wins where disks overlap, which prevents a later low-K sample from
    erasing a previously laid fast segment.
    """
    K=np.full(shape,float(background),np.float32)
    n=max(len(path)-1,1)
    vals=None if values is None else np.asarray(values,float)
    for i,(y,x) in enumerate(path):
        if vals is None:
            kv=float(fill_value)
        else:
            t=i/n
            j=min(len(vals)-1,max(0,int(round(t*(len(vals)-1)))))
            kv=float(vals[j])
        for yy,xx in _disk_indices(shape,y,x,radius):
            K[yy,xx]=max(float(K[yy,xx]),kv)
    return K


def straight_path(start, goal, n=None):
    y0,x0=start; y1,x1=goal
    if n is None:
        n=max(2,int(math.ceil(math.hypot(y1-y0,x1-x0)))+1)
    ys=np.linspace(y0,y1,int(n)); xs=np.linspace(x0,x1,int(n))
    out=[]
    for y,x in zip(ys,xs):
        p=(int(round(y)),int(round(x)))
        if not out or p!=out[-1]: out.append(p)
    return out


def route_K_profile(model, route):
    K=np.asarray(model.conductivity(mature=True),float)
    return path_profile(K, route['path'])


def counterfactual_fields(model, ra, rb, tube_radius=1.25):
    """Return isolated route fields for geometry-only, speed-only, and reconstructed both.

    The A and B routes are probed in separate fields, so their counterfactuals cannot
    steal current from one another through accidental network cross-links.
    """
    shape=model.M.shape
    # Choose one common path speed for geometry-only from the learned-body median.
    Kactual=np.asarray(model.conductivity(mature=True),float)
    live=model.M>0.20
    common_fast=float(np.median(Kactual[live])) if np.any(live) else float(np.quantile(Kactual,.85))
    bg=max(0.02,float(model.cfg.mature_base_k)*0.55)
    out={'background':bg,'common_fast':common_fast}
    for label,r in [('A',ra),('B',rb)]:
        kp=route_K_profile(model,r)
        out[f'geometry_{label}']=path_tube(shape,r['path'],radius=tube_radius,background=bg,fill_value=common_fast)
        sp=straight_path(r['path'][0],r['path'][-1])
        out[f'speed_{label}']=path_tube(shape,sp,radius=tube_radius,values=kp,background=bg)
        out[f'both_{label}']=path_tube(shape,r['path'],radius=tube_radius,values=kp,background=bg)
    return out
