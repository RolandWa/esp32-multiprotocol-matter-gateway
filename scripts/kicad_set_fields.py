#!/usr/bin/env python3
"""Set property fields (LCSC, TME, Value, ...) of parts in a KiCad schematic AND PCB.

The JLCPCB export reads the LCSC field from the PCB footprints, the BOM check reads it
from the schematic - they must agree, so this tool edits both in one run. It is a
dry run unless --apply is given, asserts that every reference matches exactly one block
and (optionally) that the current Value is what you expect, and preserves CRLF endings.

Usage:
    python scripts/kicad_set_fields.py --sch hardware/kicad/gw.kicad_sch --pcb hardware/kicad/gw.kicad_pcb \\
        --set R4:LCSC=C114065 --set R4:TME=RC0603FR-0722KL --expect R4:Value=22k [--apply]

Close the files in KiCad first (or reload them afterwards): KiCad would overwrite the change.
"""
import argparse
import sys

import kicad_lib as kl


def parse_pairs(items, what):
    out = []
    for item in items:
        try:
            ref, rest = item.split(":", 1)
            field, value = rest.split("=", 1)
        except ValueError:
            sys.exit(f"bad {what} {item!r}, expected REF:FIELD=VALUE")
        out.append((ref, field, value))
    return out


def patch(path, kind, sets, expects, apply):
    text, crlf = kl.read_kicad(path)
    for ref, field, want in expects:
        parts = kl.parts(text, kind)
        if ref not in parts:
            sys.exit(f"{path}: {ref} not found")
        have = parts[ref].get(field)
        if have != want:
            sys.exit(f"{path}: {ref} {field} is {have!r}, expected {want!r} - aborting")
    changed = 0
    for ref, field, value in sets:
        hits = [m for m, props in kl.blocks(text, kind) if props.get("Reference") == ref]
        if len(hits) != 1:
            sys.exit(f"{path}: {ref} matches {len(hits)} blocks (need exactly 1)")
        m = hits[0]
        try:
            new_block, old = kl.set_property(m.group(0), field, value)
        except KeyError as exc:
            sys.exit(f"{path}: {ref}: {exc}")
        print(f"{path.split('/')[-1].split(chr(92))[-1]}: {ref:<6} {field:<6} {old!r} -> {value!r}")
        text = text[:m.start()] + new_block + text[m.end():]
        changed += old != value
    if apply:
        kl.write_kicad(path, text, crlf)
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sch", required=True)
    ap.add_argument("--pcb", help="PCB file (recommended: JLCPCB export reads LCSC from here)")
    ap.add_argument("--set", action="append", default=[], metavar="REF:FIELD=VALUE")
    ap.add_argument("--expect", action="append", default=[], metavar="REF:FIELD=VALUE",
                    help="abort unless the current value matches (checked in every file)")
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    args = ap.parse_args()
    if not args.set:
        ap.error("nothing to do: give at least one --set")

    sets = parse_pairs(args.set, "--set")
    expects = parse_pairs(args.expect, "--expect")
    n = patch(args.sch, "sch", sets, expects, args.apply)
    if args.pcb:
        n += patch(args.pcb, "pcb", sets, expects, args.apply)
    print(("applied" if args.apply else "dry run only (use --apply)") + f" - {n} field(s) differ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
