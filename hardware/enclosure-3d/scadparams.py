"""Read hardware/enclosure-3d/params.scad into Python (single source of truth for all dimensions).

params.scad only holds statements of the form   name = <expression>;   (several per line allowed,
optional trailing // comment).  Expressions are evaluated in order with OpenSCAD semantics for the
few functions used (trigonometry in DEGREES).  Nothing is duplicated: the assembly check, the
preview and the README table are all derived from this file.

    py -3.12 scadparams.py            # print every parameter
    py -3.12 scadparams.py --table    # markdown table: name | value | source / comment
    py -3.12 scadparams.py --assumed  # only the "ASSUMED - verify" ones
"""
from __future__ import annotations

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_FILE = os.path.join(HERE, "params.scad")

_STMT = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$")


def _statements(path):
    """Yield (name, expr, comment) for every `name = expr;` in the file."""
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            code, _, com = raw.rstrip("\n").partition("//")
            for part in code.split(";"):
                m = _STMT.match(part)
                if m:
                    yield m.group(1), m.group(2), com.strip()


def _env():
    return {
        "cos": lambda d: math.cos(math.radians(d)),
        "sin": lambda d: math.sin(math.radians(d)),
        "tan": lambda d: math.tan(math.radians(d)),
        "sqrt": math.sqrt, "min": min, "max": max, "abs": abs,
        "true": True, "false": False, "__builtins__": {},
    }


def load(path: str = PARAMS_FILE, with_comments: bool = False, overrides: dict | None = None):
    """Return dict name -> value (and, optionally, name -> comment text, ordered name list).

    `overrides` replaces the *raw* value of a name before the derived ones are evaluated, e.g.
    load(overrides={"hdr_h": 8.5}) re-derives everything that depends on it.
    """
    env = _env()
    comments: dict[str, str] = {}
    order: list[str] = []
    for name, expr, com in _statements(path):
        if overrides and name in overrides:
            env[name] = overrides[name]
        else:
            env[name] = eval(expr, env)      # noqa: S307 - trusted repo file, restricted env
        comments[name] = com
        order.append(name)
    values = {k: env[k] for k in order}
    if with_comments:
        return values, comments, order
    return values


class P:
    """Attribute access:  P().Lo   (optionally P(overrides={"ant_mode": 1}))"""

    def __init__(self, path: str = PARAMS_FILE, overrides: dict | None = None):
        self.__dict__.update(load(path, overrides=overrides))


def main(argv):
    vals, com, order = load(with_comments=True)
    if "--table" in argv or "--assumed" in argv:
        only = "--assumed" in argv
        print("| Parameter | Value | Source / comment |")
        print("|---|---|---|")
        for k in order:
            if only and "ASSUMED" not in com[k]:
                continue
            v = vals[k]
            v = f"{v:.4g}" if isinstance(v, float) else str(v)
            print(f"| `{k}` | {v} | {com[k].replace('|', '/')} |")
        return 0
    for k in order:
        print(f"{k} = {vals[k]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
