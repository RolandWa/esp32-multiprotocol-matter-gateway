"""Layer-section pre-check (shapely): the owner's "inspect layer sections every 0.2-0.4 mm" as far as it can be
automated without the slicer.  NOT part of the pytest suite (shapely is not a project dependency).

    py -3.12 layer_check.py stl/enclosure_base_rev03.stl            # one file
    py -3.12 layer_check.py                                          # every STL in stl/

For every layer (0.2 mm steps, sampled 0.1 mm above the layer floor) the mesh is sliced, the even-odd fill of
the section is built, and a morphological opening with radius R = 0.4 mm (= half of the 0.8 mm hard minimum) is
applied: whatever the opening removes and that is larger than MIN_AREA mm2 is a feature thinner than 0.8 mm
(a lone wall the slicer would drop or isolate), but only when it persists for >= 6 layers at the same place - the tips of
45-degree slopes and louvre slats are thin for a few layers by geometry and are not reported.  Corner rounding of sharp corners is below MIN_AREA and ignored.
Also prints the number of separate islands per layer range (a sudden new island in mid-air would need support).
It does not model the slicer's own gap-fill / thin-wall options and it does not replace opening the 3MF layer preview.
"""
from __future__ import annotations

import glob
import os
import sys
from functools import reduce

import numpy as np
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_check  # noqa: E402

R = 0.4
MIN_AREA = 0.5
MIN_CHAIN = 6           # layers (= 1.2 mm of height at 0.2 mm layers)


def section(tris, z):
    """Even-odd fill of the mesh section at height z.  The cut segments are oriented with the face normal (solid on the left),
    chained into closed rings by their end points, and the rings are XOR-ed (nested rings alternate solid / air)."""
    d = tris[:, :, 2] - z
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    segs = {}
    for i, j in ((0, 1), (1, 2), (2, 0)):
        cross = (d[:, i] > 0) != (d[:, j] > 0)
        idx = np.where(cross)[0]
        t = d[idx, i] / (d[idx, i] - d[idx, j])
        p = tris[idx, i, :2] + t[:, None] * (tris[idx, j, :2] - tris[idx, i, :2])
        for k, q in zip(idx.tolist(), p):
            segs.setdefault(k, []).append(q)
    nxt = {}
    key = lambda q: (round(float(q[0]) * 1e5), round(float(q[1]) * 1e5))  # noqa: E731
    for k, v in segs.items():
        if len(v) != 2 or np.linalg.norm(v[0] - v[1]) < 1e-9:
            continue
        direction = np.array([-nrm[k, 1], nrm[k, 0]])        # z_hat x n  (solid on the left)
        a, b = (v[0], v[1]) if np.dot(v[1] - v[0], direction) >= 0 else (v[1], v[0])
        nxt[key(a)] = (a, b)
    rings, used = [], set()
    for k0 in list(nxt):
        if k0 in used:
            continue
        ring, k = [], k0
        while k in nxt and k not in used:
            used.add(k)
            a, b = nxt[k]
            ring.append(tuple(a))
            k = key(b)
        if len(ring) >= 3 and k == k0:
            rings.append(Polygon(ring).buffer(0))
    if not rings:
        return Polygon()
    return reduce(lambda x, y: x.symmetric_difference(y), rings)


def check(path, step=0.2):
    """Return (layers, persistent_thin, islands).  A thin piece counts only if it persists over MIN_CHAIN consecutive layers at
    the same place: the tips of 45-degree slopes / louvre slats are thin for a few layers by geometry and are not reported."""
    tris = mesh_check.read_stl(path)
    zmin, zmax = tris[:, :, 2].min(), tris[:, :, 2].max()
    layers = np.arange(zmin + 0.1, zmax, step)
    islands = []
    chains = []                     # each: [last_layer_index, (x, y), length, first_height, area]
    for li, z in enumerate(layers):
        sec = section(tris, z)
        if sec.is_empty:
            continue
        opened = sec.buffer(-R).buffer(R + 0.02)
        lost = sec.difference(opened)
        geoms = list(lost.geoms) if hasattr(lost, "geoms") else [lost]
        for g in geoms:
            if g.area <= MIN_AREA:
                continue
            c = (g.centroid.x, g.centroid.y)
            for ch in chains:
                if ch[0] == li - 1 and np.hypot(ch[1][0] - c[0], ch[1][1] - c[1]) < 2.5:
                    ch[0], ch[1], ch[2], ch[4] = li, c, ch[2] + 1, max(ch[4], g.area)
                    break
            else:
                chains.append([li, c, 1, z - zmin, g.area])
        islands.append((z - zmin, len(sec.geoms) if hasattr(sec, "geoms") else 1))
    persistent = [(ch[3], ch[2] * step, ch[4], ch[1][0], ch[1][1]) for ch in chains if ch[2] >= MIN_CHAIN]
    return layers, persistent, islands


def main(argv):
    paths = [a for a in argv if not a.startswith("-")] or sorted(glob.glob(os.path.join(HERE, "stl", "*.stl")))
    rc = 0
    for p in paths:
        layers, bad, islands = check(p)
        counts = [n for _, n in islands]
        print(f"{os.path.basename(p)}: {len(layers)} layers (0.2 mm), islands per layer {min(counts)}..{max(counts)}, "
              f"features thinner than {2 * R:.1f} mm persisting >= {MIN_CHAIN} layers: {len(bad)}")
        for h, ext, a, x, y in bad[:8]:
            print(f"    from height {h:.1f} mm for {ext:.1f} mm: area {a:.2f} mm2 near x={x:.1f}, y={y:.1f}")
        rc |= 1 if bad else 0
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
