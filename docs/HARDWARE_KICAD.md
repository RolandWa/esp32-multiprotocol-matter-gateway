# Hardware: KiCad workflow and design notes

The electrical design (KiCad, **two processors**) will live in `hardware/kicad/`. This page is the workflow that worked on the
previous project's board (an ESP32-C3 XIAO carrier with a programmable power rail, ordered from JLCPCB with SMT assembly) plus the
design constraints known for this product. Facts marked **verified** were checked on 2026-11-25; **unverified** = from the AI-generated PDF
or memory.

## 1. Files and tools (verified)

* **The GUI the owner uses is KiCad 9.0**; 10.0 is also installed. Write files in the **KiCad 9 format** (schematic `version 20250114`, generator "9.0") and take library
  symbols from `C:\Program Files\KiCad\9.0\share\kicad\symbols` — symbols copied from the 10.0 library carry tokens (`in_pos_files`, `show_name`, …) that KiCad 9 rejects
  ("Expecting pin_names, pin_numbers, …"), although the 10.0 `kicad-cli` accepts them (hit on 2026-11-26). Check files with the **9.0** `kicad-cli`.
* KiCad 10.0 / 9.0: files are written with **CRLF** line endings (PCB `version 20241229`). `scripts/kicad_lib.py` patches them
  byte-exactly. *Close the project in KiCad before running a script that edits its files* (KiCad would overwrite the change on save).
* Keep one KiCad project in `hardware/kicad/` with: schematic, PCB, `*.kicad_pro`, custom DRC rules `*.kicad_dru`, project symbol/footprint
  tables, `jlcpcb/` (export), `bom/ibom.html`, and `documentations/` (PDF/SVG/PNG of the schematic).
* `.gitattributes` marks KiCad files `-text` so git never normalises them; `.gitignore` excludes `*-backups/`, `fp-info-cache`, `*.kicad_prl`.
* **The schematic is the single source of truth** for values, footprints and part numbers.

## 2. LCSC / TME fields must be right in BOTH schematic and PCB

The JLCPCB export reads LCSC numbers from the **PCB footprints' fields**; people review the **schematic**. The previous project shipped a BOM with
the wrong parts because five resistors/one capacitor had new values but the old part numbers in both files.

```powershell
# edit both files in one go (dry run unless --apply; guards against wrong references/values; keeps CRLF)
python scripts\kicad_set_fields.py --sch hardware\kicad\gw.kicad_sch --pcb hardware\kicad\gw.kicad_pcb `
       --set R4:LCSC=C114065 --set R4:TME=RC0603FR-0722KL --expect R4:Value=22k --apply

# schematic <-> PCB <-> BOM consistency (exit 1 on any difference); run before every export
python scripts\kicad_bom_check.py --sch hardware\kicad\gw.kicad_sch --pcb hardware\kicad\gw.kicad_pcb `
       --bom hardware\kicad\jlcpcb\production_files\BOM-gw.csv
```

Both tools are unit-tested on synthetic files (`tests/unit/test_kicad_tools.py`) and were run on the previous project's real KiCad 10 files
(37 parts, 0 differences; a deliberately broken copy produced 3 errors; an edit changed exactly 2 lines per file).

## 3. Production export (JLCPCB) and iBOM — headless

Plugin choice matters: the layout `jlcpcb/{gerber,production_files,project.db}` with `BOM-*.csv`, `CPL-*.csv`, `GERBER-*.zip` comes from the
**JLCPCB Tools** plugin (bouni/kicad-jlcpcb-tools), *not* from Fabrication Toolkit (which writes `production/`).

```powershell
# 1. DRC (the plugin would run it first; headless export does not)
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --severity-error --format report --output drc.txt --units mm hardware\kicad\gw.kicad_pcb

# 2. Gerbers, drill, zip, CPL, BOM  (KiCad's own python!)  -> hardware\kicad\jlcpcb\
& "C:\Program Files\KiCad\10.0\bin\python.exe" scripts\kicad_fab_export.py hardware\kicad\gw.kicad_pcb

# 3. Interactive BOM (defaults reproduce the previous project's ibom.html)
& "C:\Program Files\KiCad\10.0\bin\python.exe" "<Documents>\KiCad\10.0\3rdparty\plugins\org_openscopeproject_InteractiveHtmlBom\generate_interactive_bom.py" `
       hardware\kicad\gw.kicad_pcb --no-browser --dest-dir bom --name-format ibom
