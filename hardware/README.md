# hardware/

Planned layout (empty so far):

| Directory | Content |
|---|---|
| `kicad/` | the KiCad 10 project: **wiring schematic** of the hand-wired gateway (**no PCB** — decided 2026-11-26), `.kicad_pro`, project library tables, Seeed XIAO symbols/footprints (copied from the previous project's library), `documentations/` (schematic PDF), parts list with TME/Mouser/Farnell status in `kicad/README.md`. The JLCPCB export / iBOM / DRC items only apply if a PCB is added later |
| `enclosure-3d/` | CAD source, STEP, per-part STL (orientation fixed, revision in the name), print profiles and fit-sample log |

Workflow and checks: `../docs/HARDWARE_KICAD.md` (KiCad, LCSC fields, fab export, DRC) and `../docs/ENCLOSURE_3D.md`. Decisions still open (wires vs. pin headers, S3 Plus symbol, BME680 module, antennas, part numbers): `../docs/OPEN_QUESTIONS.md` §3.

Reminders: the schematic is the single source of truth for values and part numbers (fields `Manufacturer`, `MPN`, `TME`, `Mouser`, `Farnell`; sourcing only from those three shops); KiCad files are CRLF (`-text` in `.gitattributes`); close KiCad before scripted edits.

## References

- KiCad documentation: <https://docs.kicad.org/>
- Previous board for reference (same workflow): `../../wireless-esp8266-dap/circuit_ESP32C3_Xiao/`
