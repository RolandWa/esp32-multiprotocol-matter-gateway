"""Hardware-free tests of the 3D-printed enclosure (hardware/enclosure-3d), rev03 CONCEPT.

* the saved STLs in stl/ (archive_* sub-folders are ignored and not committed) pass hardware/enclosure-3d/mesh_check.py (closed, no degenerate faces,
  <= 240 mm, no wall < 0.8 mm, no overhang > 45 deg, no bridge > 10 mm) - skipped with a message when the STLs have not been generated yet
  (py -3.12 hardware/enclosure-3d/build.py);
* params.scad obeys the owner's print rules (vent >= 1.5 mm, walls, louvre angles, antenna distance, bridges, snap strain, no screws,
  engraved name: depth / plate / stroke rules);
* mutation checks: the checker must FAIL on a mesh with a hole, a flipped face, a thin wall, an overhang, a long bridge and an
  oversized part; the assembly checks must FAIL when the lid is displaced, when openings are not where the check expects them, when the
  hook geometry does not match, when the pin headers are taller than the standoff, and - using the ARCHIVED rev02 STLs (top USB notch,
  no engraved text) with the rev03 parameters - the R13 (one USB opening, bottom) and R15 (engraved name) checks; a simulated BOOT/RESET
  hole must trip R16 (a check that never fails proves nothing);
* the assembly check (needs pyvista + scipy) passes on the default build.
"""
import glob
import math
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENC = os.path.join(REPO, "hardware", "enclosure-3d")
STL_DIR = os.path.join(ENC, "stl")
if ENC not in sys.path:
    sys.path.insert(0, ENC)

import mesh_check  # noqa: E402
import scadparams  # noqa: E402

STLS = sorted(glob.glob(os.path.join(STL_DIR, "*.stl")))            # top level only: archive_* folders are not globbed
ARCH2 = os.path.join(STL_DIR, "archive_rev02")      # local only (git-ignored, not committed): the rev02 mutation tests skip without it
NEED_STL = pytest.mark.skipif(not STLS, reason="no STLs in hardware/enclosure-3d/stl - run: py -3.12 hardware/enclosure-3d/build.py")


