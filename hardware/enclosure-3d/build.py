"""Regenerate every STL of the enclosure from enclosure.scad / params.scad and check the saved files.

    py -3.12 hardware/enclosure-3d/build.py              # all parts + mesh check
    py -3.12 hardware/enclosure-3d/build.py base lid     # only some parts
    py -3.12 hardware/enclosure-3d/build.py --no-check   # skip the mesh checker
    py -3.12 hardware/enclosure-3d/build.py --antenna B  # base for the outside-antenna variant only

Needs OpenSCAD (2021.01 is enough): default C:\\Program Files\\OpenSCAD\\openscad.exe, or set OPENSCAD.
Output: hardware/enclosure-3d/stl/<name>_<rev>.stl, each in its PRINT orientation (see README).
Takes about one minute (CGAL).  The file names carry `rev` from params.scad.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import scadparams  # noqa: E402

# part selector -> output stem
PARTS = {
    "base":        "enclosure_base",
    "lid":         "enclosure_lid",
    "fit_modules": "fit_sample_modules",
    "fit_antenna": "fit_sample_antenna",
    "fit_name":    "fit_sample_name",
    "fit_snap":    "fit_sample_snap",
    "fit_louvre":  "fit_sample_louvre",
    "fit_mount":   "fit_sample_mount",
}
OUT_DIR = os.path.join(HERE, "stl")


def find_openscad() -> str:
    env = os.environ.get("OPENSCAD")
    if env and os.path.exists(env):
        return env
    for cand in (r"C:\Program Files\OpenSCAD\openscad.exe", r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe"):
        if os.path.exists(cand):
            return cand
    found = shutil.which("openscad")
    if found:
        return found
    raise SystemExit("OpenSCAD not found: install it or set the OPENSCAD environment variable")


def render(exe: str, part: str, out: str, extra: list[str] | None = None) -> float:
    cmd = [exe, "-D", f'part="{part}"'] + (extra or []) + ["-o", out, os.path.join(HERE, "enclosure.scad")]
    t0 = time.time()
    res = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(out):
        sys.stderr.write(res.stdout + res.stderr)
        raise SystemExit(f"OpenSCAD failed for part {part}")
    return time.time() - t0


def main(argv: list[str]) -> int:
    check = "--no-check" not in argv
    names = [a for a in argv if not a.startswith("-") and a in PARTS] or list(PARTS)
    rev = scadparams.load()["rev"]
    exe = find_openscad()
    os.makedirs(OUT_DIR, exist_ok=True)
    produced = []
    for part in names:
        out = os.path.join(OUT_DIR, f"{PARTS[part]}_{rev}.stl")
        dt = render(exe, part, out)
        produced.append(out)
        print(f"{os.path.basename(out):42s} {dt:5.1f} s")
    if check:
        import mesh_check
        bad = 0
        for p in produced:
            rep = mesh_check.check_file(p)
            print(rep.text())
            bad += 0 if rep.ok else 1
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
