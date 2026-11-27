"""Preview PNGs of the assembled enclosure (matplotlib only): three sections and a 3/4 view.

Called by assembly_check.py --png; output goes to hardware/enclosure-3d/preview/.
All geometry comes from the saved STLs (mounted frame) plus the simple assembly bodies.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "preview")

COL = {"host": "#2a9d8f", "c6": "#e9c46a", "bme": "#e76f51", "ant": "#9b5de5", "plug": "#8d99ae"}


def slice_tris(tris, axis, val):
    """Intersection segments of the triangle soup with the plane coord[axis] = val -> (n, 2, 3)."""
    val = val + 1e-4
    d = tris[:, :, axis] - val
    pts = {}
    for i, j in ((0, 1), (1, 2), (2, 0)):
        cross = (d[:, i] > 0) != (d[:, j] > 0)
        idx = np.where(cross)[0]
        t = d[idx, i] / (d[idx, i] - d[idx, j])
        p = tris[idx, i] + t[:, None] * (tris[idx, j] - tris[idx, i])
        for k, q in zip(idx.tolist(), p):
            pts.setdefault(k, []).append(q)
    return np.array([v[:2] for v in pts.values() if len(v) >= 2])


def _proj(segs, a, b):
    return segs[:, :, [a, b]]


def _rect(ax, lo, hi, a, b, color, alpha=0.55):
    ax.add_patch(Rectangle((lo[a], lo[b]), hi[a] - lo[a], hi[b] - lo[b], facecolor=color, edgecolor="k", lw=0.4, alpha=alpha))


def _color(name):
    for k, c in COL.items():
        if name.startswith(k):
            return c
    return "#999999"


def render_all(P, surf, tb, tl, B, paths, info, suffix, mode):
    os.makedirs(OUT, exist_ok=True)
    allt = np.concatenate([tb, tl])
    tag = f"{P.rev}{suffix}"
    cable_col = lambda n: "#d00000" if n.startswith("ufl") else "#0077b6"   # noqa: E731

    # --- 1) front view section (plane through the PCB front face); X runs right-to-left as seen from the front
    fig, ax = plt.subplots(figsize=(9.5, 10))
    s = slice_tris(tb, 1, P.ym_f + 0.5)
    ax.add_collection(LineCollection(_proj(s, 0, 2), colors="k", linewidths=0.8))
    for n, (lo, hi) in B.items():
        if n.endswith(".pcb") or n.startswith("ant"):
            _rect(ax, lo, hi, 0, 2, _color(n))
    for n, (lo, hi) in B.items():
        if n.endswith(".usbc"):
            _rect(ax, lo, hi, 0, 2, "#444444", 0.8)
    for n, (pts, r) in paths.items():
        ax.plot(pts[:, 0], pts[:, 2], "-", lw=1.6, color=cable_col(n))
    ax.set_xlim(P.Lo + 3, -3)
    ax.set_ylim(-3, P.Ho + 3)
    ax.set_aspect("equal")
    ax.set_title(f"Front view, section at depth y = {P.ym_f + 0.5:.1f} mm, lid removed (X runs right-to-left)\n"
                 "teal = host S3, yellow = C6, orange = BME680, violet = antennas, red = U.FL cables, blue = BME wires", fontsize=9)
    ax.text(P.Lo / 2, (P.z_p0 + P.z_p1) / 2, "baffle (double wall, 3 mm air gap)", ha="center", va="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"section_front_{tag}.png"), dpi=110)
    plt.close(fig)

    # --- 2) side sections (Y horizontal, Z vertical)
    fig, axs = plt.subplots(1, 2, figsize=(11, 9), sharey=True)
    for ax, xcut, label in ((axs[0], (P.xh0 + P.xh1) / 2, "through the host S3 (upside down: USB opening in the bottom wall)"),
                            (axs[1], (P.bme_x0 + P.bme_x1) / 2, "through the BME680 board, baffle and the C6")):
        s = slice_tris(allt, 0, xcut)
        ax.add_collection(LineCollection(_proj(s, 1, 2), colors="k", linewidths=0.8))
        for n, (lo, hi) in B.items():
            if lo[0] <= xcut <= hi[0]:
                _rect(ax, lo, hi, 1, 2, _color(n))
        for n, (pts, r) in paths.items():
            ax.plot(pts[:, 1], pts[:, 2], ".-", lw=1, ms=3, color=cable_col(n))
        ax.set_xlim(-2, P.Do + 4)
        ax.set_ylim(-3, P.Ho + 6)
        ax.set_aspect("equal")
        ax.set_title(f"Side section x = {xcut:.1f} mm\n{label}", fontsize=9)
        ax.set_xlabel("Y (0 = wall, lid at the right)")
    axs[0].set_ylabel("Z (up)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"section_side_{tag}.png"), dpi=110)
    plt.close(fig)

    # --- 3) plan sections (X horizontal, Y vertical)
    fig, axs = plt.subplots(3, 1, figsize=(11, 11))
    for ax, zcut, label in ((axs[0], (P.zc0 + P.zc1) / 2, "C6 level (sensor / C6 column on the left of the picture, host column on the right)"),
                            (axs[1], (P.bme_z0 + P.bme_z1) / 2, "sensor level (BME680 board) and host"),
                            (axs[2], (P.zh0 + P.zh1) / 2 - 4, "host level (USB-C end down)")):
        s_ = slice_tris(allt, 2, zcut)
        ax.add_collection(LineCollection(_proj(s_, 0, 1), colors="k", linewidths=0.8))
        for n, (lo, hi) in B.items():
            if lo[2] <= zcut <= hi[2]:
                _rect(ax, lo, hi, 0, 1, _color(n))
        ax.set_xlim(P.Lo + 3, -3)
        ax.set_ylim(-2, P.Do + 3)
        ax.set_aspect("equal")
        ax.set_title(f"Plan section z = {zcut:.1f} mm, {label} (front-view orientation, wall at the bottom)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"section_plan_{tag}.png"), dpi=110)
    plt.close(fig)

    # --- 4) 3/4 view, lid exploded forward
    def shade(t, base):
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        light = np.array([-0.4, 0.8, 0.5])
        light /= np.linalg.norm(light)
        k = 0.45 + 0.55 * np.clip(n @ light, 0, 1)
        return np.clip(np.outer(k, base), 0, 1)

    fig = plt.figure(figsize=(15, 8))
    for k, (title, with_lid) in enumerate((("Base (semi-transparent) with boards, antennas, cables, lid removed", False),
                                            ("Lid seen from the front (louvres, engraved name); the six hooks stand on its inner face", True))):
        if with_lid:                                   # 58k triangles (engraved text): matplotlib's painter sort fails, so the lid is rendered with pyvista
            import pyvista as pv
            faces = np.hstack([np.full((len(tl), 1), 3), np.arange(len(tl) * 3).reshape(-1, 3)]).ravel()
            mesh = pv.PolyData(tl.reshape(-1, 3).astype(float), faces)
            pl = pv.Plotter(off_screen=True, window_size=(1000, 900))
            pl.set_background("white")
            pl.add_mesh(mesh, color="#d9e0ee", smooth_shading=False, specular=0.2)
            pl.camera_position = [(P.Lo / 2 + 70, P.Do + 150, P.Ho / 2 + 75), (P.Lo / 2, P.Do / 2, P.Ho / 2), (0, 0, 1)]
            img = pl.screenshot(return_img=True)
            pl.close()
            ax = fig.add_subplot(1, 2, k + 1)
            ax.imshow(img)
            ax.axis("off")
            ax.set_title(title, fontsize=9)
            continue
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        fc = np.concatenate([shade(tb, np.array([0.93, 0.93, 0.95])), np.full((len(tb), 1), 0.28)], axis=1)   # x-ray base
        ax.add_collection3d(Poly3DCollection(tb, facecolors=fc, edgecolors="none"))
        for n, (lo, hi) in B.items():
            if n.endswith(".plug") or n.endswith(".parts"):
                continue
            x0, y0, z0 = lo
            x1, y1, z1 = hi
            v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
            faces_ = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]]
            ax.add_collection3d(Poly3DCollection([v[f] for f in faces_], facecolors=_color(n), edgecolors="k", linewidths=0.2, alpha=0.95))
        for n, (pts, r) in paths.items():
            ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], lw=2, color=cable_col(n))
        ax.set_xlim(P.Lo, 0)
        ax.set_ylim(0, P.Do)
        ax.set_zlim(0, P.Ho)
        ax.set_box_aspect((P.Lo, P.Do * 2.0, P.Ho))
        ax.view_init(elev=24, azim=120)
        ax.set_title(title, fontsize=9)
    fig.suptitle("Enclosure rev03 CONCEPT DRAFT, mounted orientation (Z up, wall at Y = 0)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"view_3d_{tag}.png"), dpi=110)
    plt.close(fig)
    print(f"preview PNGs written to {OUT}")
