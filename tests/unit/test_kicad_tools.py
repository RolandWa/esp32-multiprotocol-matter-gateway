"""Tests for scripts/kicad_lib.py, kicad_set_fields.py and kicad_bom_check.py.

They run on tiny synthetic files that follow KiCad's layout (CRLF line endings,
placed symbols / footprints one tab deep), so no KiCad install and no real design
are needed. The tools were also verified once on a real KiCad 10 project.
"""
import csv
import subprocess
import sys

import pytest

import kicad_lib as kl
from conftest import SCRIPTS_DIR


def sch_symbol(ref, value, fp, lcsc, extra=""):
    return (
        '\t(symbol\n\t\t(lib_id "Device:R")\n\t\t(at 10 10 0)\n\t\t(unit 1)\n'
        "\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n" + extra +
        f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        f'\t\t(property "Value" "{value}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        f'\t\t(property "Footprint" "{fp}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        f'\t\t(property "LCSC" "{lcsc}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        "\t)\n"
    )


def pcb_footprint(ref, value, lcsc):
    return (
        '\t(footprint "Resistor_SMD:R_0603"\n\t\t(layer "F.Cu")\n'
        f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        f'\t\t(property "Value" "{value}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        f'\t\t(property "LCSC" "{lcsc}"\n\t\t\t(at 0 0 0)\n\t\t)\n'
        "\t)\n"
    )


FP = "Resistor_SMD:R_0603"
SCH_PARTS = [("R1", "10k", "C100"), ("R2", "10k", "C100"), ("R3", "22k", "C200")]


def write_crlf(path, text):
    path.write_bytes(text.replace("\n", "\r\n").encode())


@pytest.fixture
def project(tmp_path):
    sch = "(kicad_sch\n\t(version 20250114)\n\t(lib_symbols\n\t\t(symbol \"Device:R\"\n\t\t)\n\t)\n"
    sch += "".join(sch_symbol(r, v, FP, l) for r, v, l in SCH_PARTS)
    sch += sch_symbol("#PWR01", "GND", "", "")                               # power symbol: ignored
    sch += sch_symbol("R9", "1k", FP, "C900", extra="\t\t(in_bom no)\n")     # not in BOM: ignored
    sch += ")\n"
    pcb = "(kicad_pcb\n\t(version 20241229)\n"
    pcb += "".join(pcb_footprint(r, v, l) for r, v, l in SCH_PARTS)
    pcb += pcb_footprint("H1", "MountingHole", "") + ")\n"
    bom = tmp_path / "BOM.csv"
    with open(bom, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Quantity"])
        w.writerow(["10k", "R1,R2", "R_0603", "C100", 2])
        w.writerow(["22k", "R3", "R_0603", "C200", 1])
    write_crlf(tmp_path / "a.kicad_sch", sch)
    write_crlf(tmp_path / "a.kicad_pcb", pcb)
    return tmp_path


def run(script, *args):
    r = subprocess.run([sys.executable, f"{SCRIPTS_DIR}/{script}", *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# --------------------------------------------------------------- kicad_lib

def test_read_detects_crlf_and_normalises(project):
    text, crlf = kl.read_kicad(project / "a.kicad_sch")
    assert crlf is True and "\r" not in text


def test_read_refuses_mixed_line_endings(tmp_path):
    p = tmp_path / "x.kicad_sch"
    p.write_bytes(b"(a)\r\n(b)\n")
    with pytest.raises(ValueError, match="mixed"):
        kl.read_kicad(p)


def test_parts_skips_power_symbols_and_bom_excluded(project):
    text, _ = kl.read_kicad(project / "a.kicad_sch")
    assert sorted(kl.parts(text, "sch")) == ["R1", "R2", "R3"]


def test_bom_groups_group_by_value_footprint_lcsc(project):
    text, _ = kl.read_kicad(project / "a.kicad_sch")
    groups = kl.bom_groups(kl.parts(text, "sch"))
    assert groups[("10k", "R_0603", "C100")] == ["R1", "R2"]
    assert groups[("22k", "R_0603", "C200")] == ["R3"]


def test_set_property_replaces_exactly_one_value():
    block = '(property "LCSC" "C1"\n)\n(property "Value" "x"\n)'
    new, old = kl.set_property(block, "LCSC", "C2")
    assert old == "C1" and '"LCSC" "C2"' in new and '"Value" "x"' in new
    with pytest.raises(KeyError):
        kl.set_property(block, "Nope", "1")


# ---------------------------------------------------------- kicad_set_fields

def test_set_fields_dry_run_changes_nothing(project):
    before = (project / "a.kicad_sch").read_bytes(), (project / "a.kicad_pcb").read_bytes()
    code, out = run("kicad_set_fields.py", "--sch", str(project / "a.kicad_sch"),
                    "--pcb", str(project / "a.kicad_pcb"), "--set", "R3:LCSC=C999")
    assert code == 0 and "dry run" in out
    assert (project / "a.kicad_sch").read_bytes() == before[0]
    assert (project / "a.kicad_pcb").read_bytes() == before[1]


def test_set_fields_apply_edits_both_files_and_keeps_crlf(project):
    sch, pcb = project / "a.kicad_sch", project / "a.kicad_pcb"
    old_sch, old_pcb = sch.read_bytes(), pcb.read_bytes()
    code, out = run("kicad_set_fields.py", "--sch", str(sch), "--pcb", str(pcb),
                    "--set", "R3:LCSC=C999", "--expect", "R3:Value=22k", "--apply")
    assert code == 0, out
    for old, path in ((old_sch, sch), (old_pcb, pcb)):
        new = path.read_bytes()
        assert new.count(b"\n") == new.count(b"\r\n"), "line endings were converted"
        diff = [(a, b) for a, b in zip(old.split(b"\r\n"), new.split(b"\r\n")) if a != b]
        assert len(diff) == 1 and b'"C999"' in diff[0][1], diff


@pytest.mark.parametrize("args", [
    ["--set", "R3:LCSC=X", "--expect", "R3:Value=99k"],     # value is not what the caller expects
    ["--set", "R999:LCSC=X"],                                # unknown reference
    ["--set", "R3:NoSuchField=X"],                           # field does not exist
    ["--set", "R3LCSC"],                                     # malformed argument
])
def test_set_fields_guard_rails_abort_without_writing(project, args):
    before = (project / "a.kicad_sch").read_bytes()
    code, _ = run("kicad_set_fields.py", "--sch", str(project / "a.kicad_sch"), *args, "--apply")
    assert code != 0
    assert (project / "a.kicad_sch").read_bytes() == before


# ----------------------------------------------------------- kicad_bom_check

def check(project, *extra):
    return run("kicad_bom_check.py", "--sch", str(project / "a.kicad_sch"),
               "--pcb", str(project / "a.kicad_pcb"), "--bom", str(project / "BOM.csv"), *extra)


def test_bom_check_passes_on_consistent_files(project):
    code, out = check(project)
    assert code == 0, out
    assert "3 schematic parts checked, 0 error(s)" in out


def test_bom_check_reports_schematic_pcb_lcsc_mismatch(project):
    run("kicad_set_fields.py", "--sch", str(project / "a.kicad_sch"), "--set", "R3:LCSC=C999", "--apply")
    code, out = check(project)
    assert code == 1
    assert "R3: LCSC differs" in out and "C999" in out


def test_bom_check_reports_value_mismatch(project):
    run("kicad_set_fields.py", "--pcb", str(project / "a.kicad_pcb"), "--sch", str(project / "a.kicad_sch"),
        "--set", "R1:Value=47k", "--apply")
    code, out = check(project)
    assert code == 1 and "47k" in out


def test_bom_check_reports_bom_quantity_error(project):
    rows = list(csv.reader(open(project / "BOM.csv")))
    rows[1][4] = "3"
    csv.writer(open(project / "BOM.csv", "w", newline="")).writerows(rows)
    code, out = check(project)
    assert code == 1 and "quantity 3, expected 2" in out


def test_bom_check_reports_missing_bom_row(project):
    rows = list(csv.reader(open(project / "BOM.csv")))[:2]
    csv.writer(open(project / "BOM.csv", "w", newline="")).writerows(rows)
    code, out = check(project)
    assert code == 1 and "missing row '22k'" in out


def test_bom_check_requires_lcsc_numbers(project):
    run("kicad_set_fields.py", "--sch", str(project / "a.kicad_sch"), "--pcb", str(project / "a.kicad_pcb"),
        "--set", "R3:LCSC=", "--apply")
    code, out = run("kicad_bom_check.py", "--sch", str(project / "a.kicad_sch"))
    assert code == 1 and "R3: no LCSC number" in out
    code, out = run("kicad_bom_check.py", "--sch", str(project / "a.kicad_sch"), "--allow-missing-lcsc")
    assert code == 0 and "WARNING" in out


def test_bom_check_flags_part_missing_from_pcb(project):
    text, crlf = kl.read_kicad(project / "a.kicad_pcb")
    text = text.replace(pcb_footprint("R3", "22k", "C200"), "")
    kl.write_kicad(project / "a.kicad_pcb", text, crlf)
    code, out = check(project)
    assert code == 1 and "R3: in the schematic but not on the PCB" in out
