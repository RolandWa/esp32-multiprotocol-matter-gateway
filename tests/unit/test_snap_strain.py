"""R11 (docs/ENCLOSURE_3D.md section 3a): the lid hooks and the board clips must not break when they are pushed in or pulled out.

What is calculated: the largest bending strain in a cantilever beam that is deflected by the amount the mating part forces on it
(hook: the overlap with the case bump; clip: the lip overhang over the board corner + 0.1 mm tolerance), the stress that strain
means (E * strain), and the margin to the material limits - all with the Z-direction data of Bambu Lab PETG Basic (technical data
sheet V3.0: E 2550 MPa, strength 35 MPa, elongation at break 5.2 %), because both the hooks (lid printed outer face down) and the clip
arms (base printed back down) STAND on the plate: their bending strain acts along the layer-stacking direction, the weak one.

Two tiers:
  * the CHOSEN variant: strain <= the design limit of params.scad (0.8 %, about 1/6 of the Z elongation at break), stress <= 60 % of the
    Z strength, and a margin of at least 5 to the elongation at break (covers stress concentration at the root and repeated use);
  * EVERY variant of the fit samples (0.8 / 1.0 / 1.2 mm hook heads, 0.5 / 0.7 / 0.9 mm lip overhangs): stress <= 80 % of the Z
    strength and a margin of at least 4 to the elongation at break, so that one insertion cannot crack a variant that the owner may be
    tempted to pick because it "clicks". (A "1/3 of the elongation at break" rule would be inconsistent: E * 1.73 % = 44 MPa is above
    the 35 MPa strength, the linear model stops being valid long before.)
    A variant that passes this tier but not the first one is a TEST variant, not a choice: at the time of writing the 0.9 mm clip lip
    (0.85 % strain, 21.7 MPa) is over the design limit of 0.8 % / 21 MPa - print it to learn where the click is lost, do not adopt it
    without revising the limit.

What is NOT checked here: fatigue (cycle life) and the real strength of a printed part. The data sheet values are typical values from
the manufacturer's own tests, not guaranteed minima; the margins are design choices. The cycle test on the printed fit samples
(at least 20 closings per variant, then 24 h closed) stays the owner's job - see hardware/enclosure-3d/README.md.
"""
import math
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENC = os.path.join(REPO, "hardware", "enclosure-3d")
if ENC not in sys.path:
    sys.path.insert(0, ENC)

import scadparams  # noqa: E402

MARGIN_CHOSEN = 5.0      # elongation at break / strain, chosen variant
MARGIN_VARIANT = 4.0     # same, every fit-sample variant
STRESS_CHOSEN = 0.6      # fraction of the Z tensile strength, chosen variant
STRESS_VARIANT = 0.8     # same, every fit-sample variant
CLIP_TOLERANCE = 0.1     # mm added to the lip overhang (board outline tolerance, corner rounding)
REQUIRED_CLOSINGS = 12   # R12: about 10 during commissioning + about 2 in the life of the product (owner, 2026-11-27)
TEST_PLAN_CLOSINGS = 20  # closings per variant in the printed cycle test (README, "Snap test the owner should do")


# ----------------------------------------------------------------------------- the model
def strain_percent(t, length, deflection):
    """Peak bending strain (%) at the root of a constant rectangular cantilever deflected by `deflection` at its tip.
    Euler-Bernoulli: tip load F gives y = F L^3 / (3 E I) and a root curvature F L / (E I), so strain = (t/2) * 3 y / L^2."""
    return 100.0 * 1.5 * t * deflection / length ** 2


