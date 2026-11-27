# scripts/

Helpers that encode what was learned on the previous project. Run from the **repository root** unless noted. "Verified" says how each
was tested on 2026-11-25; anything not listed as verified is untested.

| Script | Purpose | Verified how |
|---|---|---|
| `wsl_idf.sh` | Build an ESP-IDF project that lives on the Windows file system, inside WSL: rsync to a clean path, python shim, `export.sh` without `set -u`, optional `--extra-export` (esp-matter), optional `--tools-path` (own `IDF_TOOLS_PATH` for the side-by-side IDF v6, exported in the subshell only; added 2026-11-27, verified by the RCP and host builds), a sibling `firmware/common` mirrored to `~/work/src/common`, `set-target` once per build dir, optional merged image (`--merge`), per-`(IDF, target)` build dirs. Notes when `dependencies.lock` needs pinning | built the previous project's ESP32-C3 firmware through `build.bat` with a path containing spaces/commas: image size identical to the old build script's (786 384 B), 106 B differ (embedded paths/timestamps); `--extra-export` marker test; early failure on a bad path; `bash -n` + LF check in pytest |
| `build.bat` | Windows wrapper: converts its own path with `wslpath`, passes every argument to `wsl_idf.sh` | same run as above (invoked from PowerShell as `& .\scripts\build.bat …`) |
| `flash.bat` | `esptool write-flash` of a merged image; chip → offset (0x0, or 0x1000 for esp32/esp32s2); **port is mandatory**; `DRY_RUN=1` prints the command | dry-run unit tests for 6 chips + argument errors. **Never run against a board** |
| `detect_port.py` | lists Espressif USB serial ports with VID:PID and USB serial number; `--serial`, `--last`, `--chip-id` | exit-code tests; run on this PC's COM ports (`--vid 0`: table, `--last`, unknown `--serial` → exit 1). No Espressif board was attached, so VID/serial output for real XIAO boards and `--chip-id` were **not** seen |
| `kicad_lib.py` | CRLF-safe reading/patching of KiCad 9/10 files; placed symbols/footprints, BOM grouping | unit tests (synthetic files) + run on real KiCad 10 files |
| `kicad_set_fields.py` | set `LCSC`/`TME`/… fields of parts in schematic **and** PCB; dry run by default; guards; byte-exact | unit tests; on real files: exactly 2 changed lines per file, CRLF preserved |
| `kicad_bom_check.py` | schematic ↔ PCB ↔ BOM consistency, exit 1 on difference | unit tests; real project: 37 parts, 0 errors; broken copy: 3 errors |
| `kicad_fab_export.py` | headless JLCPCB export (Gerbers, drill, zip, CPL, BOM) via the JLCPCB Tools plugin; run with **KiCad's python** | real project's PCB: BOM and CPL identical to the plugin GUI's, Gerber zip of the same size |

Typical sessions are in `docs/BUILD_AND_FLASH.md` (build/flash) and `docs/HARDWARE_KICAD.md` (KiCad). Tests: `python -m pytest tests/unit -v`.

Conventions: Python 3 standard library only (+ `pyserial` for `detect_port.py`); `.sh` and `Makefile` files must keep **LF**, `.bat` files **CRLF** (`.gitattributes`);
scripts never write outside the paths given on the command line; destructive/real-hardware actions are explicit (`--apply`, mandatory port).

## References

- ESP-IDF build system: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/build-system.html>
- esptool: <https://docs.espressif.com/projects/esptool/>
- KiCad CLI and file formats: <https://docs.kicad.org/>, <https://dev-docs.kicad.org/en/file-formats/>
- JLCPCB Tools plugin: <https://github.com/Bouni/kicad-jlcpcb-tools>