# ----------------------------------------------------------------------------- synthetic meshes
def box(x0, x1, y0, y1, z0, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v[np.array(f)]


def sheared_block(angle_deg, size=10.0, h=10.0):
    s = h * np.tan(np.radians(angle_deg))
    b = np.array([[0, 0, 0], [size, 0, 0], [size, size, 0], [0, size, 0],
                  [s, 0, h], [size + s, 0, h], [size + s, size, h], [s, size, h]], float)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return b[np.array(f)]


def cat(*meshes):
    return np.concatenate(meshes)


def portal(gap):
    return cat(box(0, 5, 0, 30, 0, 13), box(5 + gap, 10 + gap, 0, 30, 0, 13), box(5.01, 5 + gap - 0.01, 0, 30, 10, 13))


# ----------------------------------------------------------------------------- the saved STLs
@NEED_STL
@pytest.mark.parametrize("path", STLS, ids=[os.path.basename(p) for p in STLS])
def test_saved_stl_passes_mesh_check(path):
    rep = mesh_check.check_file(path, samples=2500)
    assert rep.ok, "\n" + rep.text()
    assert (rep.open_edges, rep.nonmanifold_edges, rep.reversed_edges) == (0, 0, 0)


@NEED_STL
def test_expected_files_and_revision_in_name():
    rev = scadparams.load()["rev"]
    assert rev == "rev03"
    names = {os.path.basename(p) for p in STLS}
    for stem in ("enclosure_base", "enclosure_lid", "fit_sample_modules", "fit_sample_antenna", "fit_sample_name",
                 "fit_sample_snap", "fit_sample_louvre", "fit_sample_mount"):
        assert f"{stem}_{rev}.stl" in names
    assert not [n for n in names if n.startswith(("usb_dust_plug", "fit_sample_plug"))], "the USB dust plug is gone in rev03"
    # the STL set is of ONE revision: an older revision's file next to it would be printed by mistake
    assert not [n for n in names if f"_{rev}.stl" not in n], "stl/ holds files of another revision: %s" % sorted(names)


# ----------------------------------------------------------------------------- parameter rules
def test_params_follow_print_rules():
    p = scadparams.P()
    assert p.ant_sep >= p.min_ant_sep >= 60, "antenna separation must stay >= 60 mm"
    assert p.louver_slot >= 1.5 and p.louver_slat >= 1.5, "vent slots and slats >= 1.5 mm"
    assert p.louver_ang_lid <= 45, "lid louvre faces must lean <= 45 deg from the plate normal (prints without support)"
    assert p.louver_ang_wall >= 45, "bottom-wall louvre faces must be >= 45 deg from horizontal"
    assert min(p.t_wall, p.part_wall) >= 2.0, "chamber walls >= 2 mm"
    assert 1.5 <= p.t_end <= 2.0, "wall near the antenna 1.5-2 mm"
    assert p.t_end - p.ant_seat_d >= 1.5, "wall under the antenna seat stays >= 1.5 mm"
    assert p.tape_w <= p.max_bridge, "a tape recess cell is a bridge in print"
    assert p.key_head_d + 2 * p.key_cav_m <= p.max_bridge, "keyhole chamber roof is a bridge"
    assert p.Ho <= 240 and p.Lo <= 240
    assert p.ant_z1 - p.ant_z0 == pytest.approx(p.ant_len)
    assert p.ant_flat_w >= 22 and p.ant_flat_l >= 45, "flat antenna zone must cover the largest candidate patch"
    assert p.ant_keep_m <= p.mod_inset, "module-to-antenna keep-out"
    assert p.h_post >= p.hdr_h


def test_widths_and_antenna_floor():
    p = scadparams.P()
    assert p.Win >= p.min_ant_sep + 1
    assert p.Win == pytest.approx(max(p.min_ant_sep + 1, p.h_col + p.c_col))
    assert p.c_col == pytest.approx(max(p.mid_h + p.xiao_w + p.mod_inset, p.bme_gap + p.bme_w + p.mod_inset))
    assert p.Lo == pytest.approx(p.Win + 2 * p.t_end)
    # the owner's sketch (3 mm keep-out, 5 mm gap): the 60 mm floor takes over
    p2 = scadparams.P(overrides={"mod_inset": 3.0, "mid_h": 5.0})
    assert p2.Win == pytest.approx(p2.min_ant_sep + 1) and p2.Win > p2.h_col + p2.c_col


def test_no_screws_anywhere_in_the_case():
    p = scadparams.load()
    assert "join_mode" not in p and not any(k.startswith(("m3_", "nut_", "boss_", "cs_")) for k in p), "no screw / nut / boss parameters"
    scad = open(os.path.join(ENC, "enclosure.scad"), encoding="utf-8").read()
    for word in ("nut pocket", "countersunk M3", "boss_solid", "m3_hole"):
        assert word not in scad


def test_rev03_decisions_in_params():
    """R12-R16 as parameters: no dust plug, no pin holes, one USB opening in the bottom wall, engraved name rules."""
    p = scadparams.load()
    assert not any(k.startswith(("plug_", "pin_", "fs_plug")) for k in p), "dust plug / BOOT-RESET pin parameters must be gone"
    q = scadparams.P()
    assert q.usb_open_w >= 12.4 and q.usb_lead >= 1.0 and q.tie_w >= 2.5, "opening must pass a plug overmould; tie slots a 2.5 mm tie"
    assert q.name_l1 + q.name_l2 + q.name_l3 == "esp32-matter-gateway", "name (owner typed 'gatway'; 'gateway' to be confirmed)"
    assert 0.6 <= q.name_depth <= 0.8, "recess depth 3-4 layers"
    assert q.t_lid - q.name_depth >= 1.5, "plate under the recess >= 1.5 mm"
    assert "Bold" in q.name_font, "bold face so that strokes reach 2 mm"
    assert q.name_depth / 0.2 == pytest.approx(round(q.name_depth / 0.2)), "depth is a whole number of 0.2 mm layers (stepped edge)"
    assert q.v_out_n >= 1


def test_r17_keyholes_on_one_horizontal_line_with_drilling_marks():
    """R17: both hanging holes at the same height, symmetric, spacing equal to the number printed on the back; marks printable."""
    q = scadparams.P()
    assert q.key_zh == pytest.approx(q.key_zh2), "both keyholes on ONE horizontal line"
    assert q.key_xc2 - q.key_xc == pytest.approx(q.key_dx)
    assert (q.key_xc + q.key_xc2) / 2 == pytest.approx(q.Lo / 2), "symmetric about the case centre line"
    assert float(str(q.dim_txt).split()[0]) == pytest.approx(q.key_dx), "the printed distance equals the real one"
    assert q.dim_on == 1 and q.dim_w >= 0.8, "marks present and at least the 0.8 mm print minimum"
    assert q.dim_depth / 0.2 == pytest.approx(round(q.dim_depth / 0.2)) and q.t_back - q.dim_depth >= 1.5
    assert q.tape_z1 < q.dim_z - q.dim_w, "the tape cells must not run through the drilling marks"
    assert q.dim_txt_z + 0.72 * q.dim_txt_size < q.key_zh - q.key_head_d / 2, "text stays below the head holes"


def test_snap_geometry_rules_and_strain():
    p = scadparams.P()
    assert p.snap_ret <= 45 and p.clip_ret <= 45, "catch / retention faces face down in print: <= 45 deg from vertical"
    assert p.snap_t >= p.min_wall and p.guide_t >= p.min_wall and p.snap_flat >= 1.2
    tl = math.tan(math.radians(p.snap_lead))
    ytop = p.t_back + p.snap_yb - p.snap_play + p.snap_t0 - p.snap_h - p.snap_h / tl - p.snap_flat + p.snap_h / tl + p.snap_flat + p.snap_h
    L = p.Hbase_y - ytop
    delta = p.snap_o + 0.1
    eps = 100 * 1.5 * delta * p.snap_t / L ** 2
    assert eps <= p.snap_eps_max, f"hook strain {eps:.2f} % exceeds the design limit {p.snap_eps_max} %"
    assert p.pet_E_z * eps / 100 <= 0.6 * p.pet_sig_z, "hook stress must stay below 60 % of the Z tensile strength (Bambu PETG Basic TDS)"
    Lc = p.ym_f + p.clip_play - p.t_back
    eps_c = 100 * 1.5 * (p.clip_ov + 0.1) * p.guide_t / Lc ** 2
    assert eps_c <= p.clip_eps_max
    assert p.snap_slot_skin >= 0.8 and p.sh_skin >= 0.8, "closing skins must not be thinner than 0.8 mm"


def test_rounded_corner_keeps_wall():
    p = scadparams.P()
    d = math.hypot(p.t_end + p.corner_ri - p.corner_r, p.t_wall + p.corner_ri - p.corner_r)
    wall = p.corner_r - d - p.corner_ri
    assert wall >= 1.5, f"corner wall {wall:.2f} mm"
    assert p.corner_r >= 4 and p.ch_lid <= p.t_lid - 1.0


def test_scadparams_reevaluates_overrides():
    p = scadparams.P(overrides={"Din": 26})
    assert p.Din == 26 and p.Hbase_y == p.t_back + 26 and p.Do == p.Hbase_y + p.t_lid


# ----------------------------------------------------------------------------- mutation checks of the mesh checker
def test_checker_accepts_a_good_part():
    rep = mesh_check.check_triangles(box(0, 20, 0, 20, 0, 20), "cube")
    assert rep.ok and rep.shells == 1 and rep.volume == pytest.approx(8000, rel=1e-6)


def test_checker_detects_hole_flipped_face_degenerate():
    good = box(0, 20, 0, 20, 0, 20)
    assert mesh_check.check_triangles(np.delete(good, 3, axis=0), "hole").open_edges > 0
    flipped = good.copy()
    flipped[5] = flipped[5][[0, 2, 1]]
    r = mesh_check.check_triangles(flipped, "flipped")
    assert not r.ok and r.reversed_edges > 0
    r = mesh_check.check_triangles(good[:, ::-1, :], "inverted")
    assert not r.ok and r.negative_shells == 1
    r = mesh_check.check_triangles(cat(good, np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]]], float)), "degenerate")
    assert not r.ok and r.degenerate >= 1


