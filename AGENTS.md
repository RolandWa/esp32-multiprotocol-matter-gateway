# Agent instructions — esp32-multiprotocol-matter-gateway

Read this file first, then the document that matches your task (index at the bottom).
It was written on 2026-11-25 from the experience of an earlier, finished-enough project
(`../wireless-esp8266-dap`, a wireless CMSIS-DAP probe on ESP8266/ESP32-C3/S3 with its own KiCad
board). Everything marked **verified** was checked on this machine; everything marked
**unverified** came from an AI-generated research PDF or from memory and must be confirmed
against a datasheet / official source before you build on it.

---

## 1. The project

A local multi-protocol smart-home gateway with **no external server**: it brings **Wi-Fi, BLE and
Zigbee 3.0** devices to **Amazon Alexa as a Matter bridge**, plus a **Bosch BME680** environment sensor
(temperature, humidity, pressure, IAQ for "time to ventilate"). Full intent and requirements: `project_specification_and_requirements.md`
(merged from the owner's draft README and the Gemini session, Polish; numbers unverified). Architecture — **dual SoC**, so the 2.4 GHz radio is never time-shared
between Wi-Fi/BLE and Zigbee:

```text
Alexa --Matter over Wi-Fi--> Module 1: Seeed XIAO ESP32-S3 Plus (host, esp-matter, Wi-Fi + BLE, U.FL antenna #1)
                                 |-- UART (TX, RX, RTS, CTS) --> Module 2: Seeed XIAO ESP32-C6 (802.15.4 RCP only, U.FL antenna #2)
                                 '-- I2C --> Bosch BME680 (+ BSEC, closed-source library)
```

Deliverables: **firmware for two chips**, a **KiCad design** (two processors) and a **3D-printed enclosure**.
Status when this file was written: nothing is built yet. Material in the repo: `project_specification_and_requirements.md` (the requirements; replaces the former `repository_readme.md` and the planned `SPECIFICATION.md`), `Bramka Smarthome na ESP32-C6.pdf` (AI chat export,
**unverified**), `wytyczne_projektowania_druk3d (1).md` (the owner's 3D-printing checklist, trust it).

## 1a. Findings that constrain the work (as of 2026-11-25)

Check this table before planning anything; details and options are in `docs/OPEN_QUESTIONS.md`. Do not "solve" an open item silently — raise it with the owner.

| # | Finding | Consequence for you | Status |
|---|---|---|---|
| 1 | **IDF v4.4.2 has no ESP32-C6 support** (verified in its `components/soc`). `~/esp/esp-idf` in WSL is an untagged v6.1-dev checkout whose Xtensa toolchain (for the S3) is not installed | No firmware work before an IDF tag is chosen **together with the esp-matter release** (sources disagree: v1.4.1 registry page → IDF v5.2.3, GitHub main → v6.0.2). Install it side by side (`docs/ENVIRONMENT.md` §4); never touch `~/esp/esp-idf-v4.4.2` (old project) | **open, blocks firmware** |
| 2 | **Is the C6 a supported RCP for Espressif's `zigbee_bridge`?** An old GitHub issue says the example did not support the C6; official material shows an ESP32-H2 RCP; the PDF says the C6 works. The XIAO H2 has no U.FL | Read the example's README/`sdkconfig.defaults` on the chosen esp-matter branch and Espressif's `esp-zigbee-sdk` RCP example for the C6. **Do not recommend ordering a PCB before the C6 RCP is proven on dev boards** | **open, unverified** |
| 3 | **Licence mismatch:** `LICENSE` is GPL-3.0, the draft README says MIT. **Bosch BSEC is proprietary** (binary-only, own redistribution terms) | Do not edit `LICENSE`; do not publish binaries containing BSEC before the owner decided and read BSEC's terms | **open** |
| 4 | **Decided 2026-11-26: no PCB.** Two XIAO modules + BME680 board are hand-wired (wires or pin headers) in one 3D-printed enclosure; power only via the host's USB-C (host 5V pad → C6 5V pad); host drives C6 EN/BOOT; larger external antennas; parts only from **TME, Mouser, Farnell**. KiCad holds a wiring schematic (`hardware/kicad/`, draft v0.2). The Seeed library has the plain XIAO ESP32-S3, **not the S3 Plus** (placeholder used) | Do not design a PCB or add LCSC/JLCPCB steps unless the owner asks. Open: wires vs. headers, VBUS→5V-pad behaviour (back-feed), S3 Plus symbol, BME680 module, antennas, part numbers (`hardware/kicad/README.md`) | partly open |
| 5 | `project_specification_and_requirements.md` (Gemini + former README) holds **unverified** numbers and a hand-typed wiring table | Re-check it after #1–#4 are decided; generate/check its wiring table against the pin header and the schematic | open |
| 6 | The PDF (`Bramka Smarthome na ESP32-C6.pdf`) is an AI chat export; memory sizes, currents, antenna spacing, RF-switch pins (C6 GPIO3/GPIO14), Zigbee/Wi-Fi channel advice are **unverified** | Verify each against datasheets/Seeed wiki before use and record the source in `## References` | standing rule |
| 7 | ADC facts (verified in IDF headers): S3 has 2 ADC units (10+10 ch), **C6 has 1 (ADC1, GPIO0–6)**; ADC2 is unusable with Wi-Fi; `ADC1_CHANNEL_2` is a different GPIO on every chip. The product itself needs no ADC (BME680 is I2C) | Per-target pin header + pin-conflict unit test; ADC1 only (`docs/MCU_NOTES.md`, `docs/CODING_GUIDELINES.md` §3) | rule |
| 8 | **What the helper scripts do and do not prove:** build/KiCad/test scripts were run on the old project's real files; `flash.bat` was only dry-run (no board), `detect_port.py` never saw a real XIAO | Treat the first real flash and the first port listing as unverified; report their outcome | until first hardware session |

## 2. Working agreement with the owner (follow exactly)

1. **Language:** the owner writes Polish. Answer in Polish. Code, comments, commit messages and these docs are English.
2. **Never `git commit` or `git push` (or move/delete tags) without the owner's explicit approval** for that action.
   Read-only git (`status`, `diff`, `log`) is always fine. Before asking: summarise the change and propose the commit
   message. Prefer **logical commits** (e.g. firmware+tests+docs separate from regenerated production files).
3. **Identity:** commits and generated files use the owner's first name only (git author "Roland"). Do **not**
   write the owner's surname, employer, or e-mail address into commits, code, docs or file headers.
4. **Application code:** do not change firmware behaviour on your own initiative — propose, then implement what was
   approved. Comment/doc fixes that follow an approved change are fine.
5. **Report honestly.** Say what was run and what was only built or only read. "Builds" is not "works on hardware".
   Keep a "hardware check pending" list instead of ticking things off. A test that passes on the first run is suspect:
   do a quick mutation check (break the code, see the test fail).
6. **The KiCad schematic is the single source of truth** for component values and part numbers. Do not copy values into
   five documents; link to the schematic or generate from it (a 100 R vs 22 k disagreement cost a week in the old project).
7. **Never trust the PDF/AI research blindly.** It contains useful ideas and several unverified numbers; check each against
   the Espressif/Seeed/Bosch documentation and record the source in a `## References` section.
8. **Keep the repository root clean.** Scripts → `scripts/`, docs → `docs/`, firmware → `firmware/`, hardware → `hardware/`.
   Every new/updated document gets a `## References` section (primary sources: datasheets, vendor docs, standards by number).
9. **Back up before overwriting a known-good artefact** (a flashed `.bin`, a fabrication package) — builds overwrite them.
10. Ask when a decision is the owner's (see `docs/OPEN_QUESTIONS.md`); otherwise pick the conventional option and say so.
11. **Never damage the old project's toolchain** (`wireless-esp8266-dap`: IDF v4.4.2, Python 3.10, its `~/.espressif` tools). It must keep building. New IDF / esp-matter / esp-zigbee-sdk go in separate directories with their own `IDF_TOOLS_PATH`; no global `IDF_PATH`/`PATH`/`python3`/cmake changes; capture a baseline before and rebuild the old project after any environment change. Full rules: `project_specification_and_requirements.md` §4A.
12. **In doubt about build/environment/scripts, check how the old project does it first** (`../wireless-esp8266-dap`: `build_WSL.py`, `.github/workflows/main.yml`, `sdkconfig.defaults.*`, `docs/build_wsl.md`) — it works and builds correctly, so it is the reference. **Read-only: change nothing in that project** (no edits, no git writes, no building in its directory). Deviate only with a stated reason. Rules: `project_specification_and_requirements.md` §4A item 9.

## 3. Repository layout

| Path | Content |
|---|---|
| `firmware/host-esp32s3/` | host app. **Builds (2026-11-27)**: esp-matter `zigbee_bridge` baseline + 3 small gateway changes; BLE scanner, Matter sensor endpoints, BME680/BSEC not written yet (`firmware/host-esp32s3/README.md`) |
| `firmware/rcp-esp32c6/` | 802.15.4 RCP for the C6: Espressif's `ot_rcp` + `OPENTHREAD_NCP_VENDOR_HOOK=y`. **Builds**, never run on a board |
| `firmware/common/` | **pure C, no ESP-IDF includes** — BTHome parser, unit conversions, ventilation hysteresis, report gate, sensor table, RCP supervisor (`firmware/README.md`). Host-unit-tested; the template `example_sat.*` was deleted |
| `hardware/kicad/` | *(planned)* KiCad project (+ `jlcpcb/` export, `bom/ibom.html`) |
| `hardware/enclosure-3d/` | OpenSCAD source (`params.scad` = all dimensions), `build.py` regenerates the STLs, mesh/assembly checks, previews. **rev03 ACCEPTED by the owner as the concept 2026-11-27 (R1-R17 of `docs/ENCLOSURE_3D.md` §3a: 78.8 x 69.5 x 30.5 mm, snap-fit lid, no screws, one USB-C opening in the bottom wall, engraved name, two hanging holes on one horizontal line 36 mm apart with drilling marks): computed, not printed, C6 board assumed equal to the S3, RF and thermal unmeasured; only the latest STLs are committed; old revisions are not kept in git (the rev02 mutation tests skip without a local `stl/archive_rev02`)** (`hardware/enclosure-3d/README.md`; `render_outer.py` draws the outside) |
| `scripts/` | verified helpers: WSL build, flash, KiCad checks/export (see `scripts/README.md`) |
| `tests/unit/` | hardware-free tests (C harness + pytest). `tests/hw/` *(planned)* hardware tests, never collected by default |
| `docs/` | the knowledge base (index below) |

## 4. Environment that works (verified 2026-11-25) — details in `docs/ENVIRONMENT.md`

* **Windows 11 + WSL2 (Ubuntu 26.04)**. ESP-IDF lives **only in WSL**; Windows runs Python 3.12 (pytest, pyserial, esptool 5.3.1),
  KiCad 10 and 9 (**the owner's GUI is KiCad 9: write files in KiCad 9 format, version 20250114, symbols from the 9.0 library; verify with the 9.0 `kicad-cli`**), Git, `gh`, VS Code.
* The repo sits in a **OneDrive folder whose path contains spaces and commas**. ESP-IDF/cmake cannot build there →
  `scripts/wsl_idf.sh` rsyncs the project to `~/work/src/<name>` and builds in `~/work/build/<name>/<idf>-<target>`.
* **IDF v4.4.2 is NOT usable for this project** (verified: no ESP32-C6 support). A newer IDF is needed, chosen together with
  the `esp-matter` release (open decision, `docs/OPEN_QUESTIONS.md`). The IDF at `~/esp/esp-idf` is an untagged
  **v6.1-dev** checkout whose Xtensa toolchain (needed for the S3) is **not installed**; `~/esp/esp-idf-v4.4.2` belongs to the old project — leave it alone.
* Flash **from Windows** (`esptool`), not from WSL (USB is not visible in WSL). Both XIAO boards share USB VID `0x303A`:
  always pass the COM port explicitly; identify boards by USB serial number.
* KiCad files are **CRLF**; use `scripts/kicad_*.py` for byte-exact edits. Fabrication export is headless via KiCad's own Python.

## 5. Commands (from the repository root, PowerShell)

```powershell
# unit tests, no hardware (C via gcc in WSL + pytest)                       -> docs/TESTING.md
python -m pytest tests/unit -v

# build a firmware image in WSL (separate build dir per IDF+target)          -> docs/BUILD_AND_FLASH.md
# forward slashes in --project and a QUOTED ~ (PowerShell eats both otherwise: docs/LESSONS_LEARNED.md)
& .\scripts\build.bat --project firmware/host-esp32s3 --target esp32s3 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --extra-export '~/esp/esp-matter/export.sh' --merge
& .\scripts\build.bat --project firmware/rcp-esp32c6  --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --merge

# flash (port is mandatory; DRY_RUN=1 only prints the command)
python scripts\detect_port.py                 # list Espressif USB ports (add --chip-id to ask esptool)
& .\scripts\flash.bat esp32s3 COM12 dist\esp32s3\host-esp32s3_full.bin

# KiCad consistency + production export                                     -> docs/HARDWARE_KICAD.md
python scripts\kicad_bom_check.py --sch hardware\kicad\gw.kicad_sch --pcb hardware\kicad\gw.kicad_pcb --bom hardware\kicad\jlcpcb\production_files\BOM-gw.csv
& "C:\Program Files\KiCad\10.0\bin\python.exe" scripts\kicad_fab_export.py hardware\kicad\gw.kicad_pcb
```

PowerShell/bash traps (all cost time before): use `& .\x.bat args`, never `cmd /c "x.bat args"`; `bash` on a Windows `PATH`
is WSL's bash and does not understand `C:\` paths; Git Bash rewrites `/mnt/...` arguments; put WSL commands in a script file
and run `wsl bash <file>`; do not use `set -u` around ESP-IDF's `export.sh`. Full list: `docs/LESSONS_LEARNED.md`.

## 6. Definition of done for a change

(Items marked "open" in §1a are not yours to decide — if a change depends on one, say so and stop at what can be done safely.)


1. `python -m pytest tests/unit` green (includes the C tests with ASan/UBSan).
2. New logic is in `firmware/common/` with a unit test; a mutation check was done for new tests.
3. **Both** firmware images build (`host-esp32s3` and `rcp-esp32c6`), warnings from your files reviewed.
4. If KiCad files changed: `kicad_bom_check.py` clean, DRC reviewed, production package/iBOM regenerated and committed separately.
5. Docs updated (single source of truth, `## References`), hardware checks that still need a board listed.
6. You told the owner what was *not* verified. You did not commit or push.

## 7. Document index

| File | Read when |
|---|---|
| `docs/ENVIRONMENT.md` | installing/repairing the toolchain, versions, adding an ESP-IDF version |
| `docs/BUILD_AND_FLASH.md` | compiling, merged images, flashing two boards, serial monitor |
| `docs/TESTING.md` | unit / regression / hardware test strategy, mutation checks, CI idea |
| `docs/CODING_GUIDELINES.md` | writing firmware: pure-logic split, pins, protocols, secrets, style |
| `docs/HARDWARE_KICAD.md` | schematic/PCB workflow, LCSC fields, fab export, DRC, design rules for this board |
| `docs/ENCLOSURE_3D.md` | enclosure design and print rules |
| `docs/MCU_NOTES.md` | ESP32-S3/C6/C3/ESP32 facts: ADC, pins, IDF support, XIAO pinouts |
| `docs/LESSONS_LEARNED.md` | symptom → cause → fix table from the previous project |
| `docs/OPEN_QUESTIONS.md` | decisions the owner still has to make |
| `scripts/README.md` | what each helper does and how it was verified |

## References

- ESP-IDF programming guide: <https://docs.espressif.com/projects/esp-idf/>
- esp-matter: <https://github.com/espressif/esp-matter> — programming guide: <https://docs.espressif.com/projects/esp-matter/>
- Seeed XIAO ESP32 Matter environment: <https://wiki.seeedstudio.com/xiao_esp32_matter_env/>
- Previous project (sibling folder, same author): `../wireless-esp8266-dap` — `AGENTS.md`/`.github/copilot-instructions.md`, `docs/`, `tests/unit/`
