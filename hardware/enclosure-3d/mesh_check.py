"""STL sanity checker for FDM parts (numpy only).  Part of the enclosure pre-send checklist.

    py -3.12 mesh_check.py stl/*.stl            # exit code 1 if any HARD check fails

WHAT IT CHECKS (on the SAVED STL, in its print orientation: +Z up, the plate is z = min z)
  1. closed mesh: after welding vertices (1e-5 mm) every undirected edge is used by exactly two
     triangles, once in each direction  ->  0 open edges, 0 non-manifold edges, 0 edges whose two
     faces disagree in orientation ("reversed faces");  every connected shell has positive signed
     volume (outward normals).
  2. no degenerate triangles (area < 1e-9 mm^2 or a repeated vertex index).
  3. bounding box: longest side <= 240 mm.
  4. wall thickness (heuristic): from up to N sample points on the surface a ray is shot INTO the
     material along the inverse face normal; if it meets an (almost) anti-parallel face within
     PROBE mm that distance is a local wall thickness.  < 0.8 mm = HARD fail, < 1.5 mm = warning
     (the owner's rule: walls 1.5-2 mm, never below 0.8; screw seats >= 1 mm are expected to warn).
  5. overhangs (no supports): every face whose outward normal points down by more than 45 deg from
     the vertical (n_z < -sin 45 deg - tolerance), is not on the plate and is not a flat ceiling
     (n_z < -0.99) is a HARD fail.  Flat ceilings (bridges) above the plate are grouped into
     connected regions per height; the bridge span of a region is twice the radius of the largest circle that fits
     inside it (a 8 x 30 mm rectangle: 8 mm; a 0.2 mm wide stair ring around a letter: 0.2 mm):
     > 10 mm = HARD fail, otherwise listed.

WHAT IT DOES NOT CHECK
  * whether a bridge is supported on BOTH sides, nor sagging/stringing, nor island starts in a layer
    (a face that begins in mid-air but looks like a 45 deg slope is accepted);
  * knife-edges / wedges (a thin wedge between non-parallel faces is invisible to the anti-parallel
    ray test), thin features narrower than the sampling density (random samples, seeded);
  * wall thickness measured only along face normals (diagonal thin sections are under-estimated
    in thickness only if the normal passes through them), holes < 0.4 mm, tolerances, shrinkage;
  * whether the slicer (Bambu Studio) will accept / orient the part - open the STL once and look
    at the layer preview before printing (owner's checklist).
"""
from __future__ import annotations

import math
import os
import re
import struct
import sys
from dataclasses import dataclass, field

import numpy as np

WELD = 1e-5
MAX_LEN = 240.0
HARD_MIN_WALL = 0.8
WARN_MIN_WALL = 1.5
PROBE = 4.0
OVERHANG_DEG = 45.0
OVERHANG_TOL_DEG = 0.3
MAX_BRIDGE = 10.0
FLAT_CEILING_NZ = -0.99
ANTI_PARALLEL = -0.85