def test_checker_detects_thin_wall():
    r = mesh_check.check_triangles(box(0, 20, 0, 20, 0, 0.5), "slab0.5")
    assert not r.ok and r.thin_hard > 0 and r.min_wall == pytest.approx(0.5, abs=0.01)
    r = mesh_check.check_triangles(box(0, 20, 0, 20, 0, 1.2), "slab1.2")
    assert r.ok and r.thin_warn > 0 and not r.thin_hard
    r = mesh_check.check_triangles(box(0, 20, 0, 20, 0, 2.0), "slab2")
    assert r.ok and r.thin_warn == 0


def test_checker_detects_overhang():
    assert mesh_check.check_triangles(sheared_block(40), "lean40").ok
    assert mesh_check.check_triangles(sheared_block(45), "lean45").ok
    r = mesh_check.check_triangles(sheared_block(60), "lean60")
    assert not r.ok and r.overhang_faces > 0


def test_checker_detects_long_bridge():
    r = mesh_check.check_triangles(portal(30), "bridge30")
    assert not r.ok and r.bridge_fail > 0
    r = mesh_check.check_triangles(portal(8), "bridge8")
    assert r.ok and r.bridges and max(b[1] for b in r.bridges) <= mesh_check.MAX_BRIDGE


def test_checker_detects_oversized_part():
    r = mesh_check.check_triangles(box(0, 250, 0, 20, 0, 20), "long")
    assert not r.ok and any("240" in f for f in r.failures)