```

Verified on 2026-11-25 against the previous project's board: `kicad_fab_export.py` produced a BOM and CPL **identical** to the ones made by the plugin's
GUI and a Gerber zip of the same size class. Gotchas (all encountered):

* The plugin's setting `lcsc_priority: false` makes the stale `project.db` win over the board's LCSC fields. The script forces the **board** to win
  (`--keep-db-lcsc` restores the plugin default).
* The plugin package must be imported without running its `__init__` (it registers a GUI action); the script does that.
* `<Documents>` is **OneDrive-redirected** on this PC; the script finds the real folder via the Windows known-folder API. Do the same when you type the path.
* Track in git: `jlcpcb/gerber/`, `jlcpcb/project.db`, `bom/ibom.html` (reviewable). `production_files/` (BOM/CPL/zip) is git-ignored and regenerated.
* Review the Gerbers in a viewer before ordering. Silk layers can change massively between exports (one silk layer showed ~6 700 changed body lines against the
  previous package; the cause — KiCad version vs. real board edits — was not investigated), so a text diff of Gerbers proves little.
* Custom DRC rule example from the previous board: `no_acid_traps` (min track angle 45°). Two pre-existing violations were knowingly left — write such decisions down.

## 4. Parts and sourcing lessons (verified)

* **LDO dropout is a system property.** An AP1117-3.3 fed from a XIAO's 5 V rail (≈ 4.3–4.4 V after the board's Schottky diode) was always in dropout; the output
  never regulated. Check headroom *at the real input voltage*, not the datasheet's typical.
* **Part numbers are not stock.** 5 % `RC0603JR-…` resistors of the needed values were not stocked at LCSC; the 1 % `RC0603FR-…` versions were (C114605 1.2 k,
  C114612 2.7 k, C114065 22 k, C137719 43 k at the time). A 10 µF/25 V X5R **0603** capacitor exists (C96446, Samsung CL10A106MA8NRNC) — the previous project
  believed it did not and reworked boards with a bigger part on flying leads. Check LCSC/JLCPCB's part pages (stock, basic/extended) before ordering; a web search is only a hint.
* **X5R/X7R capacitance falls with DC bias** — a 10 µF 0603 may act like 3–4 µF at its rated voltage; fine at low bias, relevant for filters and bulk decoupling.
* Resistor tolerance and MOSFET Vth spread dominated board-to-board variation of an analog feedback circuit; design analog parts with margin or plan per-board calibration.
* BOM rows group by *(value, footprint, LCSC)*: giving the same value two LCSC numbers splits the row (and the checker flags it).

## 5. Seeed XIAO modules in KiCad (verified from the library)

The previous project contains the Seeed library: `../wireless-esp8266-dap/circuit_ESP32C3_Xiao/Seeed Studio XIAO Series Library/`
(`Seeed_Studio_XIAO_Series.kicad_sym` + `XIAO-ESP32C6-SMD|DIP.kicad_mod`, `XIAO-ESP32S3-SMD|DIP.kicad_mod`, …). Copy it into this project (do not reference the sibling path).

| Pin | XIAO ESP32-C6 (symbol `XIAO-ESP32-C6-SMD`, 24 pins) | XIAO ESP32-S3 (symbol `XIAO-ESP32-S3-SMD`, 25 pins) |
|---|---|---|
| 1 | GPIO0 / A0 / D0 | GPIO1 / A0 / D0 |
| 2 | GPIO1 / A1 / D1 | GPIO2 / A1 / D1 |
| 3 | GPIO2 / A2 / D2 | GPIO3 / A2 / D2 |
| 4 | GPIO21 / D3 | GPIO4 / A3 / D3 |
| 5 | GPIO22 / D4 / SDA | GPIO5 / A4 / D4 / SDA |
| 6 | GPIO23 / D5 / SCL | GPIO6 / A5 / D5 / SCL |
| 7 | GPIO16 / D6 / **TX** (console UART0) | GPIO43 / D6 / **TX** (console UART0) |
| 8 | GPIO17 / D7 / **RX** | GPIO44 / D7 / **RX** |
| 9 | GPIO19 / D8 / SCK | GPIO7 / A8 / D8 / SCK |
| 10 | GPIO20 / D9 / MISO | GPIO8 / A9 / D9 / MISO |
| 11 | GPIO18 / D10 / MOSI | GPIO9 / A10 / D10 / MOSI |
| 12–16 | 3V3, GND, 5V, BAT, GND | 3V3, GND, 5V, BAT, GND |
| 17–22 | MTDI, MTDO, CHIP_EN, GND, MTMS, MTCK | MTDI, MTDO, CHIP_EN, GND, MTMS, MTCK |
| 23–25 | BOOT, 3V3 | USB_DN, USB_DP, PAD |

* The library has the **plain XIAO ESP32-S3**, not the **S3 Plus** the README wants (more GPIOs on a second row/B2B connector, 8 MB PSRAM / 16 MB flash — **unverified**,
  from the PDF/Seeed). You need the Plus footprint/symbol from Seeed (or make it) before layout. The RTS/CTS lines the README plans for the UART need those extra pins — a
  plain XIAO S3 has only D0–D10 on the header.
* The C6's RF-switch pins (GPIO3 power, GPIO14 select for the U.FL port, per the PDF — **unverified**, check the Seeed wiki) are **not** on the header: internal to the module.
* Both boards carry the **ESP32 USB-Serial/JTAG** on the USB-C port (VID `0x303A`).

## 6. Design requirements for this board (several unverified — verify, then delete the label)

* **Power:** both modules from one 5 V USB-C rail through their own regulators, local decoupling at each module (PDF suggests ≈ 100 µF + 100 nF); S3 Wi-Fi TX bursts
  ≈ 350 mA, C6 ≈ 100–150 mA (PDF, **unverified**). Check the connector, the 5 V path and any added protection for ≥ 1.5 A. Simulate or measure the sag.
* **UART between the chips:** TX, RX, **RTS, CTS**, GND; short, no crossing of antenna lines. Also route **C6 EN and BOOT to S3 GPIOs** so the host can reset
  and reflash the RCP (design-time decision; see `CODING_GUIDELINES.md` §4). Reserve the console UART/USB for service access.
* **Antennas:** two U.FL → SMA pigtails, antennas on opposite sides, collinear, **≈ 10 cm apart, less acceptable but not below ≈ 6 cm** (owner's decision 2026-11-26, small enclosure — measure isolation; see the requirements file, decision 4). Zigbee channel
  (e.g. 25) away from the Wi-Fi channel in use (PDF: Wi-Fi 1 or 6). Keep modules a few cm apart to avoid desensitisation of the C6 while the S3 transmits.
* **BME680:** I2C (address 0x76/0x77 depending on the SDO strap — check the module). Mount it **thermally isolated** from the modules and regulators (slot/air gap,
  or a separate small board on a cable) because self-heating biases temperature/humidity and the gas/IAQ result; the enclosure needs an air path (`ENCLOSURE_3D.md`).
  Pull-ups on SDA/SCL, 3.3 V supply. BSEC needs its own calibration time after power-on.
* **Debug/service:** test points for 3V3, 5 V, GND, UART, I2C; BOOT/RESET access for both modules; status LED(s) (the old board used one GPIO-driven LED).
* **Assembly:** decide which parts JLCPCB assembles (passives, connectors) and which are hand-fitted (XIAO modules, sockets). Keep LCSC numbers in the schematic from the start.

## 7. Release checklist for a PCB order

- [ ] ERC clean (or every warning explained), DRC reviewed (`drc.txt` kept with the release)
- [ ] `kicad_bom_check.py` clean; LCSC numbers checked on the LCSC/JLCPCB page for stock and basic/extended
- [ ] `kicad_fab_export.py` + iBOM regenerated from the committed files; production files reviewed in a Gerber viewer
- [ ] 3D model check (modules, connectors, mounting holes vs. the enclosure STEP) — `ENCLOSURE_3D.md`
- [ ] schematic PDF exported to `documentations/`; values in docs link to the schematic
- [ ] commit in portions (design / regenerated production files); tag only after the board was built and tested

## References

- KiCad documentation and file formats: <https://docs.kicad.org/>, <https://dev-docs.kicad.org/en/file-formats/>
- JLCPCB Tools plugin: <https://github.com/Bouni/kicad-jlcpcb-tools> — InteractiveHtmlBom: <https://github.com/openscopeproject/InteractiveHtmlBom>
- JLCPCB help centre (assembly, BOM/CPL format): <https://jlcpcb.com/help>
- LCSC parts search: <https://www.lcsc.com/>
- Seeed XIAO ESP32-S3 / S3 Plus / ESP32-C6 wiki: <https://wiki.seeedstudio.com/> (pinouts, antenna, RF switch)
- Bosch BME680 datasheet: <https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/>
- Previous board and notes: `../wireless-esp8266-dap/circuit_ESP32C3_Xiao/` (`documentations/`, `scripts/`, `jlcpcb/`)