def numeric_strain_percent(t, length, deflection, n=4001):
    """The same number by a different route: take the deflection curve of a tip-loaded cantilever, differentiate it twice
    numerically and multiply the largest curvature by t/2 (guards against a typo in the closed form)."""
    x = np.linspace(0.0, length, n)
    w = deflection * (3 * x ** 2 * length - x ** 3) / (2 * length ** 3)
    kappa = np.gradient(np.gradient(w, x), x)
    inner = slice(n // 100, n - n // 100)          # the end rows of np.gradient are one-sided and inexact
    return 100.0 * float(np.max(np.abs(kappa[inner]))) * t / 2.0


def violations(p, t, length, deflection, eps_limit, margin, stress_fraction=STRESS_CHOSEN):
    """List of broken limits for one beam (empty = safe)."""
    eps = strain_percent(t, length, deflection)
    sigma = p.pet_E_z * eps / 100.0
    out = []
    if eps > eps_limit + 1e-9:
        out.append(f"strain {eps:.2f} % exceeds the limit {eps_limit:.2f} %")
    if sigma > stress_fraction * p.pet_sig_z + 1e-9:
        out.append(f"stress {sigma:.1f} MPa exceeds {stress_fraction:.0%} of the Z strength ({stress_fraction * p.pet_sig_z:.1f} MPa)")
    if p.pet_eb_z / eps < margin:
        out.append(f"margin to the elongation at break is {p.pet_eb_z / eps:.1f}, below {margin}")
    return out


# ----------------------------------------------------------------------------- the geometry of the real design
def hook_geometry(p, head=None):
    """(thickness, free length, deflection) of one lid hook. The deflection is what the case bump forces on the hook when the head
    passes it: bump height minus the gap that is free between the head tip and the wall."""
    h = p.snap_h if head is None else head
    t0 = p.snap_t0                                   # gap beam inner face -> wall face, fixed by the case, not by the head variant
    deflection = p.snap_q - (t0 - h)
    tl_, tr_ = math.tan(math.radians(p.snap_lead)), math.tan(math.radians(p.snap_ret))
    ye = p.t_back + p.snap_yb - p.snap_play + t0 - h - h / tl_ - p.snap_flat    # lowest point of the head (lead-in tip)
    ytop = ye + h / tl_ + p.snap_flat + h / tr_                                 # top of the head = where the beam ends
    return p.snap_t, p.Hbase_y - ytop, deflection, ye


def clip_geometry(p, overhang=None):
    ov = p.clip_ov if overhang is None else overhang
    return p.guide_t, p.ym_f + p.clip_play - p.t_back, ov + CLIP_TOLERANCE


# ----------------------------------------------------------------------------- the formula itself
@pytest.mark.parametrize("t,length,y", [(1.8, 19.0, 0.75), (1.6, 16.8, 0.8), (2.0, 20.0, 1.0), (1.0, 8.0, 0.3)])
def test_closed_form_agrees_with_the_numeric_beam_model(t, length, y):
    assert strain_percent(t, length, y) == pytest.approx(numeric_strain_percent(t, length, y), rel=0.03)


def test_textbook_case():
    # 2 mm thick, 20 mm long beam bent 1 mm: eps = 1.5 * 2 * 1 / 400 = 0.75 %
    assert strain_percent(2.0, 20.0, 1.0) == pytest.approx(0.75)


def test_strain_grows_with_deflection_and_thickness_and_falls_with_length_squared():
    base = strain_percent(1.8, 19.0, 0.75)
    assert strain_percent(1.8, 19.0, 1.5) == pytest.approx(2 * base)
    assert strain_percent(3.6, 19.0, 0.75) == pytest.approx(2 * base)
    assert strain_percent(1.8, 38.0, 0.75) == pytest.approx(base / 4)


# ----------------------------------------------------------------------------- the lid hooks
def test_hook_deflection_equals_the_designed_bump_overlap():
    p = scadparams.P()
    _t, _length, y, _ye = hook_geometry(p)
    assert y == pytest.approx(p.snap_o), "deflection (bump height - free gap) must equal the engagement overlap of params.scad"


def test_hook_geometry_matches_the_saved_lid_stl():
    """The free length is derived from params.scad; confirm the lowest point of the head against the saved STL, so that the length
    used for the strain is the length of the printed part. (Skipped when the STLs have not been built.)"""
    import mesh_check
    stl = os.path.join(ENC, "stl", f"enclosure_lid_{scadparams.load()['rev']}.stl")
    if not os.path.exists(stl):
        pytest.skip("lid STL not built: py -3.12 hardware/enclosure-3d/build.py")
    p = scadparams.P()
    tris = mesh_check.read_stl(stl)
    # the lid prints OUTER face down: print z = Do - Y, so the lowest head point (smallest Y) is the largest print z
    y_lowest = p.Do - float(tris[..., 2].max())
    ye = hook_geometry(p)[3]
    assert y_lowest == pytest.approx(ye, abs=0.05), f"STL lowest hook point y = {y_lowest:.3f}, params give {ye:.3f}"


def test_chosen_hook_is_inside_the_design_limits():
    p = scadparams.P()
    t, length, y, _ye = hook_geometry(p)
    bad = violations(p, t, length, y, p.snap_eps_max, MARGIN_CHOSEN)
    assert not bad, f"hook {t} x {length:.1f} mm, deflection {y} mm: " + "; ".join(bad)


@pytest.mark.parametrize("head", ["fs_h1", "fs_h2", "fs_h3"])
def test_every_hook_variant_of_the_fit_sample_survives_one_insertion(head):
    p = scadparams.P()
    t, length, y, _ye = hook_geometry(p, head=getattr(p, head))
    bad = violations(p, t, length, y, 100.0, MARGIN_VARIANT, STRESS_VARIANT)
    assert not bad, f"{head} = {getattr(p, head)} mm head: deflection {y:.2f} mm, strain {strain_percent(t, length, y):.2f} %: " + "; ".join(bad)


def test_hook_removal_loads_the_beam_no_more_than_insertion():
    # the 45 degree catch face is a ramp: a hard pull opens the lid, the hook deflects by the same overlap as when it closed
    p = scadparams.P()
    _t, _length, y, _ye = hook_geometry(p)
    assert y == pytest.approx(p.snap_o)


# ----------------------------------------------------------------------------- the board clips
def test_chosen_board_clip_is_inside_the_design_limits():
    p = scadparams.P()
    t, length, y = clip_geometry(p)
    bad = violations(p, t, length, y, p.clip_eps_max, MARGIN_CHOSEN)
    assert not bad, f"clip arm {t} x {length:.1f} mm, deflection {y:.2f} mm: " + "; ".join(bad)


@pytest.mark.parametrize("ov", ["fs_ov1", "fs_ov2", "fs_ov3"])
def test_every_clip_variant_of_the_fit_sample_survives_one_insertion(ov):
    p = scadparams.P()
    t, length, y = clip_geometry(p, overhang=getattr(p, ov))
    bad = violations(p, t, length, y, 100.0, MARGIN_VARIANT, STRESS_VARIANT)
    assert not bad, f"{ov} = {getattr(p, ov)} mm lip: deflection {y:.2f} mm, strain {strain_percent(t, length, y):.2f} %: " + "; ".join(bad)


# ----------------------------------------------------------------------------- the check must be able to fail
@pytest.mark.parametrize("override,what", [
    ({"snap_t": 3.0}, "a hook twice as thick as the 1.8 mm design bends more for the same deflection"),
    ({"snap_o": 1.6}, "a deeper engagement overlap deflects the hook further"),
    ({"snap_eps_max": 0.4}, "a stricter design limit rejects the default geometry"),
    ({"guide_t": 3.2}, "a clip arm of double thickness"),
    ({"clip_ov": 1.6}, "a lip that reaches 1.6 mm over the board"),
])
def test_unsafe_designs_are_reported(override, what):
    p = scadparams.P(overrides=override)
    t, length, y, _ye = hook_geometry(p)
    tc, lc, yc = clip_geometry(p)
    problems = violations(p, t, length, y, p.snap_eps_max, MARGIN_CHOSEN) + violations(p, tc, lc, yc, p.clip_eps_max, MARGIN_CHOSEN)
    assert problems, f"nothing was reported for: {what}"


def test_a_short_beam_is_reported():
    p = scadparams.P()
    t, _length, y, _ye = hook_geometry(p)
    assert violations(p, t, 9.0, y, p.snap_eps_max, MARGIN_CHOSEN)    # half the length: four times the strain


def test_printed_cycle_test_covers_the_required_service_life_with_margin():
    """R12: the strain calculation says nothing about fatigue, so the printed cycle test is what proves the life. The documented
    plan must exceed the required number of closings, and the README must really state that plan (a plan that is not written down
    does not get done)."""
    assert TEST_PLAN_CLOSINGS >= 1.5 * REQUIRED_CLOSINGS
    with open(os.path.join(ENC, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    assert f"at least {TEST_PLAN_CLOSINGS} close/open cycles" in readme, "README no longer states the cycle test plan"
    assert f"survive {REQUIRED_CLOSINGS} closings" in readme, "README no longer states the required service life (R12)"


def test_material_data_is_the_cited_z_direction_data():
    p = scadparams.P()
    assert (p.pet_E_z, p.pet_sig_z, p.pet_eb_z) == (2550, 35, 5.2)    # Bambu Lab PETG Basic TDS V3.0, Z direction (typical values)


def test_report_margins():
    """Prints the numbers (py -3.12 -m pytest tests/unit/test_snap_strain.py -s) so that the owner can read them."""
    p = scadparams.P()
    t, length, y, _ye = hook_geometry(p)
    tc, lc, yc = clip_geometry(p)
    for name, (tt, ll, yy, lim) in {"lid hook": (t, length, y, p.snap_eps_max), "board clip": (tc, lc, yc, p.clip_eps_max)}.items():
        eps = strain_percent(tt, ll, yy)
        margin = p.pet_eb_z / eps
        print(f"{name}: {tt} x {ll:.1f} mm, deflection {yy:.2f} mm -> strain {eps:.2f} % (limit {lim} %), stress {p.pet_E_z * eps / 100:.1f} MPa "
              f"= {100 * p.pet_E_z * eps / 100 / p.pet_sig_z:.0f} % of the Z strength, margin to break {margin:.1f}x")
        assert margin >= MARGIN_CHOSEN