@NEED_STL
def test_checker_fails_on_mutated_real_stl():
    base = [p for p in STLS if os.path.basename(p).startswith("enclosure_base_rev")]
    tris = mesh_check.read_stl(base[0])
    assert mesh_check.check_triangles(np.delete(tris, 100, axis=0), "hole", samples=200).open_edges > 0
    flipped = tris.copy()
    flipped[100] = flipped[100][[0, 2, 1]]
    assert mesh_check.check_triangles(flipped, "flip", samples=200).reversed_edges > 0
    p = scadparams.P()
    thin = tris.copy()
    face_inner = np.isclose(thin[:, :, 2], p.t_back, atol=1e-6).all(axis=1)
    thin[face_inner, :, 2] = 0.5
    assert mesh_check.check_triangles(thin, "thin plate", samples=3000).thin_hard > 0


# ----------------------------------------------------------------------------- assembly check (+ mutations of its new checks)
def _asm():
    pytest.importorskip("pyvista")
    pytest.importorskip("scipy")
    import assembly_check
    assembly_check.RESULTS.clear()
    return assembly_check


def _failed(asm):
    return [n for n, ok, _ in asm.RESULTS if not ok]


@NEED_STL
def test_assembly_check_passes_default_and_fails_with_tall_headers(capsys):
    asm = _asm()
    assert asm.run(["--no-air"]) == 0, "assembly check failed on the default build"
    asm.RESULTS.clear()
    assert asm.run(["--no-air", "--hdr", "18"]) == 1, "18 mm headers must collide with the back plate"
    capsys.readouterr()