# ------------------------------------------------------------------------------ reading
def read_stl(path: str) -> np.ndarray:
    """Return an (n, 3, 3) float64 array of triangles (ASCII or binary STL)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + 50 * n == len(data):
            rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
            return np.frombuffer(data, dtype=rec, count=n, offset=84)["v"].astype(np.float64)
    text = data.decode("ascii", errors="replace")
    nums = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", text)
    arr = np.array(nums, dtype=np.float64)
    if arr.size == 0 or arr.shape[0] % 3:
        raise ValueError(f"{path}: not a readable STL")
    return arr.reshape(-1, 3, 3)


def weld(tris: np.ndarray):
    """Return (vertices (m,3), faces (n,3) int) with vertices merged at WELD resolution."""
    flat = tris.reshape(-1, 3)
    key = np.round(flat / WELD).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return flat[idx], inv.reshape(-1, 3)


# ------------------------------------------------------------------------------ report
@dataclass
class Report:
    name: str = ""
    triangles: int = 0
    bbox: tuple = ()
    open_edges: int = 0
    nonmanifold_edges: int = 0
    reversed_edges: int = 0
    degenerate: int = 0
    shells: int = 0
    negative_shells: int = 0
    volume: float = 0.0
    min_wall: float = float("inf")
    min_wall_at: tuple = ()
    thin_hard: int = 0
    thin_warn: int = 0
    thin_examples: list = field(default_factory=list)   # (thickness, (x, y, z)) of the thinnest distinct spots
    overhang_faces: int = 0
    overhang_area: float = 0.0
    overhang_example: tuple = ()
    bridges: list = field(default_factory=list)       # (z, span, area, (x,y)) of flat ceilings
    bridge_fail: int = 0
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def text(self) -> str:
        lines = [f"== {self.name}: {'PASS' if self.ok else 'FAIL'}  ({self.triangles} triangles, "
                 f"bbox {self.bbox[0]:.1f} x {self.bbox[1]:.1f} x {self.bbox[2]:.1f} mm, "
                 f"volume {self.volume / 1000:.1f} cm3, {self.shells} shell(s))"]
        lines.append(f"   edges: open {self.open_edges}, non-manifold {self.nonmanifold_edges}, "
                     f"reversed {self.reversed_edges}; degenerate faces {self.degenerate}; "
                     f"inverted shells {self.negative_shells}")
        mw = "n/a" if math.isinf(self.min_wall) else f"{self.min_wall:.2f} mm at {tuple(round(float(c), 1) for c in self.min_wall_at)}"
        lines.append(f"   thinnest measured wall: {mw}  (<0.8: {self.thin_hard} samples, <1.5: {self.thin_warn} samples)")
        lines.append(f"   overhang faces > {OVERHANG_DEG:.0f} deg: {self.overhang_faces} "
                     f"({self.overhang_area:.1f} mm2) {self.overhang_example if self.overhang_faces else ''}")
        if self.bridges:
            worst = max(self.bridges, key=lambda b: b[1])
            lines.append(f"   flat ceilings above the plate: {len(self.bridges)}; widest bridge span "
                         f"{worst[1]:.1f} mm at z={worst[0]:.1f} (limit {MAX_BRIDGE:.0f})")
        for w in self.warnings:
            lines.append(f"   warning: {w}")
        for d, at in self.thin_examples:
            lines.append(f"      thin spot {d:.2f} mm near ({at[0]:.1f}, {at[1]:.1f}, {at[2]:.1f})")
        for f in self.failures:
            lines.append(f"   FAIL: {f}")
        return "\n".join(lines)


# ------------------------------------------------------------------------------ topology
def _edge_checks(faces: np.ndarray, rep: Report):
    a = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    b = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    nv = int(faces.max()) + 1
    key = lo.astype(np.int64) * nv + hi
    fwd = (a < b).astype(np.int64)                         # direction relative to the sorted key
    order = np.argsort(key, kind="stable")
    key, fwd = key[order], fwd[order]
    uniq, start, cnt = np.unique(key, return_index=True, return_counts=True)
    rep.open_edges = int((cnt == 1).sum())
    rep.nonmanifold_edges = int((cnt > 2).sum())
    two = np.where(cnt == 2)[0]
    s = fwd[start[two]] + fwd[start[two] + 1]
    rep.reversed_edges = int((s != 1).sum())               # a proper pair is one forward + one backward


def _shells(faces: np.ndarray, verts: np.ndarray, rep: Report):
    """Connected components over shared vertices (union-find on vertex indices) + signed volume."""
    parent = np.arange(len(verts))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # vectorised-ish union: iterate over faces (n ~ 1e5 is fine)
    for f0, f1, f2 in faces.tolist():
        r0, r1, r2 = find(f0), find(f1), find(f2)
        if r0 != r1:
            parent[r1] = r0
        r2 = find(f2)
        r0 = find(f0)
        if r0 != r2:
            parent[r2] = r0
    roots = np.array([find(i) for i in faces[:, 0].tolist()])
    p0, p1, p2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    vol = np.einsum("ij,ij->i", p0, np.cross(p1, p2)) / 6.0
    shells = {}
    for r, v in zip(roots.tolist(), vol.tolist()):
        shells[r] = shells.get(r, 0.0) + v
    rep.shells = len(shells)
    rep.negative_shells = sum(1 for v in shells.values() if v < 0)
    rep.volume = float(sum(shells.values()))


# ------------------------------------------------------------------------------ wall thickness
def _build_grid(p0, p1, p2, cell):
    lo = np.minimum(np.minimum(p0, p1), p2)
    hi = np.maximum(np.maximum(p0, p1), p2)
    gmin = lo.min(axis=0) - 1e-3
    ilo = np.floor((lo - gmin) / cell).astype(np.int64)
    ihi = np.floor((hi - gmin) / cell).astype(np.int64)
    dims = ihi.max(axis=0) + 1
    cells: dict[int, list] = {}
    # triangles whose bbox spans many cells are rare; loop in python over those, vectorise the small ones
    span = ihi - ilo + 1
    small = (span.prod(axis=1) <= 8)
    for t in np.where(~small)[0].tolist():
        for ix in range(ilo[t, 0], ihi[t, 0] + 1):
            for iy in range(ilo[t, 1], ihi[t, 1] + 1):
                for iz in range(ilo[t, 2], ihi[t, 2] + 1):
                    cells.setdefault((ix * dims[1] + iy) * dims[2] + iz, []).append(t)
    for t in np.where(small)[0].tolist():
        for ix in range(ilo[t, 0], ihi[t, 0] + 1):
            for iy in range(ilo[t, 1], ihi[t, 1] + 1):
                for iz in range(ilo[t, 2], ihi[t, 2] + 1):
                    cells.setdefault((ix * dims[1] + iy) * dims[2] + iz, []).append(t)
    return gmin, dims, {k: np.array(v, dtype=np.int64) for k, v in cells.items()}


def _wall_thickness(tris, normals, areas, rep: Report, samples: int, seed: int):
    rng = np.random.default_rng(seed)
    n = len(tris)
    if n == 0:
        return
    p0, p1, p2 = tris[:, 0], tris[:, 1], tris[:, 2]
    cell = 2.0
    gmin, dims, cells = _build_grid(p0, p1, p2, cell)
    e1, e2 = p1 - p0, p2 - p0
    # sample faces proportionally to sqrt(area) so large walls and small features are both visited
    w = np.sqrt(areas)
    w = w / w.sum()
    pick = rng.choice(n, size=min(samples, n), replace=False, p=w) if samples < n else np.arange(n)
    bary = rng.random((len(pick), 2))
    flip = bary.sum(axis=1) > 1
    bary[flip] = 1 - bary[flip]
    pts = p0[pick] + bary[:, :1] * e1[pick] + bary[:, 1:] * e2[pick]
    best = float("inf")
    best_at = ()
    hard = warn = 0
    spots: dict = {}
    for k, t in enumerate(pick.tolist()):
        nrm = normals[t]
        d = -nrm
        o = pts[k] + d * 1e-4
        end = o + d * PROBE
        lo = np.minimum(o, end) - 1e-3
        hi = np.maximum(o, end) + 1e-3
        ilo = np.floor((lo - gmin) / cell).astype(int)
        ihi = np.floor((hi - gmin) / cell).astype(int)
        cand = []
        for ix in range(max(ilo[0], 0), min(ihi[0], dims[0] - 1) + 1):
            for iy in range(max(ilo[1], 0), min(ihi[1], dims[1] - 1) + 1):
                for iz in range(max(ilo[2], 0), min(ihi[2], dims[2] - 1) + 1):
                    c = cells.get((ix * dims[1] + iy) * dims[2] + iz)
                    if c is not None:
                        cand.append(c)
        if not cand:
            continue
        ids = np.unique(np.concatenate(cand))
        ids = ids[ids != t]
        ids = ids[(normals[ids] @ nrm) < ANTI_PARALLEL]          # only faces looking back at us
        if len(ids) == 0:
            continue
        # Moller-Trumbore
        pvec = np.cross(d, e2[ids])
        det = np.einsum("ij,ij->i", e1[ids], pvec)
        ok = np.abs(det) > 1e-12
        inv = np.zeros_like(det)
        inv[ok] = 1.0 / det[ok]
        tvec = o - p0[ids]
        u = np.einsum("ij,ij->i", tvec, pvec) * inv
        qvec = np.cross(tvec, e1[ids])
        v = (qvec @ d) * inv
        tt = np.einsum("ij,ij->i", e2[ids], qvec) * inv
        hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (tt > 1e-6) & (tt <= PROBE)
        if hit.any():
            dist = float(tt[hit].min()) + 1e-4
            if dist < best:
                best, best_at = dist, tuple(pts[k])
            if dist < HARD_MIN_WALL:
                hard += 1
            elif dist < WARN_MIN_WALL:
                warn += 1
            if dist < WARN_MIN_WALL:
                sk = tuple(np.round(pts[k] / 3.0).astype(int).tolist())
                if sk not in spots or dist < spots[sk][0]:
                    spots[sk] = (dist, tuple(float(c) for c in pts[k]))
    rep.min_wall, rep.min_wall_at = best, best_at
    rep.thin_examples = sorted(spots.values())[:6]
    rep.thin_hard, rep.thin_warn = hard, warn



def _inscribed_span(tri2d, dmin, dmax):
    """Diameter of the largest circle inside a flat region given as 2D triangles (m, 3, 2): the longest unsupported distance.
    Boundary = edges used by exactly one triangle; samples = a grid inside the region plus the triangles' centroids and vertices.
    Estimate within about one grid step; exact for rectangles and rings of any width.  (A bounding-box measure would call a thin ring
    around a big letter a 'bridge' as wide as the letter.)"""
    m = len(tri2d)
    e = np.concatenate([tri2d[:, [0, 1]], tri2d[:, [1, 2]], tri2d[:, [2, 0]]])           # (3m, 2, 2)
    q = np.round(e / 1e-4).astype(np.int64)
    a = q.reshape(-1, 4)
    b = np.concatenate([q[:, 1], q[:, 0]], axis=1)
    swap = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
    key = np.where(swap[:, None], b, a)
    _, idx, cnt = np.unique(key, axis=0, return_index=True, return_counts=True)
    bnd = e[idx[cnt == 1]]                                                                # boundary segments (k, 2, 2)
    if len(bnd) == 0:
        return dmin
    lo, hi = tri2d.reshape(-1, 2).min(axis=0), tri2d.reshape(-1, 2).max(axis=0)
    step = max(0.1, math.sqrt((hi[0] - lo[0]) * (hi[1] - lo[1]) / 12000.0))
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0] + step, step), np.arange(lo[1], hi[1] + step, step))
    pts = np.stack([gx.ravel(), gy.ravel()], axis=1)
    extra = np.concatenate([tri2d.mean(axis=1), tri2d.reshape(-1, 2)])
    p0, p1 = bnd[:, 0], bnd[:, 1]

    def inside(P):
        out = np.zeros(len(P), bool)
        for c in range(0, len(P), 2000):
            Q = P[c:c + 2000]
            y0, y1 = p0[None, :, 1], p1[None, :, 1]
            cond = ((y0 > Q[:, None, 1]) != (y1 > Q[:, None, 1]))
            xint = p0[None, :, 0] + (Q[:, None, 1] - y0) * (p1[None, :, 0] - p0[None, :, 0]) / np.where(y1 == y0, 1, y1 - y0)
            out[c:c + 2000] = ((cond & (Q[:, None, 0] < xint)).sum(axis=1) % 2) == 1
        return out

    def dist(P):
        out = np.empty(len(P))
        d = p1 - p0
        dd = (d ** 2).sum(axis=1)
        dd = np.where(dd == 0, 1, dd)
        for c in range(0, len(P), 2000):
            Q = P[c:c + 2000]
            t = np.clip(((Q[:, None, :] - p0[None]) * d[None]).sum(axis=2) / dd[None], 0, 1)
            proj = p0[None] + t[..., None] * d[None]
            out[c:c + 2000] = np.sqrt(((Q[:, None, :] - proj) ** 2).sum(axis=2)).min(axis=1)
        return out

    allp = np.concatenate([pts[inside(pts)], extra])
    if len(allp) == 0:
        return dmin
    return float(2.0 * dist(allp).max())

# ------------------------------------------------------------------------------ overhangs
def _overhangs(tris, normals, areas, rep: Report, zmin):
    nz = normals[:, 2]
    limit = -math.sin(math.radians(OVERHANG_DEG + OVERHANG_TOL_DEG))
    zlow = tris[:, :, 2].max(axis=1)
    off_plate = zlow > zmin + 0.05                               # not touching the first layer
    steep = (nz < limit) & (nz > FLAT_CEILING_NZ) & off_plate
    rep.overhang_faces = int(steep.sum())
    rep.overhang_area = float(areas[steep].sum())
    if steep.any():
        i = int(np.argmax(np.where(steep, areas, 0)))
        c = tris[i].mean(axis=0)
        rep.overhang_example = (round(float(c[0]), 1), round(float(c[1]), 1), round(float(c[2]), 1))
    # flat ceilings: connected regions (shared vertices) per height
    flat = np.where((nz <= FLAT_CEILING_NZ) & off_plate)[0]
    if len(flat) == 0:
        return
    zs = np.round(tris[flat, :, 2].mean(axis=1) / 0.01).astype(np.int64)
    for zlevel in np.unique(zs):
        ids = flat[zs == zlevel]
        key = np.round(tris[ids].reshape(-1, 3) / WELD).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.reshape(-1, 3)
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b, c in inv.tolist():
            for x, y in ((a, b), (b, c)):
                rx, ry = find(x), find(y)
                if rx != ry:
                    parent[ry] = rx
        groups: dict[int, list] = {}
        for j, (a, _, _) in enumerate(inv.tolist()):
            groups.setdefault(find(a), []).append(j)
        for members in groups.values():
            pts = tris[ids[members]].reshape(-1, 3)
            dx = float(np.ptp(pts[:, 0]))
            dy = float(np.ptp(pts[:, 1]))
            span = _inscribed_span(tris[ids[members]][:, :, :2], min(dx, dy), max(dx, dy))
            area = float(areas[ids[members]].sum())
            rep.bridges.append((float(zlevel) * 0.01, span, area, (float(pts[:, 0].mean()), float(pts[:, 1].mean()))))
            if span > MAX_BRIDGE:
                rep.bridge_fail += 1


# ------------------------------------------------------------------------------ driver
def check_triangles(tris: np.ndarray, name: str = "mesh", samples: int = 4000, seed: int = 1) -> Report:
    rep = Report(name=name, triangles=len(tris))
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    rep.bbox = tuple((hi - lo).tolist())
    verts, faces = weld(tris)
    # degenerate
    p0, p1, p2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    areas2 = np.linalg.norm(cr, axis=1)
    rep.degenerate = int(((areas2 / 2 < 1e-9) | (faces[:, 0] == faces[:, 1]) |
                          (faces[:, 1] == faces[:, 2]) | (faces[:, 0] == faces[:, 2])).sum())
    good = areas2 > 0
    _edge_checks(faces[good] if rep.degenerate else faces, rep)
    _shells(faces, verts, rep)
    tri_w = verts[faces]
    normals = np.zeros_like(cr)
    normals[good] = cr[good] / areas2[good, None]
    areas = areas2 / 2
    keep = good & (areas > 1e-9)
    _wall_thickness(tri_w[keep], normals[keep], areas[keep], rep, samples, seed)
    _overhangs(tri_w[keep], normals[keep], areas[keep], rep, float(lo[2]))

    f = rep.failures
    if rep.open_edges:
        f.append(f"{rep.open_edges} open edge(s)")
    if rep.nonmanifold_edges:
        f.append(f"{rep.nonmanifold_edges} non-manifold edge(s)")
    if rep.reversed_edges:
        f.append(f"{rep.reversed_edges} edge(s) with inconsistent face orientation (reversed faces)")
    if rep.negative_shells:
        f.append(f"{rep.negative_shells} shell(s) with negative volume (inverted normals)")
    if rep.degenerate:
        f.append(f"{rep.degenerate} degenerate triangle(s)")
    if max(rep.bbox) > MAX_LEN:
        f.append(f"longest side {max(rep.bbox):.1f} mm > {MAX_LEN:.0f} mm")
    if rep.thin_hard:
        f.append(f"wall thinner than {HARD_MIN_WALL} mm (min {rep.min_wall:.2f} mm near {tuple(round(float(c), 1) for c in rep.min_wall_at)})")
    if rep.overhang_faces:
        f.append(f"{rep.overhang_faces} face(s) overhang more than {OVERHANG_DEG:.0f} deg (e.g. near {rep.overhang_example})")
    if rep.bridge_fail:
        f.append(f"{rep.bridge_fail} flat ceiling region(s) with a span > {MAX_BRIDGE:.0f} mm")
    if rep.thin_warn:
        rep.warnings.append(f"{rep.thin_warn} sample(s) with wall {HARD_MIN_WALL}-{WARN_MIN_WALL} mm (screw seats / countersinks are expected here)")
    return rep


def check_file(path: str, samples: int = 4000, seed: int = 1) -> Report:
    return check_triangles(read_stl(path), os.path.basename(path), samples, seed)


def main(argv):
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        print(__doc__)
        return 2
    bad = 0
    for p in paths:
        rep = check_file(p)
        print(rep.text())
        bad += 0 if rep.ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
