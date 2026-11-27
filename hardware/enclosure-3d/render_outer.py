"""Outer-look renders of the CURRENT STLs (base + lid, mounted frame) with pyvista, off-screen.

    py -3.12 hardware/enclosure-3d/render_outer.py            # writes preview/outer_*.png

Why it exists: the section previews of render_preview.py are technical drawings; this shows what the case looks like from the outside,
from the front (lid), from the back (the face against the wall) and with the lid lifted off. Not a photo-realistic render, and it
contains nothing that the STLs do not contain. The conversion print frame -> mounted frame is the one of assembly_check.py
(base: (X, Zp, Ho - Y); lid prints OUTER face down: (X, Do - Zp, Y)). Run it right after build.py:
params.scad and the STLs must be in step, otherwise the placement of the lid is wrong (the printed bounding box tells).
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mesh_check  # noqa: E402
import scadparams  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "preview")


def newest(pattern):
    files = sorted(glob.glob(os.path.join(HERE, "stl", pattern)))
    if not files:
        raise SystemExit("no STL matches stl/%s - run build.py first" % pattern)
    return files[-1]


def main():
    import pyvista as pv

    params = scadparams.load(os.path.join(HERE, "params.scad"))

    def val(name):
        return float(params[name])

    ho, hbase_y, do = val("Ho"), val("Hbase_y"), val("Do")
    rev = params["rev"]

    def surf(tris):
        v = tris.reshape(-1, 3)
        faces = np.hstack([np.full((len(tris), 1), 3), np.arange(len(v)).reshape(-1, 3)]).ravel()
        return pv.PolyData(v, faces)

    base = mesh_check.read_stl(newest("enclosure_base_rev*.stl"))
    lid = mesh_check.read_stl(newest("enclosure_lid_rev*.stl"))
    tb = np.stack([base[..., 0], base[..., 2], ho - base[..., 1]], axis=-1)
    tl = np.stack([lid[..., 0], do - lid[..., 2], lid[..., 1]], axis=-1)
    mb, ml = surf(tb), surf(tl)

    pts = np.concatenate([tb.reshape(-1, 3), tl.reshape(-1, 3)])
    lo, hi = pts.min(0), pts.max(0)
    ctr, size = (lo + hi) / 2, hi - lo
    print("mounted frame: width %.1f x height %.1f x depth %.1f mm (x, z, y)" % (size[0], size[2], size[1]))

    os.makedirs(OUT, exist_ok=True)

    def shot(name, cam_dir, lift=0.0, ortho=False):
        p = pv.Plotter(off_screen=True, window_size=(1100, 1100))
        p.set_background("white")
        p.add_mesh(mb, color="#e9e9e4", smooth_shading=False, specular=0.2)
        # tint by depth below the lid's outer face: the engraved recess (floor 0.6 mm deep) shows as a darker area, which flat lighting alone would hide
        ml.point_data["depth_tint"] = ml.points[:, 1].copy()
        p.add_mesh(ml.translate((0, lift, 0), inplace=False), scalars="depth_tint", cmap=["#7c7c76", "#dededa"], clim=(do - 0.7, do - 0.05),
                   show_scalar_bar=False, smooth_shading=False, specular=0.2)
        d = np.array(cam_dir, float)
        d /= np.linalg.norm(d)
        c2 = ctr + np.array([0.0, lift / 2.0, 0.0])                      # exploded: look at the middle of base + lifted lid, a little further away
        p.camera_position = [tuple(c2 + d * (size.max() * 2.6 + 1.6 * lift)), tuple(c2), (0, 0, 1)]
        if ortho:
            p.enable_parallel_projection()
        p.enable_anti_aliasing()
        p.screenshot(os.path.join(OUT, name))
        p.close()

    # front = the lid side (+y), seen from the viewer's left and above; back = the wall side (-y); bottom = the face the USB cable leaves through
    shot(f"outer_front_34_{rev}.png", (0.9, 1.0, 0.55))
    shot(f"outer_back_{rev}.png", (-0.5, -1.0, 0.4))
    shot(f"outer_exploded_{rev}.png", (1.0, 1.1, 0.5), lift=45.0)
    shot(f"outer_bottom_{rev}.png", (0.35, 0.55, -1.0))
    shot(f"outer_front_straight_{rev}.png", (0.0, 1.0, 0.0), ortho=True)
    print("wrote 5 PNGs to", OUT)


if __name__ == "__main__":
    main()
