#!/usr/bin/env python3
"""Consistency check: KiCad schematic <-> PCB <-> JLCPCB BOM.

The schematic is the source of truth. Checks (exit code 1 on any error):
  1. every schematic part has a LCSC number (warning only with --allow-missing-lcsc)
  2. schematic and PCB agree on Value and LCSC for every reference
  3. (with --bom) the exported BOM CSV equals the schematic grouping:
     same value / designators / footprint / quantity / LCSC per row

Usage:
    python scripts/kicad_bom_check.py --sch hardware/kicad/gw.kicad_sch --pcb hardware/kicad/gw.kicad_pcb \\
        [--bom hardware/kicad/jlcpcb/production_files/BOM-gw.csv]
"""
import argparse
import csv
import sys

import kicad_lib as kl


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sch", required=True)
    ap.add_argument("--pcb")
    ap.add_argument("--bom")
    ap.add_argument("--allow-missing-lcsc", action="store_true")
    args = ap.parse_args()

    sch = kl.parts(kl.read_kicad(args.sch)[0], "sch")
    errors, warnings = [], []

    for ref, p in sorted(sch.items()):
        if not p.get("LCSC"):
            (warnings if args.allow_missing_lcsc else errors).append(f"{ref}: no LCSC number in the schematic")

    if args.pcb:
        pcb = kl.parts(kl.read_kicad(args.pcb)[0], "pcb")
        for ref in sorted(set(sch) | set(pcb)):
            if ref not in pcb:
                errors.append(f"{ref}: in the schematic but not on the PCB (update PCB from schematic)")
            elif ref not in sch:
                if pcb[ref].get("LCSC"):      # mounting holes etc. have no LCSC and are ignored
                    errors.append(f"{ref}: on the PCB but not in the schematic BOM")
            else:
                for field in ("Value", "LCSC"):
                    if sch[ref].get(field, "") != pcb[ref].get(field, ""):
                        errors.append(f"{ref}: {field} differs - schematic {sch[ref].get(field)!r} "
                                      f"vs PCB {pcb[ref].get(field)!r}")

    if args.bom:
        want = {(v, ",".join(refs), fp, lc): len(refs) for (v, fp, lc), refs in kl.bom_groups(sch).items()}
        got = {}
        with open(args.bom, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["Comment"], ",".join(sorted(r["Designator"].split(","))), r["Footprint"], r["LCSC"])
                got[key] = int(r["Quantity"])
        for key, qty in sorted(want.items()):
            if key not in got:
                errors.append(f"BOM is missing row {key[0]!r} [{key[1]}] LCSC {key[3] or '-'}")
            elif got[key] != qty:
                errors.append(f"BOM row {key[0]!r} [{key[1]}]: quantity {got[key]}, expected {qty}")
        for key in sorted(set(got) - set(want)):
            errors.append(f"BOM has a row that is not in the schematic: {key[0]!r} [{key[1]}] LCSC {key[3] or '-'}")

    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:  ", e)
    print(f"{len(sch)} schematic parts checked, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