def _surf_from(asm, P, lid_shift=(0, 0, 0), base=None, lid=None):
    import pyvista as pv
    surf, tb, tl = asm.load_enclosure(P, base or os.path.join(STL_DIR, f"enclosure_base_{P.rev}.stl"),
                                      lid or os.path.join(STL_DIR, f"enclosure_lid_{P.rev}.stl"))
    tl2 = tl + np.array(lid_shift, float)
    s2 = asm._surf(np.concatenate([tb, tl2]))
    pv.set_new_attribute(s2, "shells", (asm._surf(tb), asm._surf(tl2)))
    return s2, tb, tl2


def _rev02_surf(asm, P):
    base = os.path.join(ARCH2, "enclosure_base_rev02.stl")
    lid = os.path.join(ARCH2, "enclosure_lid_rev02.stl")
    if not (os.path.isfile(base) and os.path.isfile(lid)):
        pytest.skip("archived rev02 STLs missing")
    return _surf_from(asm, P, base=base, lid=lid)[0]


@NEED_STL
def test_snap_checks_pass_and_fail_when_lid_is_displaced(capsys):
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    asm.snap_checks(P, surf)
    assert _failed(asm) == [], _failed(asm)
    asm.RESULTS.clear()
    surf2, _, _ = _surf_from(asm, P, lid_shift=(0, 0.4, 0))           # lid sitting 0.4 mm too far out: the hook heads run into the bumps
    asm.snap_checks(P, surf2)
    assert any("engaged without interference" in n for n in _failed(asm)), "displaced lid must be detected"
    asm.RESULTS.clear()
    surf3, _, _ = _surf_from(asm, P, lid_shift=(0, 0, 8.0))           # lid shifted 8 mm along Z: no hook stands at a bump any more
    asm.snap_checks(P, surf3)
    assert any("stands at every bump" in n for n in _failed(asm)), "a lid shifted by 8 mm must be reported"
    capsys.readouterr()


@NEED_STL
def test_visible_face_check_is_not_vacuous(capsys):
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    asm.visible_faces(P, surf)
    assert _failed(asm) == [], _failed(asm)
    asm.RESULTS.clear()
    Pm = scadparams.P(overrides={"usb_open_w": 6.0})                 # the expected USB opening is narrower than the real one -> unexplained bottom openings
    asm.visible_faces(Pm, surf)
    assert any("visible faces" in n for n in _failed(asm)), "unexpected openings on the bottom face must be reported"
    asm.RESULTS.clear()
    Pm1 = scadparams.P(overrides={"tie_x": 14.0})                    # tie slots expected elsewhere
    asm.visible_faces(Pm1, surf)
    assert any("visible faces" in n for n in _failed(asm)), "tie slots outside the expected boxes must be reported"
    asm.RESULTS.clear()
    Pm2 = scadparams.P(overrides={"snap_t0": 3.0})                   # release slots expected elsewhere -> back-face openings unexplained
    asm.visible_faces(Pm2, surf)
    assert any("release access" in n for n in _failed(asm)), "release slots outside the expected boxes must be reported"
    asm.RESULTS.clear()
    asm.visible_faces(P, _rev02_surf(asm, P))                         # rev02 housing: a USB notch in the TOP face and a pin hole pair in the lid
    assert any("visible faces" in n for n in _failed(asm)), "the rev02 top USB notch must be reported as an opening in the top face"
    capsys.readouterr()


@NEED_STL
def test_usb_checks_pass_and_fail_on_the_rev02_housing(capsys):
    """R13: ONE opening in the bottom wall.  The archived rev02 housing has the notch in the TOP wall: it must fail."""
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    B, info = asm.build_bodies(P, 0.0)
    asm.usb_checks(P, surf, B, info)
    assert _failed(asm) == [], _failed(asm)
    asm.RESULTS.clear()
    asm.usb_checks(P, _rev02_surf(asm, P), B, info)
    bad = _failed(asm)
    assert any("BOTTOM wall" in n for n in bad), "no opening in the bottom wall must be reported"
    assert any("no other USB opening" in n for n in bad), "a USB notch in the top face must be reported"
    assert any("cable anchor" in n for n in bad), "missing tie slots must be reported"
    capsys.readouterr()


