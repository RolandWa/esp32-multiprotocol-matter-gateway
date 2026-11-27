"""Assembly check of the enclosure (rev03 concept): simple bodies for the real parts are placed inside the SAVED STLs
(base + lid, converted back from print orientation to the mounted frame) and tested numerically.

    py -3.12 assembly_check.py                      # default build, prints a PASS/FAIL table
    py -3.12 assembly_check.py --hdr 8.5            # 2.54 mm pin headers under the boards
    py -3.12 assembly_check.py --antenna-size A02   # re-check with the Seeed A-02 patch (37.4 x 17.5, 65 mm cable); A01 = 40 x 20, 80 mm.
                                                    # The base is re-rendered with OpenSCAD into a temporary folder (seat size changes).
    py -3.12 assembly_check.py --png                # also write preview PNGs (+ the proof of the engraved text) to preview/
    py -3.12 assembly_check.py --no-air             # skip the air-path (flood fill) analysis

ASSUMED MOUNTING: vertical, BME680 at the bottom of the C column, the HOST standing upside down so that its USB-C points down through the
bottom wall (R13); the C6 stands USB-C up behind a closed ceiling.  NO SCREWS close the case or hold a board.

What is checked (all from the saved STLs and params.scad):
  * bodies (boards, USB plug, antennas, wall screws, optional header rows) vs the enclosure by signed distance; cables / wires as swept polylines;
  * R13: the one USB opening faces down, lead-in, cable-tie anchor, end arms against a tug, no other USB opening, top face closed;
  * R8/R10/R11: six lid hooks (engagement, capture, closing strain, release blade through the back plate) and the board clips (insertion strain, play);
  * R14: the clips are measured on the BASE alone (bench use with the lid off);
  * R15/R16: the engraved name is probed on the lid STL (inside the plate, clear of louvres, strokes >= 2 mm) and no pin holes exist;
  * visible faces: which outer faces carry openings; none is a snap feature, a second USB opening or a BOOT/RESET hole;
  * air paths (0.5 mm voxels, boards = obstacles): the sensor is upstream of the C6 and the only way up is the end gap; the host column (hotter) is
    a separate volume whose exhaust never passes the sensor; the top face is closed; keyholes / release slots / screw holes do not open an air path.
WHAT THIS DOES NOT PROVE: fit of the real boards (partly assumed dimensions), print quality, RF behaviour, heat flow, real airflow (no CFD,
no measurement).  Bodies are envelopes, not vendor 3D models.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mesh_check  # noqa: E402
import scadparams  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []

CANDIDATES = {"BOM": (39.6, 8.4, 100), "A02": (37.4, 17.5, 65), "A01": (40.0, 20.0, 80)}


def record(name: str, ok: bool, info: str):
    RESULTS.append((name, ok, info))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {info}")


# ----------------------------------------------------------------------------- geometry helpers
def box_samples(lo, hi, step=0.5, inset=0.0):
    lo = np.asarray(lo, float) + inset
    hi = np.asarray(hi, float) - inset
    axes = [np.linspace(lo[i], hi[i], max(2, int(math.ceil((hi[i] - lo[i]) / step)) + 1)) for i in range(3)]
    return np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)


def cyl_y_samples(cx, cz, y0, y1, r, step=0.5, r1=None):
    r1 = r if r1 is None else r1
    ys = np.linspace(y0, y1, max(2, int(math.ceil(abs(y1 - y0) / step)) + 1))
    pts = []
    for y in ys:
        rr = r + (r1 - r) * (y - y0) / (y1 - y0) if y1 != y0 else r
        for ring in np.linspace(0, rr, max(2, int(math.ceil(rr / step)) + 1)):
            n = max(1, int(round(2 * math.pi * ring / step))) if ring > 0 else 1
            a = np.linspace(0, 2 * math.pi, n, endpoint=False)
            pts.append(np.stack([cx + ring * np.cos(a), np.full(n, y), cz + ring * np.sin(a)], axis=1))
    return np.concatenate(pts)


def hex_y_samples(cx, cz, y0, y1, af, step=0.4):
    """Hexagonal prism along Y (vertices on the X axis, like the pocket in enclosure.scad), across flats = af."""
    rc = af / math.cos(math.radians(30)) / 2
    pts = []
    for x in np.arange(-rc, rc + 1e-9, step):
        for z in np.arange(-af / 2, af / 2 + 1e-9, step):
            if abs(z) <= af / 2 and abs(x) * math.cos(math.radians(30)) + abs(z) * math.sin(math.radians(30)) <= af / 2 + 1e-9:
                pts.append((cx + x, cz + z))
    ys = np.linspace(y0, y1, max(2, int(math.ceil((y1 - y0) / step)) + 1))
    return np.array([[px, y, pz] for y in ys for px, pz in pts])


def polyline_samples(pts, step=0.4):
    pts = np.asarray(pts, float)
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def polyline_length(pts):
    return float(np.linalg.norm(np.diff(np.asarray(pts, float), axis=0), axis=1).sum())


def bend_margin(pts, rmin):
    """Smallest (segment length - tangent lengths) for fillets of radius rmin; >= 0 = every bend can have R >= rmin."""
    pts = np.asarray(pts, float)
    t = [0.0]
    for i in range(1, len(pts) - 1):
        u, v = pts[i] - pts[i - 1], pts[i + 1] - pts[i]
        c = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
        t.append(rmin * math.tan(math.acos(max(-1.0, min(1.0, c))) / 2))
    t.append(0.0)
    return min(np.linalg.norm(pts[i + 1] - pts[i]) - t[i] - t[i + 1] for i in range(len(pts) - 1))


def dist_points_box(pts, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return np.linalg.norm(np.maximum(np.maximum(lo - pts, pts - hi), 0), axis=1)


def boxes_overlap_volume(a, b):
    d = np.minimum(a[1], b[1]) - np.maximum(a[0], b[0])
    return float(np.prod(d)) if np.all(d > 1e-9) else 0.0


# ----------------------------------------------------------------------------- enclosure mesh (mounted frame)
def _surf(t):
    import pyvista as pv
    v = t.reshape(-1, 3)
    return pv.PolyData(v, np.hstack([np.full((len(t), 1), 3), np.arange(len(v)).reshape(-1, 3)]).ravel())


def load_enclosure(P, base_path, lid_path):
    import pyvista as pv
    base = mesh_check.read_stl(base_path)
    lid = mesh_check.read_stl(lid_path)

    def conv_base(t):
        return np.stack([t[..., 0], t[..., 2], P.Ho - t[..., 1]], axis=-1)

    def conv_lid(t):                      # lid prints OUTER face down: print z = Do - Y, print y = Z
        return np.stack([t[..., 0], P.Do - t[..., 2], t[..., 1]], axis=-1)

    tb, tl = conv_base(base), conv_lid(lid)
    surf = _surf(np.concatenate([tb, tl]))
    pv.set_new_attribute(surf, "shells", (_surf(tb), _surf(tl)))
    return surf, tb, tl


def signed_distance(surf, pts):
    import pyvista as pv
    return np.asarray(pv.PolyData(np.asarray(pts, float)).compute_implicit_distance(surf, inplace=False)["implicit_distance"])


def in_solid(surf, pts):
    """True where a point is inside printed material (base OR lid; tested per shell because the two touch on a plane)."""
    import pyvista as pv
    mask = np.zeros(len(pts), dtype=bool)
    for shell in surf.shells:
        sel = pv.PolyData(np.asarray(pts, float)).select_interior_points(shell, check_surface=False)
        mask |= np.asarray(sel[list(sel.point_data.keys())[0]]).astype(bool)
    return mask


def ray_hits(surf, p0, p1):
    pts, _ = surf.ray_trace(p0, p1)
    return np.asarray(pts)


def inside_points(shell, lo, hi, step):
    import pyvista as pv
    g = box_samples(lo, hi, step)
    sel = pv.PolyData(g).select_interior_points(shell, check_surface=False)
    key = list(sel.point_data.keys())[0]
    return g[np.asarray(sel[key]).astype(bool)]


# ----------------------------------------------------------------------------- bodies
def build_bodies(P, hdr):
    """Boxes (lo, hi) in the mounted frame.  Host: standing upside down (USB-C end DOWN), C6: USB-C end up (unused), BME680 at the bottom of the C column."""
    B = {}
    y_usb = P.ym_f + P.usb_h / 2
    info = {"y_usb": y_usb}
    boards = {"host": (P.xh0, P.zh0, P.zh1), "c6": (P.xc0, P.zc0, P.zc1)}
    for name, (x0, z0, z1) in boards.items():
        B[f"{name}.pcb"] = (np.array([x0, P.ym_b, z0]), np.array([x0 + P.xiao_w, P.ym_f, z1]))
        B[f"{name}.parts"] = (np.array([x0, P.ym_f, z0]), np.array([x0 + P.xiao_w, P.ym_top, z1]))
        xu = x0 + P.xiao_w / 2
        if name == "host":                                         # USB-C at the lower edge, plug comes from below through the bottom wall
            B["host.usbc"] = (np.array([xu - P.usb_w / 2, P.ym_f, z0 - P.usb_over]), np.array([xu + P.usb_w / 2, P.ym_f + P.usb_h, z0]))
            zt = z0 - P.usb_over - 0.5
            B["host.plug"] = (np.array([xu - 6.2, y_usb - 3.25, zt - 25]), np.array([xu + 6.2, y_usb + 3.25, zt]))
        else:                                                      # C6: receptacle at the top edge, NO opening, NO plug
            B["c6.usbc"] = (np.array([xu - P.usb_w / 2, P.ym_f, z1]), np.array([xu + P.usb_w / 2, P.ym_f + P.usb_h, z1 + P.usb_over]))
        if hdr > 0:
            zc = (z0 + z1) / 2
            for side, xr in (("L", x0 + P.xiao_w - 0.84), ("R", x0 + 0.84)):
                B[f"{name}.hdr{side}"] = (np.array([xr - 1.27, P.ym_b - hdr, zc - 8.89]), np.array([xr + 1.27, P.ym_b, zc + 8.89]))
    B["bme.pcb"] = (np.array([P.bme_x0, P.bme_yb, P.bme_z0]), np.array([P.bme_x1, P.bme_yb + P.bme_pcb_t, P.bme_z1]))
    B["bme.parts"] = (np.array([P.bme_x0, P.bme_yb + P.bme_pcb_t, P.bme_z0]),
                      np.array([P.bme_x1, P.bme_yb + P.bme_pcb_t + P.bme_top_h, P.bme_z1]))
    d = P.ant_seat_d
    xl = (P.t_end - d + 0.05, P.t_end - d + 0.05 + P.ant_t)             # patch on the seat floor, wall at X = 0 (host side)
    xr = (P.Lo - xl[1], P.Lo - xl[0])                                    # wall at X = Lo (sensor / C6 side)
    for nm, (a, b) in (("ant.left", xl), ("ant.right", xr)):
        B[nm] = (np.array([a, P.ant_y - P.ant_w / 2, P.ant_z0]), np.array([b, P.ant_y + P.ant_w / 2, P.ant_z1]))
    info["ant_x_left"], info["ant_x_right"] = xl, xr
    return B, info


def cable_paths(P, info):
    """Waypoints (mounted frame): the two U.FL cables, the BME wires (sensor -> divider slot 1 -> host 3V3/GND pads at the USB end) and the
    host <-> C6 wires (host 5 V pad -> up the host column -> divider slot 2 -> C6 pads)."""
    y_c = P.ym_f + 1.5
    r = 0.7
    fz = P.ant_z0 + 1.0
    paths = {}
    # host: standing upside down -> its U.FL is at the TOP edge, near the small-X wall; the cable climbs above the board, runs to the wall, drops to the patch feed
    xs = P.xh0 + P.xiao_ufl_u
    zs = P.zh1 - P.xiao_ufl_v
    z_run_h = P.zh1 + 7.5
    fx = info["ant_x_left"][1] + r
    paths["ufl.host"] = (np.array([[xs, y_c, zs], [xs, y_c, z_run_h], [P.t_end + 4.5, P.ant_y, z_run_h], [fx, P.ant_y, fz]], float), r)
    # C6: USB-C up -> its U.FL is at the lower edge near the large-X wall.  The cable rises over the C6's lower-right corner clips (in front of
    # the arms, y up to 26 mm), then runs down the end gap (beside the baffle's end cap) to the patch feed: bends >= coax_min_bend.
    xs = P.xc1 - P.xiao_ufl_u
    zs = P.zc0 + P.xiao_ufl_v
    fx = info["ant_x_right"][0] - r
    paths["ufl.c6"] = (np.array([[xs, y_c, zs], [xs + 3.8, 26.2, zs + 1.3], [xs + 11.3, 23.5, 41.5], [P.Lo - P.t_end - 2.3, P.ant_y, 33.0], [fx, P.ant_y, fz]], float), r)
    # BME wires through divider slot 1
    zmid = P.div_s1_z
    a = [P.bme_x0 - 0.5, P.bme_yb + 0.8, zmid]
    b = [P.x_div, 10.5, zmid]
    c = [P.xh1 + 3.5, 10.5, zmid - 2]
    d = [P.xh1 + 0.4, P.ym_b + 0.5, P.zh0 + 6.0]
    paths["wires.bme"] = (np.array([a, b, c, d], float), 1.25)
    # host <-> C6 (5 V, GND, UART, EN, BOOT): one representative bundle
    a = [P.xh1 + 0.4, P.ym_b + 0.5, P.zh0 + 9.0]
    b = [P.xh1 + 4.0, 11.0, P.zh0 + 13.0]
    c = [P.xh1 + 4.0, 11.0, P.div_s2_z - 5.0]                 # up the free strip between the host's clip arms and the divider
    d = [P.x_div, 11.0, P.div_s2_z]                           # through divider slot 2
    e = [P.xc0 - 0.4, P.ym_b + 0.5, P.zc0 + 6.0]
    paths["wires.uart"] = (np.array([a, b, c, d, e], float), 1.25)
    return paths


# ----------------------------------------------------------------------------- main analysis
def run(argv):
    hdr = float(argv[argv.index("--hdr") + 1]) if "--hdr" in argv else 0.0
    cand = argv[argv.index("--antenna-size") + 1].upper() if "--antenna-size" in argv else "BOM"
    over = {"hdr_h": hdr}
    if cand != "BOM":
        over.update({"ant_len": CANDIDATES[cand][0], "ant_w": CANDIDATES[cand][1], "ant_cable": CANDIDATES[cand][2]})
    P = scadparams.P(overrides=over)
    stl_dir = os.path.join(HERE, "stl")
    base_path = os.path.join(stl_dir, f"enclosure_base_{P.rev}.stl")
    if cand != "BOM":                                           # re-render the base with the other seat size
        import build
        tmp = tempfile.mkdtemp(prefix="encl_ant_")
        base_path = os.path.join(tmp, "base.stl")
        build.render(build.find_openscad(), "base", base_path,
                     ["-D", f"ant_len={over['ant_len']}", "-D", f"ant_w={over['ant_w']}", "-D", f"ant_cable={over['ant_cable']}"])
    print(f"== assembly check {P.rev}: antenna {cand} ({P.ant_len} x {P.ant_w} mm, cable {P.ant_cable} mm), headers {hdr} mm")
    surf, tb, tl = load_enclosure(P, base_path, os.path.join(stl_dir, f"enclosure_lid_{P.rev}.stl"))
    B, info = build_bodies(P, hdr)
    paths = cable_paths(P, info)

    allv = np.concatenate([tb.reshape(-1, 3), tl.reshape(-1, 3)])
    ext = allv.max(axis=0) - allv.min(axis=0)
    record("outer size", True, f"{ext[0]:.1f} (X) x {ext[2]:.1f} (Z, height) x {ext[1]:.1f} (Y, depth) mm, mounted")
    cx_l, cx_r = sum(info["ant_x_left"]) / 2, sum(info["ant_x_right"]) / 2
    sep = cx_r - cx_l
    record("antenna centre distance", sep >= P.min_ant_sep, f"{sep:.1f} mm (owner's floor {P.min_ant_sep}; the 100 mm target is relaxed)")
    record("params consistent with STL", abs(ext[0] - P.Lo) < 0.05 and abs(ext[2] - P.Ho) < 0.05 and abs(ext[1] - P.Do) < 0.05,
           f"STL {ext[0]:.2f}/{ext[2]:.2f}/{ext[1]:.2f} vs params {P.Lo:.2f}/{P.Ho:.2f}/{P.Do:.2f}")

    # --- bodies vs enclosure
    for name, (lo, hi) in B.items():
        inset = 0.02 if (name.endswith(".pcb") or name.startswith("bme")) else 0.0
        pts_b = box_samples(lo, hi, 0.5, inset)
        if name.endswith(".parts"):                                   # corner squares under the clip lips carry no tall parts (ASSUMED: S3 buttons / U.FL are >= 1.5 mm from the edge)
            keepx = P.clip_ov + 0.3
            kz = P.arm_z + 0.3
            m = ((np.minimum(pts_b[:, 0] - lo[0], hi[0] - pts_b[:, 0]) < keepx) &
                 (np.minimum(pts_b[:, 2] - lo[2], hi[2] - pts_b[:, 2]) < kz))
            pts_b = pts_b[~m]
        d = signed_distance(surf, pts_b)
        inside = int((d < -1e-6).sum())
        by_design = name.endswith(".pcb") or name.startswith("bme.pcb") or name.startswith("ant")
        record(f"body '{name}' vs enclosure", inside == 0, f"min clearance {d.min():.2f} mm, intersecting samples {inside} (~{inside * 0.125:.2f} mm3)"
               + ("  [rests on supports / in seat by design]" if by_design else ""))
    names = [n for n in B if not n.startswith("ant")]
    coll = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.split(".")[0] == b.split(".")[0] and ({a.split(".")[1], b.split(".")[1]} <= {"pcb", "parts", "usbc", "plug", "hdrL", "hdrR"}):
                continue
            v = boxes_overlap_volume(B[a], B[b])
            if v > 0:
                coll.append((a, b, v))
    record("body vs body (different modules / boards)", not coll, "no overlap" if not coll else str(coll))

    # --- wall screws (the only screws: they fix the case to the wall, not the lid or the boards)
    metal = []
    kw = 9.0
    for kx, kz in ((P.key_xc, P.key_zh), (P.key_xc2, P.key_zh2)):
        zl = kz + P.key_slot_l                                   # loaded position: top of the slot
        shank = cyl_y_samples(kx, zl, P.t_back - 4, P.t_back + 0.0, 1.9)
        head = cyl_y_samples(kx, zl, P.t_back + 0.02, P.t_back + P.key_head_t, (P.key_head_d - 0.4) / 2)
        kw = min(kw, float(signed_distance(surf, np.concatenate([shank, head])).min()))
        metal += [shank, head]
    record("wall screws in the two keyhole chambers (loaded position)", kw >= 0, f"min clearance {kw:.2f} mm (head {P.key_head_d - 0.4:.1f} mm x {P.key_head_t} mm in a sealed chamber)")
    sw = 9.0
    for (sx_, sz_) in ((P.sh_x, P.sh_z), (P.sh_x2, P.sh_z2)):
        cs2 = (P.sh_head_d - P.sh_d) / 2 / math.tan(math.radians(P.sh_half))
        shank = cyl_y_samples(sx_, sz_, P.sh_skin + 0.05, P.t_back - cs2, 2.0)
        head = cyl_y_samples(sx_, sz_, P.t_back - cs2, P.t_back - 0.05, 2.0, r1=P.sh_head_d / 2 - 0.1)
        sw = min(sw, float(signed_distance(surf, np.concatenate([shank, head])).min()))
        metal += [shank, head]
    record("countersunk wall screws through the back plate (2)", sw >= 0, f"min clearance {sw:.2f} mm (they pierce the {P.sh_skin} mm skin; boards are fitted AFTER screwing the case to the wall)")

    # --- cables
    for name, (pts, r) in paths.items():
        rmin = P.coax_min_bend if name.startswith("ufl") else P.wire_min_bend
        L = polyline_length(pts)
        samp = polyline_samples(pts, 0.4)
        chk = samp[int(2.0 / 0.4):] if name.startswith("ufl") else samp
        d = signed_distance(surf, chk) - r
        bd = 9.0
        for bn, (lo, hi) in B.items():
            if bn.startswith("ant") or bn.endswith(".plug") or bn.endswith(".usbc"):
                continue
            if (name == "ufl.host" and bn.startswith("host")) or (name == "ufl.c6" and bn.startswith("c6")):
                continue
            if name.startswith("wires") and bn.startswith(("host", "bme", "c6")):
                continue                                  # wires attach to those boards
            bd = min(bd, float(dist_points_box(chk, lo, hi).min()) - r)
        margin = bend_margin(pts, rmin)
        limit = P.ant_cable - 5 if name.startswith("ufl") else 9e9
        ok = bool(d.min() >= 0 and bd >= 0 and margin >= 0 and L <= limit)
        record(f"path '{name}'", ok, f"length {L:.0f} mm" + (f" (cable {P.ant_cable:.0f}, 5 mm kept for plug/slack)" if name.startswith("ufl") else "")
               + f", min clearance to enclosure {d.min():.2f} mm, to other boards {('>= 9' if bd >= 9 else format(bd, '.2f'))} mm, bend R>={rmin} feasible by {margin:.1f} mm")

    # --- wire space behind the boards (in front of the keyhole chambers), divider slots, antennas
    for nm, (x0_, z0_, z1_) in (("host", (P.xh0 - 2.5, P.zh0 + 2.5, P.zh1 - 2.5)), ("C6", (P.xc0 - 3.5, P.zc0 + 2.5, P.zc1 - 2.5))):
        w_ = P.xiao_w + 6.0
        lo_ = np.array([x0_, 10.0, z0_])
        hi_ = np.array([x0_ + w_, P.ym_b - 0.5, z1_])
        dd_ = signed_distance(surf, box_samples(lo_, hi_, 0.6))
        record(f"wire space behind the {nm} board", int((dd_ < 0).sum()) == 0,
               f"{hi_[0] - lo_[0]:.0f} x {hi_[1] - lo_[1]:.1f} x {hi_[2] - lo_[2]:.0f} mm in front of the keyhole chambers, printed material inside: {int((dd_ < 0).sum())} samples")
    for nm, zc_ in (("1 (sensor -> host 3V3/GND)", P.div_s1_z), ("2 (host <-> C6)", P.div_s2_z)):
        hits = ray_hits(surf, [P.x_div - 3, P.t_back + 7.0, zc_], [P.x_div + 3, P.t_back + 7.0, zc_])
        record(f"divider slot {nm} open", len(hits) == 0, f"ray through the slot centre hits {len(hits)} surfaces")
    for side in (0, 1):
        thick = []
        for z in np.linspace(P.ant_z0, P.ant_z1, 9):
            for dy in (-3.0, 0.0, 3.0):
                x_in, x_out = (-1, P.Lo / 2) if side == 0 else (P.Lo + 1, P.Lo / 2)
                h = ray_hits(surf, [x_in, P.ant_y + dy, z], [x_out, P.ant_y + dy, z])
                if len(h) >= 2:
                    thick.append(abs(float(h[1][0] - h[0][0])))
        wall = "host side" if side == 0 else "sensor/C6 side"
        if thick:
            record(f"end-wall thickness behind the antenna seat ({wall})", min(thick) >= 1.5, f"{min(thick):.2f} .. {max(thick):.2f} mm (owner 1.5-2 mm)")
        fl = np.array([P.t_end + 0.05, P.ant_y - P.ant_flat_w / 2, P.ant_z0 - (P.ant_flat_l - P.ant_len) / 2])
        fh = np.array([P.t_end + 6.0, P.ant_y + P.ant_flat_w / 2, P.ant_z1 + (P.ant_flat_l - P.ant_len) / 2])
        if side == 1:
            fl, fh = np.array([P.Lo - fh[0], fl[1], fl[2]]), np.array([P.Lo - fl[0], fh[1], fh[2]])
        fz = signed_distance(surf, box_samples(fl, fh, 0.6))
        record(f"antenna flat zone {P.ant_flat_l:.0f} x {P.ant_flat_w:.0f} mm free of ribs/bosses ({wall}, 6 mm deep)", int((fz < 0).sum()) == 0,
               f"printed material in the zone: {int((fz < 0).sum())} samples (zone z {fl[2]:.1f}..{fh[2]:.1f}, y {fl[1]:.1f}..{fh[1]:.1f}; the seat itself is outside this check)")
    mets = [box_samples(*B[n], 1.0) for n in B if n.startswith(("host.pcb", "host.parts", "c6.pcb", "c6.parts", "bme")) or "hdr" in n] + metal
    mall = np.concatenate(mets)
    for nm in ("ant.left", "ant.right"):
        dmin = float(dist_points_box(mall, *B[nm]).min())
        record(f"metal keep-out around {nm}", dmin >= P.ant_keep_m - 0.05,
               f"nearest metal (board PCB, header, wall-screw head) {dmin:.1f} mm (rule of thumb {P.ant_keep_m} mm, ASSUMED; no RF measurement)")

    # --- lid gap
    hl = ray_hits(surf.shells[1], [P.x_div + 7, 0.0, P.zc0 + 2], [P.x_div + 7, P.Do + 1, P.zc0 + 2])
    lid_y0 = float(hl[0][1]) if len(hl) else float(tl[..., 1].min())
    record("lid to tallest component", lid_y0 - P.ym_top >= 2.0, f"{lid_y0 - P.ym_top:.2f} mm (lid inner face y={lid_y0:.2f}, components up to y={P.ym_top:.2f})")

    # --- the USB-C opening, snap hooks, board clips, visible faces, engraved name
    usb_checks(P, surf, B, info)
    snap_checks(P, surf)
    clip_checks(P, surf, B)
    visible_faces(P, surf)
    text_checks(P, surf, "--png" in argv)

    # --- tape recess, screw-hole skin
    if P.tape_on:
        res = []
        for i in range(P.tape_n):
            xc = P.tape_xc + (i - (P.tape_n - 1) / 2) * (P.tape_w + P.tape_rib)
            h = ray_hits(surf, [xc, -1, 18.0], [xc, P.Do + 1, 18.0])
            res.append(float(h[0][1]) if len(h) else -1)
        hr = ray_hits(surf, [P.tape_xc, -1, 18.0], [P.tape_xc, P.Do + 1, 18.0])
        record("tape recess on the back (2 cells + rib)", all(abs(v - P.tape_d) < 0.02 for v in res) and len(hr) > 0 and abs(float(hr[0][1])) < 0.02,
               f"recess floor at y={res} (design {P.tape_d}), rib in the middle at y={float(hr[0][1]) if len(hr) else None:.2f}; cell width {P.tape_w} mm <= bridge limit {P.max_bridge}; plate left under the recess {P.t_back - P.tape_d:.1f} mm")
    # --- R17: both keyholes on one horizontal line, drilling marks (dimension line, extension lines, text) recessed in the back face
    same_line = abs(P.key_zh - P.key_zh2) < 1e-6 and abs((P.key_xc2 - P.key_xc) - P.key_dx) < 1e-6 and abs((P.key_xc + P.key_xc2) / 2 - P.Lo / 2) < 1e-6
    try:
        txt_num = float(str(P.dim_txt).split()[0])
    except ValueError:
        txt_num = -1.0
    record("R17 the two keyholes stand on ONE horizontal line, symmetric about the centre, spacing = the printed number",
           same_line and abs(txt_num - P.key_dx) < 1e-6, f"holes at z={P.key_zh:.2f} / {P.key_zh2:.2f}, x={P.key_xc:.2f} / {P.key_xc2:.2f} (spacing {P.key_xc2 - P.key_xc:.2f} mm), printed '{P.dim_txt}'")
    if P.dim_on:
        def first_y(x, z):
            h = ray_hits(surf, [x, -1, z], [x, P.Do + 1, z])
            return float(h[0][1]) if len(h) else -9.0
        line_pts = [(P.Lo / 2 + dx, P.dim_z) for dx in (-15.0, 15.0)] + [(x, P.dim_z) for x in (P.key_xc, P.key_xc2)]
        ext_pts = [(x, (P.dim_ext_z1 + P.dim_ext_z2) / 2 + 1.0) for x in (P.key_xc, P.key_xc2)]
        ok_lines = all(abs(first_y(x, z) - P.dim_depth) < 0.02 for x, z in line_pts + ext_pts)
        z0, z1 = P.dim_txt_z, P.dim_txt_z + 0.72 * P.dim_txt_size
        gx = np.arange(P.Lo / 2 - 16.0, P.Lo / 2 + 16.0, 0.4)
        gz = np.arange(z0, z1, 0.4)
        n_rec = sum(1 for x in gx for z in gz if abs(first_y(x, z) - P.dim_depth) < 0.02)
        record("R17 drilling marks recessed in the back face: dimension line, two extension lines, and the distance as text",
               ok_lines and n_rec > 40, f"line/extension probes at recess floor y={P.dim_depth} mm: {ok_lines}; text area: {n_rec} probe points in recess (0.4 mm grid), "
               f"line {P.dim_w} mm wide, {P.dim_depth} mm deep; tape cells end at z={P.tape_z1} below the marks (line z={P.dim_z})")
    if P.sh_on:
        for (sx_, sz_) in ((P.sh_x, P.sh_z), (P.sh_x2, P.sh_z2)):
            h = ray_hits(surf, [sx_, -1, sz_], [sx_, P.Do + 1, sz_])
            record("screw hole closed by a skin at the back (no air path before use)", len(h) > 1 and abs(float(h[0][1])) < 0.02 and abs(float(h[1][1]) - P.sh_skin) < 0.02,
                   f"back face closed, skin {float(h[1][1]):.2f} mm thick (design {P.sh_skin})" if len(h) > 1 else "ray found no skin")

    if "--no-air" not in argv:
        air_analysis(P, surf, B, argv)

    bad = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(bad)} / {len(RESULTS)} checks passed")
    if "--png" in argv:
        import render_preview
        render_preview.render_all(P, surf, tb, tl, B, paths, info, "", 0)
    return 1 if bad else 0


def usb_checks(P, surf, B, info):
    """R13: ONE USB-C opening, host, bottom wall, facing down, lead-in, cable anchor; no other USB opening anywhere."""
    xh = P.xh0 + P.xiao_w / 2
    y_usb = info["y_usb"]
    hits = ray_hits(surf, [xh, y_usb, -8.0], [xh, y_usb, P.zh0 - P.usb_over - 0.2])
    record("R13 the host's USB-C opening is in the BOTTOM wall: a straight path from below to the receptacle is free", len(hits) == 0,
           f"vertical ray from 8 mm below the case to the receptacle front hits {len(hits)} surfaces; receptacle front at z={P.zh0 - P.usb_over:.1f} (bottom wall inner face z={P.z_s0})")

    def width(z):
        h = ray_hits(surf, [xh - 25, y_usb, z], [xh + 25, y_usb, z])
        xs_ = sorted(float(p[0]) for p in h)
        left = [x for x in xs_ if x < xh]
        right = [x for x in xs_ if x > xh]
        return (min(right) - max(left)) if left and right else float("nan")

    w_out, w_in = width(0.15), width(P.z_s0 - 0.15)
    record("R13 smooth lead-in: the opening widens towards the outside", w_out > w_in + 2 * (P.usb_lead - 0.3) and abs(w_in - P.usb_open_w) < 0.3,
           f"width {w_out:.1f} mm at the outer face, {w_in:.1f} mm through the wall (design {P.usb_open_w}, bevel {P.usb_lead} mm at 45 degrees)")
    xc6 = P.xc0 + P.xiao_w / 2
    up = ray_hits(surf, [xc6, y_usb, P.zc1], [xc6, y_usb, P.Ho + 3])
    xt = np.arange(5.0, P.Lo - 5.0, 1.0)
    ytop = np.arange(2.0, P.Do - 2.0, 1.0)
    top_open = in_solid(surf, np.array([(x, y, P.Ho - 1.0) for x in xt for y in ytop])).__invert__().sum()
    record("R13 no other USB opening: the C6's USB-C faces a closed ceiling, the top face has no opening at all", len(up) >= 1 and int(top_open) == 0,
           f"ray up from the C6 receptacle meets {len(up)} surfaces (ceiling), open probe points in the top face: {int(top_open)}")
    xs_ = [xh - P.tie_x, xh + P.tie_x]
    open_ = all(len(ray_hits(surf, [x, y_usb, -4.0], [x, y_usb, P.z_s0 + 0.5])) == 0 for x in xs_)
    outside = all(abs(x - (P.xh0 + P.xiao_w / 2)) > P.xiao_w / 2 + P.tie_w / 2 for x in xs_)
    record("R13 cable anchor: two tie slots beside the opening, outside the board outline (tie head inside the case, loop round the cable)", open_ and outside,
           f"slots {P.tie_w} x {P.tie_h} mm at x = {xs_[0]:.1f} / {xs_[1]:.1f} mm, through the bottom wall; board spans x {P.xh0:.1f}..{P.xh1:.1f}")
    stop = []
    for x in (P.xh0 + 2.0, P.xh1 - 2.0):
        h = ray_hits(surf, [x, P.ym_b + 0.8, P.zh0 - 0.02], [x, P.ym_b + 0.8, P.zh0 - 1.5])
        stop.append(float(P.zh0 - h[0][2]) if len(h) else 9.9)
    record("R13 a tug on the cable cannot pull the board down: end arms stop it", max(stop) <= P.clr + 0.1,
           f"gap between the host's USB-end edge and the end arms {stop[0]:.2f} / {stop[1]:.2f} mm (design {P.clr}); the plug unplugs before the receptacle is torn off the board (plug retention is a USB-C property, not measured here)")


# ----------------------------------------------------------------------------- snap hooks (lid), board clips, visible faces
def hook_list(P):
    return [(P.x_div + P.div_t / 2, 1, P.snap_zm), (P.x_div - P.div_t / 2, -1, P.snap_zm),
            (P.t_end, 1, P.snap_zb1), (P.t_end, 1, P.snap_zb2),
            (P.Lo - P.t_end, -1, P.snap_zb1), (P.Lo - P.t_end, -1, P.snap_zb2)]


def cantilever(E, t, L, delta, b):
    """Rectangular cantilever t x b, length L, tip deflection delta (mm): root strain (%) and tip force (N)."""
    eps = 1.5 * delta * t / L ** 2
    I = b * t ** 3 / 12.0
    return 100 * eps, 3 * E * I * delta / L ** 3


def snap_checks(P, surf):
    base_sh, lid_sh = surf.shells
    tl_ = math.tan(math.radians(P.snap_lead))
    tr_ = math.tan(math.radians(P.snap_ret))
    h, t0 = P.snap_h, P.snap_t0
    ye = P.t_back + P.snap_yb - P.snap_play + t0 - h - h / tl_ - P.snap_flat
    ytop = ye + h / tl_ + P.snap_flat + h / tr_
    L = P.Hbase_y - ytop
    clear_min, cap_hits, dreq, contact, blade_ok, skin_ok, missing = 9.0, 0, 0.0, 0, True, True, 0
    for (xf, s, z0) in hook_list(P):
        xa, xb = sorted((xf + s * (t0 - h), xf + s * (t0 + P.snap_t)))
        pts = inside_points(lid_sh, [xa, ye - 0.01, z0], [xb, P.Hbase_y - 0.3, z0 + P.snap_b], 0.2)
        if len(pts) < 100:                                     # no lid hook where the case has its bump
            missing += 1
            continue
        d = signed_distance(base_sh, pts)
        clear_min = min(clear_min, float(d.min()))
        head = pts[pts[:, 1] < ytop + 0.3]
        fine = inside_points(lid_sh, [xa, ye - 0.01, z0], [xb, ytop + 0.3, z0 + P.snap_b], 0.08)
        up = fine + np.array([0, 0.5, 0])                      # lid lifted by 0.5 mm: the hook must hit the bump
        cap_hits += int((signed_distance(base_sh, up) < 0).sum())
        found = None                                           # closing: rigid hook deflected away from the wall by delta while the lid comes down from 4 mm above
        for delta in np.arange(0.0, 2.01, 0.05):
            ok = True
            for dy in np.arange(4.0, 0.0, -0.5):
                if (signed_distance(base_sh, head + np.array([s * delta, dy, 0])) < 0).any():
                    ok = False
                    break
            if ok:
                found = float(delta)
                break
        dreq = max(dreq, found if found is not None else 9.9)
        ts = t0 - 0.5                                          # release blade 1.0 x 3.0 mm through the back-plate slot onto the lead-in ramp
        bx = sorted((xf + s * (ts - 0.5), xf + s * (ts + 0.5)))
        yb_end = ye + (found or 1.0) / tl_
        zc_ = z0 + P.snap_b / 2
        blade = box_samples([bx[0], -6.0, zc_ - 1.5], [bx[1], yb_end, zc_ + 1.5], 0.25)
        pocket = blade[blade[:, 1] < P.t_back - P.snap_slot_skin - 0.01]
        above = blade[blade[:, 1] > P.t_back + 0.01]
        blade_ok &= bool((signed_distance(base_sh, pocket) >= -1e-6).all()) and bool((signed_distance(base_sh, above) >= -1e-6).all())
        contact += int((signed_distance(lid_sh, above) < 0).sum() > 0)
        hs = ray_hits(base_sh, [xf + s * (t0 - 0.5), -1, zc_], [xf + s * (t0 - 0.5), P.t_back + 0.5, zc_])
        skin_ok &= len(hs) >= 1 and abs(float(hs[0][1]) - (P.t_back - P.snap_slot_skin)) < 0.02
    record("snap hooks x6: a lid hook stands at every bump / release slot", missing == 0, f"{6 - missing} of 6 stations have a hook in the expected place")
    record("snap hooks x6: engaged without interference", clear_min >= 0,
           f"min clearance hook - case {clear_min:.2f} mm (design play {P.snap_play} mm along Y)")
    record("snap hooks x6: lid cannot lift (hook hits the bump)", cap_hits > 0, f"{cap_hits} interfering samples (0.08 mm grid) when the lid is lifted 0.5 mm; the catch faces are 45 degrees, so a lift of {P.snap_play}+ mm engages them")
    eps_pct, force = cantilever(P.pet_E_z, P.snap_t, L, dreq, P.snap_b)
    fin = force * (P.snap_mu + tl_) / (1 - P.snap_mu * tl_)
    fout = force * (P.snap_mu + tr_) / (1 - P.snap_mu * tr_)
    record("snap hooks x6: closing deflection and strain within the design limit", dreq < 9 and eps_pct <= P.snap_eps_max,
           f"hook must deflect {dreq:.2f} mm (swept through the real STL), beam {P.snap_t} x {P.snap_b} x {L:.1f} mm -> strain {eps_pct:.2f} % "
           f"(limit {P.snap_eps_max} %, Z break {P.pet_eb_z} %), stress {P.pet_E_z * eps_pct / 100:.0f} MPa = {100 * P.pet_E_z * eps_pct / 100 / P.pet_sig_z:.0f} % of the Z tensile strength {P.pet_sig_z} MPa")
    print(f"        estimated force per hook (friction mu {P.snap_mu} ASSUMED): closing {fin:.1f} N, pulling the lid off {fout:.1f} N; x6 hooks: lid pull-off about {6 * fout:.0f} N (not measured)")
    record("snap release: blade path through the back-plate slot is free and reaches the lead-in ramp", blade_ok and contact == 6 and skin_ok,
           f"blade 1.0 x 3.0 mm, pocket depth {P.t_back - P.snap_slot_skin:.1f} mm + {P.snap_slot_skin} mm skin (pierce it), tip travel {dreq / tl_:.1f} mm above the plate; contact with the ramp at {contact}/6 hooks; skin as designed at {'all' if skin_ok else 'NOT all'} hooks")
    return dreq


def clip_checks(P, surf, B):
    """Board clips measured on the BASE alone (R14: the lid is not needed to hold a board)."""
    base_sh = surf.shells[0]
    worst_d, play_min = 0.0, 9.0
    boards = {"host": (P.xh0, P.zh0, P.zh1, P.ym_b, P.xiao_pcb_t), "c6": (P.xc0, P.zc0, P.zc1, P.ym_b, P.xiao_pcb_t),
              "bme": (P.bme_x0, P.bme_z0, P.bme_z1, P.bme_yb, P.bme_pcb_t)}
    for name, (bx0, z0, z1, yb, thk) in boards.items():
        bx1 = bx0 + (P.bme_w if name == "bme" else P.xiao_w)
        yf = yb + thk
        pcb = (np.array([bx0, yb, z0]), np.array([bx1, yf, z1]))
        for cx, dx in ((bx0, 1), (bx1, -1)):
            for cz, dz in ((z0, 1), (z1, -1)):
                xa, xb = sorted((cx - dx * (P.clr + P.guide_t), cx + dx * (P.clr + P.clip_ov)))
                za, zb = sorted((cz - dz * (P.clr + P.guide_t), cz + dz * P.arm_z))
                pts = inside_points(base_sh, [xa, yf - 0.05, za], [xb, yf + P.clip_play + 6, zb], 0.15)
                over = box_samples([min(cx, cx + dx * P.clip_ov), yf + 0.01, min(cz, cz + dz * P.arm_z)],
                                   [max(cx, cx + dx * P.clip_ov), yf + 0.01, max(cz, cz + dz * P.arm_z)], 0.2)
                play_min = min(play_min, float(signed_distance(base_sh, over).min()))
                found = None                                   # board lowered from 5 mm above, arm points pushed outwards by delta
                for delta in np.arange(0.0, 2.01, 0.05):
                    ok = True
                    for dy in np.arange(5.0, -0.01, -0.5):
                        mv = pts + np.array([-dx * delta, 0, 0])
                        inside = ((mv[:, 0] > pcb[0][0]) & (mv[:, 0] < pcb[1][0]) & (mv[:, 2] > pcb[0][2]) & (mv[:, 2] < pcb[1][2]) &
                                  (mv[:, 1] > pcb[0][1] + dy) & (mv[:, 1] < pcb[1][1] + dy))
                        if inside.any():
                            ok = False
                            break
                    if ok:
                        found = float(delta)
                        break
                worst_d = max(worst_d, found if found is not None else 9.9)
    L = P.ym_f + P.clip_play - P.t_back
    width = P.clr + P.guide_t + P.arm_z
    eps_pct, force = cantilever(P.pet_E_z, P.guide_t, L, worst_d, width)
    fout = force * (P.snap_mu + 1.0) / (1 - P.snap_mu)
    record("board clips (12 arms: host, C6, BME680): insertion deflection and strain", worst_d < 9 and eps_pct <= P.clip_eps_max,
           f"arm must deflect {worst_d:.2f} mm (board pushed through the real STL), beam {P.guide_t} x {width:.1f} x {L:.1f} mm -> strain {eps_pct:.2f} % (limit {P.clip_eps_max} %); "
           f"about {fout:.1f} N per lip to pull a board out (mu {P.snap_mu} ASSUMED, not measured)")
    record("R14 bench use: the base alone holds the boards - no pressure at rest, a board can lift only by the play", 0 <= play_min <= P.clip_play + 0.02,
           f"lip underside {play_min:.2f} mm above the PCB corner (design {P.clip_play}), measured on the BASE ONLY; antennas sit in seats of the base; nothing relies on the lid")

    def rect_gap(a, b):
        return math.hypot(max(a[0] - b[1], b[0] - a[1], 0.0), max(a[2] - b[3], b[2] - a[3], 0.0))

    keeps = {"U.FL pads": (3.20, 5.88, 0.0, 3.6),
             "BOOT button": (P.btn_boot_u - 1.6, P.btn_boot_u + 1.6, P.xiao_l - P.btn_dv - 1.2, P.xiao_l - P.btn_dv + 1.2),
             "RESET button": (P.btn_rst_u - 1.6, P.btn_rst_u + 1.6, P.xiao_l - P.btn_dv - 1.2, P.xiao_l - P.btn_dv + 1.2),
             "USB-C receptacle": (P.xiao_w / 2 - P.usb_w / 2, P.xiao_w / 2 + P.usb_w / 2, P.xiao_l - 7.3, P.xiao_l + 1.5)}
    nearest = ("", 9.0)
    for (u0, u1) in ((0, P.clip_ov), (P.xiao_w - P.clip_ov, P.xiao_w)):          # the corner set is symmetric: valid for the upside-down host too
        for (v0, v1) in ((0, P.arm_z), (P.xiao_l - P.arm_z, P.xiao_l)):
            for kn, kr in keeps.items():
                g = rect_gap((u0, u1, v0, v1), kr)
                if g < nearest[1]:
                    nearest = (kn, g)
    record("board clips keep clear of U.FL pads, buttons and the USB-C shell", nearest[1] >= P.clip_keep_ufl,
           f"nearest keep-out '{nearest[0]}' {nearest[1]:.2f} mm from a lip footprint ({P.clip_ov} x {P.arm_z} mm at each corner); S3 footprints from Seeed's file, C6 ASSUMED equal, BME680 corner parts unknown")


def visible_faces(P, surf):
    """Probe 1 mm inside every outer face on a 1 mm grid (edges and rounded corners excluded): an opening is a probe point that is NOT
    inside printed material.  Every opening must lie in a designed box (vents, the ONE bottom USB opening + tie slots); none may be a snap
    feature, a USB opening elsewhere or a BOOT/RESET hole."""
    m = P.corner_r + 1.0
    xs = np.arange(m, P.Lo - m + 1e-9, 1.0)
    zs = np.arange(m, P.Ho - m + 1e-9, 1.0)
    ys = np.arange(2.0, P.Do - 2.0 + 1e-9, 1.0)
    xh_c, xc_c = P.xh0 + P.xiao_w / 2, P.xc0 + P.xiao_w / 2
    xb_c = (P.bme_x0 + P.bme_x1) / 2

    def probe(pts2d, mk):
        pts = np.array([mk(a, b) for a, b in pts2d])
        solid = in_solid(surf, pts)
        return [pt for pt, sd in zip(pts2d, solid) if not sd]

    res = {
        "front": probe([(x, z) for x in xs for z in zs], lambda a, b: (a, P.Do - 1.0, b)),
        "top": probe([(x, y) for x in xs for y in ys], lambda a, b: (a, b, P.Ho - 1.0)),
        "bottom": probe([(x, y) for x in xs for y in ys], lambda a, b: (a, b, 1.0)),
        "left": probe([(y, z) for y in ys for z in zs], lambda a, b: (1.0, a, b)),
        "right": probe([(y, z) for y in ys for z in zs], lambda a, b: (P.Lo - 1.0, a, b)),
        "back": probe([(x, z) for x in xs for z in zs], lambda a, b: (a, 1.0, b)),
    }

    def inside(boxes, a, b):
        return any(x0 <= a <= x1 and z0 <= b <= z1 for (x0, x1, z0, z1) in boxes)

    lid_out = P.v_out_n * P.lid_pitch_u
    front_boxes = [(xc - P.v_out_len / 2 - 1, xc + P.v_out_len / 2 + 1, P.v_out_zt - lid_out - 3, P.v_out_zt + 3) for xc in (xh_c, xc_c)]
    bottom_boxes = ([(xb_c - P.s_len / 2 - 1, xb_c + P.s_len / 2 + 1, P.v_bot_y - 3.5, P.v_bot_y + P.v_bot_n * P.wall_pitch_u + 1),
                     (xh_c - P.usb_open_w / 2 - 1.0, xh_c + P.usb_open_w / 2 + 1.0, 0, P.Do)]
                    + [(xh_c + s * P.tie_x - P.tie_w / 2 - 0.5, xh_c + s * P.tie_x + P.tie_w / 2 + 0.5, 0, P.Do) for s in (-1, 1)])
    unexpl = {"front": [p for p in res["front"] if not inside(front_boxes, *p)],
              "top": list(res["top"]),
              "bottom": [p for p in res["bottom"] if not inside(bottom_boxes, *p)],
              "left": list(res["left"]), "right": list(res["right"])}
    summary = "; ".join(f"{f}: {len(res[f])} probe points open" for f in ("front", "top", "bottom", "left", "right"))
    record("R10/R13/R16 visible faces: only vents, the ONE USB opening (bottom) and its tie slots are open; no snap feature, no BOOT/RESET hole, no second USB opening",
           all(len(v) == 0 for v in unexpl.values()),
           summary + f" (front = louvres only, top = NONE, bottom = inlet louvres + USB opening + tie slots, sides = none); unexplained openings: {sum(len(v) for v in unexpl.values())}")
    slot_boxes = []
    for (xf, s, z0) in hook_list(P):
        xa, xb = sorted((xf + s * (P.snap_t0 - P.snap_h - 0.4), xf + s * (P.snap_t0 + 1.2)))
        slot_boxes.append((xa - 0.2, xb + 0.2, z0 + 0.1, z0 + P.snap_b - 0.1))
    key_boxes = [(kx - P.key_head_d / 2 - 0.2, kx + P.key_head_d / 2 + 0.2, kz - P.key_head_d / 2 - 0.2, kz + P.key_slot_l + P.key_head_d / 2 + 0.2)
                 for kx, kz in ((P.key_xc, P.key_zh), (P.key_xc2, P.key_zh2))]
    in_slots = [p for p in res["back"] if inside(slot_boxes, *p)]
    other = [p for p in res["back"] if not inside(slot_boxes + key_boxes, *p)]
    record("R8 release access only through the back plate (six blind slots), none on any other face", len(in_slots) > 0 and len(other) == 0,
           f"{len(in_slots)} probe points open in the six release slots on the back face; {len(other)} unexplained openings on the back (keyholes: own check; tape cells 0.5 mm deep are not open at 1 mm)")


def text_no_hole_check(P, surf):
    """R16: no BOOT/RESET pin holes - the lid is solid in front of all four buttons (0.3 / 1.5 / 2.7 mm below the outer face)."""
    probes = []
    for (xb, zb0_, zb1_, up) in ((P.xh0, P.zh0, P.zh1, False), (P.xc0, P.zc0, P.zc1, True)):
        for u in (P.btn_boot_u, P.btn_rst_u):
            if up:                                                   # standard orientation: u from the larger-X edge, buttons 1.65 mm below the top edge
                probes.append((xb + P.xiao_w - u, zb1_ - P.btn_dv))
            else:                                                    # upside down: u from the smaller-X edge, buttons 1.65 mm above the lower edge
                probes.append((xb + u, zb0_ + P.btn_dv))
    pts = np.array([(x, P.Do - d, z) for (x, z) in probes for d in (0.3, 1.5, 2.7)])
    solid_all = bool(in_solid(surf, pts).all())
    record("R16 no BOOT/RESET pin holes: the lid is solid in front of all four buttons", solid_all,
           f"probed {len(probes)} button positions at 0.3 / 1.5 / 2.7 mm depth: all solid = {solid_all}")


def text_checks(P, surf, png):
    """R15: the engraved name.  Everything is derived from the SAVED lid STL by probing the outer face on a 0.4 mm grid:
    text pixel = air 0.3 mm below the outer face but solid at 0.9 mm and deeper; louvre pixel = air somewhere deeper."""
    from scipy import ndimage
    h = 0.4
    xs = np.arange(3.0, P.Lo - 3.0, h)
    zs = np.arange(5.0, P.Ho - 5.0, h)
    G = np.array([(x, z) for x in xs for z in zs])

    def air(depth):
        return (~in_solid(surf, np.stack([G[:, 0], np.full(len(G), P.Do - depth), G[:, 1]], axis=1))).reshape(len(xs), len(zs))

    a03, a05, a09 = air(0.3), air(0.5), air(0.9)
    deep = air(1.5) | air(2.1) | air(2.7)
    louvre = a09 | deep
    # the slanted louvre slots also leave 0.2-0.6 mm slivers of "air at 0.3 mm but solid at 0.9 mm" along their outer edge: a binary opening
    # with a 1.0 mm disc removes these slivers; real strokes (>= 2 mm) survive (strokes below 1 mm would be dropped here, none is designed)
    r1 = max(1, int(round(0.5 / h)))
    yy1, xx1 = np.mgrid[-r1:r1 + 1, -r1:r1 + 1]
    text = ndimage.binary_opening(a03 & ~louvre, structure=(xx1 ** 2 + yy1 ** 2) <= r1 ** 2)
    floor = a05 & text
    ncomp = ndimage.label(text)[1]
    record("R15 the engraved name exists as recess strokes in the outer face of the lid", text.sum() > 500,
           f"{int(text.sum() * h * h)} mm2 of recess in {ncomp} connected shapes (text = {P.name_l1}{P.name_l2}{P.name_l3}, 3 lines); font {P.name_font}")
    if not text.any():                                          # no engraving at all (e.g. an older revision's lid): every text check fails
        for nm in ("R15 the text lies fully inside the lid plate, clear of the edges", f"R15 the text keeps >= {P.name_louvre_gap:g} mm from every louvre",
                   f"R15 strokes at the recess floor are >= {P.name_stroke_min:g} mm wide (bridge and print safety)", "R15 the plate under the text stays >= 1.5 mm"):
            record(nm, False, "no engraved text found in the lid")
        text_no_hole_check(P, surf)
        return
    ix, iz = np.where(text)
    x_lo, x_hi, z_lo, z_hi = xs[ix].min(), xs[ix].max(), zs[iz].min(), zs[iz].max()
    record("R15 the text lies fully inside the lid plate, clear of the edges", x_lo >= 6 and x_hi <= P.Lo - 6 and z_lo >= 6 and z_hi <= P.Ho - 6,
           f"text spans x {x_lo:.1f}..{x_hi:.1f}, z {z_lo:.1f}..{z_hi:.1f} mm of a {P.Lo:.1f} x {P.Ho:.1f} mm lid; depth {P.name_depth} mm, plate left {P.t_lid - P.name_depth:.1f} mm")
    if louvre.any():
        dist = ndimage.distance_transform_edt(~louvre) * h
        dmin = float(dist[text].min())
    else:
        dmin = 99.0
    record(f"R15 the text keeps >= {P.name_louvre_gap:g} mm from every louvre", dmin >= P.name_louvre_gap, f"nearest louvre opening {dmin:.1f} mm from the recess (outer opening of the slanted slots measured on the outer face)")
    rr = max(1, int(round((P.name_stroke_min / 2 - 0.05) / h)))
    yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
    disk = (xx ** 2 + yy ** 2) <= rr ** 2
    opened = ndimage.binary_opening(floor, structure=disk)
    removed = floor & ~opened                                   # not reachable by a stroke-wide disc: sharp corners (thin slivers) and too-narrow strokes
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)    # a removed region wider than ~0.8 mm is a real narrow stroke, not a corner sliver
    narrow = ndimage.binary_opening(removed, structure=cross)
    frac = float(narrow.sum()) / max(1, float(floor.sum()))
    record(f"R15 strokes at the recess floor are >= {P.name_stroke_min:g} mm wide (bridge and print safety)", frac < 0.005,
           f"{100 * (1 - float(opened.sum()) / max(1, float(floor.sum()))):.1f} % of the floor area is out of reach of a disc of the stroke width (letter corners); "
           f"{100 * frac:.2f} % ({int(narrow.sum() * h * h)} mm2) lies in strokes that are really narrower (limit 0.5 %); rasterised estimate, 0.4 mm grid")
    # plate under the text
    ci = np.argwhere(text)[len(np.argwhere(text)) // 2]
    xt, zt = xs[ci[0]], zs[ci[1]]
    hit = ray_hits(surf.shells[1], [xt, P.Hbase_y - 1, zt], [xt, P.Do + 1, zt])
    ys_ = sorted(float(p[1]) for p in hit)
    left = (ys_[1] - ys_[0]) if len(ys_) >= 2 else float("nan")
    record("R15 the plate under the text stays >= 1.5 mm", left >= 1.5, f"{left:.2f} mm of plate at x={xt:.1f}, z={zt:.1f} (plate {P.t_lid} mm, recess {P.name_depth} mm)")
    text_no_hole_check(P, surf)
    if png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 7.6))
        img = np.zeros((len(zs), len(xs)))
        img[:, :] = 0.0
        img += 1.0 * louvre.T
        img[text.T] = 2.0
        ax.imshow(img[:, ::-1], origin="lower", extent=[xs[-1] + h / 2, xs[0] - h / 2, zs[0] - h / 2, zs[-1] + h / 2], cmap="Greys", vmin=0, vmax=3, aspect="equal")
        ax.set_title("Proof of the engraved text, probed on the SAVED lid STL, as seen from the front\n(X axis reversed = the viewer's view; black = recess, grey = louvres)", fontsize=9)
        ax.set_xlabel("X (mm, runs right to left for the viewer)")
        ax.set_ylabel("Z (mm, up)")
        os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
        fig.savefig(os.path.join(HERE, "preview", f"name_proof_{P.rev}.png"), dpi=110, bbox_inches="tight")
        plt.close(fig)


def air_analysis(P, surf, B, argv):
    import pyvista as pv
    from scipy import ndimage
    h = 0.5
    nx, ny, nz = int(P.Lo / h), int(P.Do / h), int(P.Ho / h)
    xs, ys, zs = (np.arange(nx) + 0.5) * h, (np.arange(ny) + 0.5) * h, (np.arange(nz) + 0.5) * h
    grid = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1).reshape(-1, 3)
    solid = np.zeros(nx * ny * nz, dtype=bool)
    for shell in surf.shells:
        sel = pv.PolyData(grid).select_interior_points(shell, check_surface=False)
        solid |= np.asarray(sel[list(sel.point_data.keys())[0]]).astype(bool)
    solid = solid.reshape(nx, ny, nz)
    R = P.corner_r                                   # voxels outside the rounded outline are not part of the case: treat them as solid
    gx, gz = np.meshgrid(xs, zs, indexing="ij")
    outside_outline = (gx - np.clip(gx, R, P.Lo - R)) ** 2 + (gz - np.clip(gz, R, P.Ho - R)) ** 2 > R ** 2
    solid |= outside_outline[:, None, :]

    def box_mask(m, lo, hi):
        m[int(lo[0] / h):int(math.ceil(hi[0] / h)), int(lo[1] / h):int(math.ceil(hi[1] / h)), int(lo[2] / h):int(math.ceil(hi[2] / h))] = True

    base_m = solid.copy()
    for n, (lo, hi) in B.items():
        if not n.startswith(("ant", "host.plug")):
            box_mask(base_m, lo, hi)

    def idx(x, y, z):
        return (int(x / h), int(y / h), int(z / h))

    xh_c, xc_c = P.xh0 + P.xiao_w / 2, P.xc0 + P.xiao_w / 2
    xb_c = (P.bme_x0 + P.bme_x1) / 2
    p_sens = idx(xb_c, P.ym_f + 1, P.bme_z1 + 3)                          # above the sensor board, below the baffle
    p_c6 = idx(xc_c, P.Hbase_y - 1.5, P.z_p1 + 3)                         # C6 channel, low, in front of the board
    p_host = idx(xh_c, P.Hbase_y - 1.5, P.zh1 + 10)                       # host column above the host
    p_key = idx(P.key_xc, P.t_back + 1.5, P.key_zh)                       # inside the lower keyhole chamber
    plan = []
    for label, slots_open, gap_blocked in (("as assembled (divider slots sealed with foam)", False, False),
                                           ("sensor-side end gap blocked (tests that it is the only way up)", False, True),
                                           ("divider slots open (before sealing)", True, False)):
        m = base_m.copy()
        box_mask(m, [0, 0, 0], [P.t_end + 0.01, P.Do, P.Ho])                 # end walls incl. the antenna seats (the patch fills the 0.3 mm seat)
        box_mask(m, [P.Lo - P.t_end - 0.01, 0, 0], [P.Lo, P.Do, P.Ho])
        if not slots_open:
            for zc_ in (P.div_s1_z, P.div_s2_z):
                box_mask(m, [P.x_div - 1.5, P.t_back + 3.5, zc_ - P.div_slot_w / 2], [P.x_div + 1.5, P.t_back + 4 + P.div_slot_h + 0.5, zc_ + P.div_slot_w / 2])
        if gap_blocked:
            box_mask(m, [P.Lo - P.t_end - P.g_gap, P.t_back, P.z_p0], [P.Lo - P.t_end, P.Hbase_y, P.z_p1])
        lab, _ = ndimage.label(~m)
        plan.append((label, lab))
        ls, lc, lh = lab[p_sens], lab[p_c6], lab[p_host]
        print(f"[INFO] air, {label}: sensor zone - C6 channel connected: {'YES' if (ls != 0 and ls == lc) else 'no'}; sensor zone - host column connected: {'YES' if (ls != 0 and ls == lh) else 'no'}")
    lab = plan[0][1]
    ls, lc, lh, lk = lab[p_sens], lab[p_c6], lab[p_host], lab[p_key]

    def faces(comp):
        return {"bottom": float(comp[:, :, 0].sum()) * h * h, "front": float(comp[:, -1, :].sum()) * h * h, "top": float(comp[:, :, -1].sum()) * h * h,
                "back": float(comp[:, 0, :].sum()) * h * h, "ends": float(comp[0].sum() + comp[-1].sum()) * h * h}

    fs, fh = faces(lab == ls), faces(lab == lh)
    print("        sensor + C6 column opens to: " + "; ".join(f"{k} {a:.0f} mm2" for k, a in fs.items() if a > 0))
    print("        host column opens to:        " + "; ".join(f"{k} {a:.0f} mm2" for k, a in fh.items() if a > 0))
    record("R2 chimney (sensor column): inlet in the bottom wall -> sensor -> end gap -> C6 -> outlet in the lid; sensor upstream of the C6",
           ls != 0 and ls == lc and fs["bottom"] > 0 and fs["front"] > 0,
           f"inlet {fs['bottom']:.0f} mm2 (bottom-wall louvres), outlet through the lid louvres {fs['front']:.0f} mm2")
    lab_b = plan[1][1]
    record("R2 the sensor-side end gap is the only way up from the sensor to the C6", lab_b[p_sens] != 0 and lab_b[p_sens] != lab_b[p_c6],
           "baffle (double wall, closed gap, end cap) from the divider to 7 mm short of the end wall; blocking that gap separates sensor and C6 channel")
    record("R2 host column (hotter module): own bottom inlet (the USB opening) + lid outlet, its exhaust never passes the sensor zone", lh != 0 and lh != ls and fh["bottom"] > 0 and fh["front"] > 0,
           f"host column and sensor zone are separate air volumes (divider slots sealed); host inlet {fh['bottom']:.0f} mm2 at the bottom (the USB opening + tie slots), outlet {fh['front']:.0f} mm2")
    lab_c = plan[2][1]
    print(f"[INFO] with the divider slots OPEN host column and sensor zone are {'connected' if lab_c[p_host] == lab_c[p_sens] else 'still separate'} (hence: seal them with foam after wiring)")
    record("R3 no opening in an upward-facing face: the top face is closed (no USB notch any more)", fs["top"] == 0 and fh["top"] == 0,
           f"open top area: sensor/C6 column {fs['top']:.0f} mm2, host column {fh['top']:.0f} mm2")
    sealed = lk != 0 and lk not in (ls, lc, lh)
    ck = lab == lk
    karea = {k: float(v.sum()) * h * h for k, v in {"back (wall side)": ck[:, 0, :], "front": ck[:, -1, :], "top": ck[:, :, -1], "bottom": ck[:, :, 0], "left": ck[0], "right": ck[-1]}.items() if v.any()}
    record("R4 keyhole chamber is sealed from the case interior (open only to the wall)", sealed and set(karea) == {"back (wall side)"},
           f"chamber air connected to the case: {'yes' if not sealed else 'no'}; its only opening: {karea}")
    back = lab[:, 0, :]
    comps = [c for c in np.unique(back) if c != 0]
    connected = [c for c in comps if c in (ls, lc, lh)]
    record("R4/R8 no opening on the back face is connected to the case interior (keyholes, 6 release slots, tape cells are blind)", len(connected) == 0 and len(comps) >= 9,
           f"{len(comps)} separate air pockets touch the back face, connected to the interior: {len(connected)}")
    for (sx_, sz_) in ((P.sh_x, P.sh_z), (P.sh_x2, P.sh_z2)):
        sk = lab[int(sx_ / h), 0, int(sz_ / h)]
        record("R4 a countersunk wall-screw hole is closed at the back (skin) - no air path", sk == 0 or sk not in (ls, lc, lh),
               f"voxel at the hole axis on the back plane is {'solid' if sk == 0 else 'air in a separate pocket'}")


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
