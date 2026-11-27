"""Tiny helpers for reading/patching KiCad 9/10 s-expression files without KiCad.

Verified on KiCad 10 files (schematic format 2025, PCB version 20241229). Limits:
* flat schematics only - a hierarchical design needs the sub-sheet files passed too;
* placed symbols / footprints are found by their indentation (one tab), the way KiCad
  writes them; it is a text tool, not a full s-expression parser.

KiCad on Windows writes CRLF line endings. Always go through read_kicad()/write_kicad()
so a patch never converts a whole file (that would turn a 10-line change into a
full-file diff).
"""
import re
from collections import defaultdict

PROP_RE = re.compile(r'\(property "([^"]+)" "([^"]*)"')


def read_kicad(path):
    """Return (text with LF line endings, was_crlf)."""
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    if crlf:
        if raw.count("\r\n") != raw.count("\n"):
            raise ValueError(f"{path}: mixed line endings, refusing to touch it")
        raw = raw.replace("\r\n", "\n")
    return raw, crlf


def write_kicad(path, text, crlf):
    if crlf:
        text = text.replace("\n", "\r\n")
    open(path, "wb").write(text.encode("utf-8"))


_SYMBOL_BLOCK = re.compile(r"\n\t\(symbol\n.*?\n\t\)(?=\n)", re.S)
_FOOTPRINT_BLOCK = re.compile(r"\n\t\(footprint\s.*?\n\t\)(?=\n)", re.S)


def blocks(text, kind):
    """Yield (match, props) for every placed symbol ('sch') or footprint ('pcb')."""
    rx = _SYMBOL_BLOCK if kind == "sch" else _FOOTPRINT_BLOCK
    for m in rx.finditer(text):
        yield m, dict(PROP_RE.findall(m.group(0)))


def parts(text, kind):
    """Return {reference: props} of the real parts (no power symbols, no virtual parts).

    For the schematic, parts that are excluded from the BOM or marked DNP are skipped.
    """
    out = {}
    for m, props in blocks(text, kind):
        ref = props.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        body = m.group(0)
        if kind == "sch":
            flags = dict(re.findall(r"\((in_bom|dnp)\s+(yes|no)\)", body))
            if flags.get("in_bom") == "no" or flags.get("dnp") == "yes":
                continue
            if not props.get("Footprint"):
                continue
        out[ref] = props
    return out


def bom_groups(part_map):
    """Group parts like the JLCPCB BOM: (value, footprint-name, lcsc) -> [refs]."""
    groups = defaultdict(list)
    for ref, p in part_map.items():
        fp = p.get("Footprint", "").split(":")[-1]
        groups[(p.get("Value", ""), fp, p.get("LCSC", ""))].append(ref)
    return {k: sorted(v) for k, v in groups.items()}


def set_property(block_text, field, value):
    """Replace the value of an existing property inside one symbol/footprint block."""
    pat = re.compile(r'(\(property "' + re.escape(field) + r'" ")([^"]*)(")')
    found = pat.findall(block_text)
    if len(found) != 1:
        raise KeyError(f"property {field!r}: {len(found)} matches (add it in KiCad first)")
    return pat.sub(lambda m: m.group(1) + value + m.group(3), block_text), found[0][1]
