#!/usr/bin/env python3
"""Headless JLCPCB export (Gerbers, drill, zip, CPL, BOM) with the "JLCPCB Tools" plugin.

Run it with KiCad's OWN python (it needs `pcbnew` and wx), not with a system python:

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" scripts/kicad_fab_export.py hardware/kicad/gw.kicad_pcb

It mirrors what the plugin's "Generate" button does, minus the GUI, the DRC prompt and
the hooks, and writes next to the board:
    jlcpcb/gerber/                gerber + drill files
    jlcpcb/production_files/      GERBER-<board>.zip, CPL-<board>.csv, BOM-<board>.csv
    jlcpcb/project.db             part assignments (synced from the board's LCSC fields)
The board file itself is never saved.

Why not Fabrication Toolkit? It writes a different layout (production/) and different file
names; the JLCPCB Tools plugin (bouni/kicad-jlcpcb-tools) is the one this project uses.

Before exporting make sure the LCSC fields are right in schematic AND PCB:
    python scripts/kicad_bom_check.py --sch ... --pcb ...
Run DRC separately (the plugin normally does it first):
    kicad-cli pcb drc --severity-error --format report --output drc.txt <board>
"""
import argparse
import ctypes
import glob
import importlib
import json
import logging
import os
import sys
import types

PLUGIN_ID = "com_github_bouni_kicad-jlcpcb-tools"


def documents_dir():
    """The real Documents folder (OneDrive redirection aware)."""
    if sys.platform == "win32":
        try:
            guid = ctypes.c_byte * 16
            folderid = (ctypes.c_ubyte * 16)(0xD0, 0x9A, 0xD3, 0xFD, 0x8F, 0x23, 0xAF, 0x46,
                                             0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
            buf = ctypes.c_wchar_p()
            ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folderid), 0, None, ctypes.byref(buf))
            if buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def find_plugin(explicit=None):
    if explicit:
        return explicit
    roots = [documents_dir(), os.path.join(os.path.expanduser("~"), "Documents"),
             os.environ.get("KICAD_USER_DIR", "")]
    for root in roots:
        hits = sorted(glob.glob(os.path.join(root, "KiCad", "*", "3rdparty", "plugins", PLUGIN_ID)),
                      reverse=True)           # newest KiCad version first
        if hits:
            return hits[0]
    sys.exit(f"plugin {PLUGIN_ID} not found - install it from KiCad's Plugin and Content Manager "
             f"or pass --plugin-dir")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board", help=".kicad_pcb file")
    ap.add_argument("--plugin-dir", help=f"directory of {PLUGIN_ID} (auto-detected by default)")
    ap.add_argument("--no-fill-zones", action="store_true", help="skip refilling copper zones")
    ap.add_argument("--keep-db-lcsc", action="store_true",
                    help="let project.db win over the LCSC fields of the board (the plugin default; "
                         "this script lets the BOARD win, because the board is the source of truth)")
    args = ap.parse_args()

    import pcbnew  # only available in KiCad's python

    board_path = os.path.abspath(args.board)
    plugin_dir = os.path.abspath(find_plugin(args.plugin_dir))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Register the plugin directory as a package WITHOUT running its __init__
    # (which would try to register a KiCad action plugin).
    pkg = types.ModuleType(PLUGIN_ID)
    pkg.__path__ = [plugin_dir]
    sys.modules[PLUGIN_ID] = pkg
    sys.path.append(os.path.join(plugin_dir, "lib"))
    fabrication = importlib.import_module(PLUGIN_ID + ".fabrication")
    store_mod = importlib.import_module(PLUGIN_ID + ".store")
    library_mod = importlib.import_module(PLUGIN_ID + ".library")

    with open(os.path.join(plugin_dir, "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)
    settings.setdefault("general", {})["lcsc_priority"] = not args.keep_db_lcsc
    settings.setdefault("gerber", {})["fill_zones"] = not args.no_fill_zones

    class Parent:                 # the plugin's main window, reduced to what the export touches
        pass

    parent = Parent()
    parent.settings = settings
    parent.project_path = os.path.dirname(board_path)

    board = pcbnew.LoadBoard(board_path)
    parent.library = library_mod.Library(parent)
    parent.store = store_mod.Store(parent, parent.project_path, board)
    fab = fabrication.Fabrication(parent, board)

    warnings = fab.get_part_consistency_warnings()
    print("part consistency warnings:", warnings.strip() if warnings else "none")

    try:
        fab.fill_zones()
    except Exception as exc:      # Refresh() wants a GUI frame; the zones are still filled
        print("fill_zones note:", exc)

    layers = board.GetCopperLayerCount()
    print("copper layers:", layers)
    fab.generate_geber(layers)
    fab.generate_excellon()
    fab.zip_gerber_excellon()
    fab.generate_cpl()
    fab.generate_bom()
    for name, path in fab.get_artifact_paths().items():
        print(f"{name}: {path} ({os.path.getsize(path)} bytes)")
    print("DONE")


if __name__ == "__main__":
    main()