@NEED_STL
def test_text_checks_pass_and_fail_without_engraving_or_with_pin_hole(capsys, monkeypatch):
    """R15/R16: the engraved name is found in the lid STL; a lid without text fails; a pin hole in front of a button fails R16."""
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    asm.text_checks(P, surf, False)
    assert _failed(asm) == [], _failed(asm)
    assert sum(1 for n, ok, _ in asm.RESULTS if n.startswith("R15")) >= 5
    asm.RESULTS.clear()
    asm.text_checks(P, _rev02_surf(asm, P), False)                    # rev02 lid: no engraved name
    bad = _failed(asm)
    assert any("engraved name exists" in n for n in bad), "a lid without text must fail R15"
    asm.RESULTS.clear()
    real = asm.in_solid
    bx, bz = P.xh0 + P.btn_boot_u, P.zh0 + P.btn_dv

    def with_hole(s, pts):                                            # simulate a 3 mm pin hole through the lid at the host BOOT button
        r = real(s, pts)
        near = (np.hypot(pts[:, 0] - bx, pts[:, 2] - bz) < 1.5) & (pts[:, 1] > P.Do - 3.0)
        return r & ~near

    monkeypatch.setattr(asm, "in_solid", with_hole)
    asm.text_checks(P, surf, False)
    assert any("R16" in n for n in _failed(asm)), "a pin hole in front of a button must fail R16"
    capsys.readouterr()


@NEED_STL
def test_text_check_catches_wide_strokes_and_louvre_clearance_demands(capsys):
    """The stroke / louvre-clearance limits are parameters: demanding more than the lid delivers must fail (not vacuous)."""
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    asm.text_checks(scadparams.P(overrides={"name_louvre_gap": 30.0}), surf, False)
    assert any("from every louvre" in n for n in _failed(asm)), "a 30 mm louvre clearance cannot be met"
    asm.RESULTS.clear()
    asm.text_checks(scadparams.P(overrides={"name_stroke_min": 4.5}), surf, False)
    assert any("strokes at the recess floor" in n for n in _failed(asm)), "4.5 mm strokes cannot be met by a 2 mm bold font"
    capsys.readouterr()


@NEED_STL
def test_clip_checks_pass_and_fail(capsys):
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    B, _ = asm.build_bodies(P, 0.0)
    asm.clip_checks(P, surf, B)
    assert _failed(asm) == [], _failed(asm)
    asm.RESULTS.clear()
    Pm = scadparams.P(overrides={"clip_ov": 1.6})                    # lips expected to reach 1.6 mm over the board: strain / keep-out must object
    asm.clip_checks(Pm, surf, B)
    assert _failed(asm), "a mismatching clip geometry must fail"
    capsys.readouterr()


@NEED_STL
def test_air_analysis_passes_and_fails_on_the_rev02_housing(capsys):
    """R2/R3: chimney, separate host column, closed top face (flood fill, about 40 s per run).  The archived rev02 housing has the top USB notches."""
    asm = _asm()
    P = scadparams.P()
    surf, _, _ = _surf_from(asm, P)
    B, _ = asm.build_bodies(P, 0.0)
    asm.air_analysis(P, surf, B, [])
    assert _failed(asm) == [], _failed(asm)
    assert any("R2 chimney" in n for n, ok, _ in asm.RESULTS) and any("R3 no opening in an upward-facing face" in n for n, ok, _ in asm.RESULTS)
    asm.RESULTS.clear()
    asm.air_analysis(P, _rev02_surf(asm, P), B, [])
    assert any("R3 no opening in an upward-facing face" in n for n in _failed(asm)), "the top USB notches of rev02 must be reported"
    capsys.readouterr()
