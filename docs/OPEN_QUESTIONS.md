# Open questions and decisions (owner's call)

Ordered by how much they block. For each: what is known, what the options are, and a default the agent may assume **only if the owner agrees**
(say which default you used in your report). Strike items through / move them to a "Decided" section with date and reason when resolved.

## 1. ESP-IDF and esp-matter versions — blocks all firmware work

* Known: IDF v4.4.2 cannot build for the ESP32-C6. The IDF on this PC at `~/esp/esp-idf` is an untagged v6.1-dev checkout without the Xtensa toolchain. esp-matter pins its
  own IDF release. **Update 2026-11-26 (each branch's README, `DEPENDENCIES_AND_OTA.md` §2):** `release/v1.4.2` → IDF v5.4.1, `release/v1.5` → v5.5.5, `release/v1.6.1` and `main` (v1.7, ongoing) → **v6.0.2**; latest IDF release is v6.1.1. The older "registry page → v5.2.3" figure belonged to an older release.
* Options: (a) newest esp-matter release + the IDF it names; (b) esp-matter `main` + IDF v6.x; (c) an older pair that is known to support the C6 *and* the bridge example.
* Default if undecided: **(a)** — take the exact IDF tag from the README of the esp-matter release you check out, install it side by side (`ENVIRONMENT.md` §4), pin tags in `ENVIRONMENT.md`.
* **Progress 2026-11-27 (default (a) assumed — owner to confirm):** ESP-IDF **v6.0.2** installed side by side in `~/esp/esp-idf-v6.0.2` with its own `IDF_TOOLS_PATH=~/.espressif-gateway` (Python 3.14 env `idf6.0_py3.14_env`; targets esp32s3, esp32c6). The old toolchain baseline (`~/work/baseline_old_toolchain_20261127.txt`) was compared after the install: unchanged. **Owner confirmed option (a) the same day.** esp-matter `release/v1.6.1` (tip `4645784`, connectedhomeip `0998b87db7`) cloned shallow to `~/esp/esp-matter`; its README names IDF v6.0.2 and the build below succeeded with it. Acceptance test of the old project (spec §4A item 8) passed — see `tests/TEST_RESULTS.md`. **Build of `zigbee_bridge` for `esp32s3` succeeded** (IDF v6.0.2 + esp-matter v1.6.1, build only, nothing flashed). Caveats: (1) connectedhomeip's `bootstrap.sh` pigweed Python env could **not** be completed (Python 3.14 → PyGObject needs `pkg-config`/cairo dev packages; `sudo` unavailable; retry with Python 3.10 ignored `PW_BOOTSTRAP_PYTHON`) — it is not needed for firmware builds (`export.sh` only adds the cipd `gn`/`zap` to `PATH`), so `install.sh --no-bootstrap --no-host-tool` was used; **`chip-tool`/host tools are not built** and will need that env (or `apt install pkg-config libcairo2-dev` by the owner). (2) The app is **1 842 784 B in a 1 900 544 B slot (3 % free)**: the example's 4 MB partition table must be replaced by a larger layout before adding BSEC and the BLE scanner — 8 MB is the starting point, 16 MB (S3 Plus) only if needed (rule and numbers: "Host module: 8 MB or 16 MB flash" in section 3; flash sizes are listing data, not measured).

## 2. Which radio co-processor and which Zigbee stack

* Known: PDF claims "XIAO ESP32-C6 as RCP + S3 host" works via esp-matter's `zigbee_bridge`; an old GitHub issue says that example did not support the C6; official material shows an
  ESP32-H2 RCP. The XIAO H2 has no U.FL connector; the C6 has one (RF switch).
* **Update 2026-11-26 (read on GitHub, `DEPENDENCIES_AND_OTA.md` §2):** the example is at `examples/bridge_apps/zigbee_bridge` (not `examples/zigbee_bridge`); its README describes an **ESP32-H2** RCP and never mentions the C6. IDF's `ot_rcp` README **does list ESP32-C6** as a supported target (≈ 299 KB image), so a C6 RCP image can be built — the combination with the bridge example is still untested.
* To do first (cheap): read `sdkconfig.defaults` of that example on the chosen branch and build `ot_rcp` for `esp32c6` with `OPENTHREAD_NCP_VENDOR_HOOK=y`.
* **Progress 2026-11-27:**
  * **Read (GitHub, `main`):** the `zigbee_bridge` example now uses the ZBOSS host stack (`CONFIG_ZB_HOST=y`, `CONFIG_ZB_RADIO_MACSPLIT_UART=y`) and talks Spinel over UART to an `ot_rcp` image (S3 pins default TX=GPIO4, RX=GPIO5, `Kconfig.projbuild`). Its own README still says only ESP32-H2. **Espressif's `esp-zigbee-sdk` `zigbee_gateway` README, however, names "ESP32-H2 or ESP32-C6" running `ot_rcp` as the 802.15.4 SoC** — that is the documented support for the C6 RCP with the same host stack. `ot_rcp` README lists C5/C6/H2.
  * **Built (WSL, IDF v6.0.2):** `ot_rcp` for `esp32c6` with `CONFIG_OPENTHREAD_NCP_VENDOR_HOOK=y`, UART interface (`OPENTHREAD_RCP_UART=y`, 460 800 baud default) → `esp_ot_rcp.bin` 246 112 bytes. Build only.
  * **Correction/finding (same day):** the `main` defaults quoted above do not match the chosen release. `release/v1.6.1` pins `esp-zigbee-lib ~1.6.0` (resolved **1.6.9**) whose Kconfig has only `ZB_RADIO_NATIVE` / `ZB_RADIO_SPINEL_UART`; the example's `CONFIG_ZB_HOST=y` and `CONFIG_ZB_RADIO_MACSPLIT_UART=y` (written for a newer library) are **silently ignored** and the build falls back to `ZB_RADIO_SPINEL_UART=y` — the correct host-side mode for an `ot_rcp`, but it means the example's own defaults are not what is built. S3 host build with that: OK (`zigbee_bridge.bin` 1 842 784 B).
  * **Still unproven:** runtime behaviour of the S3 host against the C6 RCP, and above all the C6 RCP talking to the S3 on real boards (UART pins on the C6 side, EN/BOOT wiring, RF switch). Keep "no PCB order before it works on dev boards" — now moot (no PCB), but the hardware check is still pending.
* Options: C6 RCP (as planned) · H2 RCP (bare module/other board) · another Zigbee path (e.g. Tasmota's Zigbee2Tasmota — mentioned in the PDF, needs its own build).
* Default: keep the C6 plan, **but do not order a PCB before the C6 RCP is proven on dev boards**.

## 3. What the KiCad design contains

**Decided by the owner on 2026-11-26** (details: `project_specification_and_requirements.md`, "Decyzje konstrukcyjne"; schematic: `hardware/kicad/`):

* **No PCB.** The two XIAO modules and the BME680 board are soldered together with wires or pin headers (modules possibly one above the other) in one 3D-printed enclosure. Bare-chip designs are off the table.
* Power: USB-C of the host (S3) only; the host's 5V pad feeds the C6's 5V pad.
* The host resets/flashes the C6 (C6 EN/BOOT driven from S3 GPIOs) — in the schematic.
* Larger external antennas on both modules (EU EIRP limit to check); parts only from TME, Mouser, Farnell.

Added later the same day: **supercap C3 (≥ 5 V, low ESR) on U1 `BAT`** for hold-up; **IKEA SJÖSS 20 W** (USB-C, PD) as the mains adapter — an exception to the TME/Mouser/Farnell rule chosen by the owner; antenna placement: small enclosure, ≈ 10 cm apart (less acceptable, not below ≈ 6 cm), collinear on opposite walls — requirements, decision 4; USB-C ↔ USB-C cable from IKEA: SITTBRUNN 1.0 m, white 906.185.40 or light green 305.959.85 (decided; the USB-A → USB-C variant was dropped because the SJÖSS charger has only a USB-C socket). The owner assumes the XIAO has CC resistors — unconfirmed, measure 5 V first.
Open from that: does the XIAO ESP32-S3 have 5.1 kΩ on CC (else the PD adapter gives no 5 V)? how does the XIAO feed its load and protect `BAT` (supercap inrush, charge current shared with the load)? which supercap model (ESR, voltage)?

Still open: wires vs. pin headers vs. a small perfboard for the stack; how the XIAO routes VBUS to its 5V pad (diode in the U1→U2 wire?); the S3 **Plus** symbol (not in the Seeed library);
BME680 module choice (the CJMCU-680 is not sold by the three shops); antennas: the owner picked the adhesive FPC `2JF0802P-010MC137-UFL` (TME; gain at 2.4 GHz not stated — ≈ 1.7 dBi unconfirmed; no SMA pigtails needed) — range vs. the bundled antenna and the 10 cm separation must be measured; part numbers (`hardware/kicad/README.md`, "Parts"). Whether to build a PCB later is a new decision.

### Host module: 8 MB or 16 MB flash (owner's rule, 2026-11-27)

The listings give **8 MB for the plain XIAO ESP32-S3 and 16 MB for the S3 Plus** (from the shop/Seeed listings, not measured on a board). Rule: start with the **plain 8 MB module**
(it is in TME/Mouser, and the wiring needs only D0–D7, which both have); take the **Plus** only if the firmware no longer fits in 8 MB.
Numbers behind it (2026-11-27; the layout is a **proposal that is not in the repo**, the vendor 4 MB table is still used): host app today 1 844 192 B (vendor example + `firmware/common`);
Bosch's `libalgobsec.a` for the S3 is 250 968 B as an archive (upper-bound hint only, the linked size was not measured); the BLE observer role is small next to that.
A layout with **2 × 3 MB OTA slots**, otadata, NVS, `zb_storage`, `fctry` and a 0x60000 data partition for the RCP image ends at 0x6B7000 = 6.71 MB, i.e. it passes the partition checker for 8 MB with 1.29 MB spare
and leaves 1.24 MB of growth in a slot. The measurable trigger for "buy the Plus": the host app (BSEC + scanner included) approaches **≈ 3 MB**, or secure boot / flash encryption (section 8) pushes it there.
Switching later means `CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y` (or 16) plus a new `partitions.csv`; the logic and the wiring do not change.

## 3a. BLE sensors: Xiaomi LYWSD03MMC (chosen by the owner 2026-11-26)

Decided: Xiaomi Mijia `LYWSD03MMC` temperature/humidity sensors; the gateway scans them passively and exposes each as a Matter bridged Temperature Sensor + Humidity Sensor (details and sources: `project_specification_and_requirements.md` §3, BLE sensors).
**Decided by the owner (2026-11-26): the sensors' firmware will be replaced with custom `pvvx/ATC_MiThermometer` (BTHome v2)**; the stock firmware (encrypted MiBeacon, Mi Home bindkey) is not used. Flashing from the browser is the owner's action on each sensor — not done yet; the gateway code must parse BTHome v2. **Decided by the owner (2026-11-27): no encryption for now** — the sensors send unencrypted BTHome, `gw_bthome` rejects encrypted packets (`GW_BTHOME_ERR_ENCRYPTED`); a bindkey (AES-CCM) can be added later without changing the rest.
Open: (1) ~~stock vs. custom firmware~~ decided; ~~encryption~~ decided (not now); (2) the hardware revision of the sensors bought (**B1.5/B1.6 not recommended** by the pvvx README); (3) how many sensors and the advertising interval; (4) the S3's passive scan reliability with Wi-Fi active (measure); (5) battery reporting in Alexa (unverified); (6) code: **custom NimBLE scanner + BTHome v2 parser** (no esp-matter example; reference parsers: ESPHome `atc_mithermometer`/`xiaomi_ble`, `custom-components/ble_monitor` MIT).

## 4. Inter-chip link parameters

**Decided by the owner (2026-11-27): pins as in the KiCad schematic.** Implemented in `firmware/common/gw_pins.h` (follows the schematic; `tests/unit/test_pin_map.py` compares it with the netlist exported by `kicad-cli`), `firmware/host-esp32s3/sdkconfig.defaults.gateway` and `firmware/rcp-esp32c6/sdkconfig.defaults.esp32c6`. Build only, never run on a board.

| Link | S3 host (U1) | C6 RCP (U2) |
|---|---|---|
| TX / RX | GPIO43 / GPIO44 on **UART1** (vendor `app_zboss.h`) | GPIO16 / GPIO17 on UART0 = the chip's default UART0 pins |
| RTS / CTS (wired, reserved) | GPIO3 / GPIO4 | GPIO2 / GPIO21 |
| Reset / boot drive | GPIO1 → R3 → C6 CHIP_EN, GPIO2 → R4 → C6 BOOT (GPIO9) | — |
| Speed | 460 800 baud, 8N1 — the vendor default on both sides (kept) | same |

Consequences found while implementing (verified in the sources, ESP-IDF v6.0.2 / esp-zigbee-lib 1.6.9):
* **GPIO43/44 are the S3's default console pads (UART0).** The vendor config used UART0 as the console, so the host now sets `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` (the vendor `zb_gw_board` variant does the same) and the link runs on UART1. The ROM boot messages still use UART0/GPIO43 for a moment at every S3 reset; the C6 sees that as noise before its Spinel traffic (unverified on hardware).
* **The RTS/CTS wires cannot be used with the standard stack:** `esp_openthread_uart_config_t` (RCP) and `esp_zb_uart_config_t` (host) carry only `rx_pin`/`tx_pin`, and both vendor configs hard-code `UART_HW_FLOWCTRL_DISABLE`. Flow control stays off; the wires are harmless but unused. This differs from `CODING_GUIDELINES.md` section 4 ("use RTS/CTS"). Options if byte loss shows up in a hardware test: lower the Spinel traffic, or write a custom UART layer (not planned).
* S3 GPIO3 (RTS) is a strapping pin; nothing drives it, so it does not disturb boot. C6 GPIO9 (BOOT) is a strapping pin on purpose and is driven by the S3 only while flashing the RCP.
* The C6's RF switch pins (GPIO3, GPIO14) are not used in the map.
SPI instead of UART was not pursued.

## 5. Licence

`LICENSE` is GPL-3.0; the draft README says "MIT". esp-matter/ESP-IDF are Apache-2.0. **Bosch BSEC is proprietary** (binary-only, own redistribution terms) and may not be redistributable together with GPL code.
Decide the licence, fix the README/LICENSE mismatch, and read BSEC's terms before publishing binaries. Do not edit `LICENSE` without the owner.
**Owner (2026-11-27): not now — set aside.** Still open; nothing is published, so nothing depends on it yet.

## 6. `project_specification_and_requirements.md`

The merged requirements document (hardware spec, wiring table, functional requirements, enclosure requirements, source repositories; Polish; written from the Gemini session and the former README) replaces the planned `SPECIFICATION.md`.
Its numbers are **unverified** AI material. After §1–§4 are decided, re-check it and make sure the wiring table is generated from/checked against the per-target pin header and the schematic, not typed twice.

## 7. Enclosure

CAD tool (FreeCAD / Fusion / other), antenna connector type and positions, wall-mount vs. desk, ventilation/BME680 chamber concept, colour/material (PETG white per the owner's guidelines), dimensions — after §3.

**Progress 2026-11-27:** the owner's requirements R1-R10 are in `docs/ENCLOSURE_3D.md` section 3a. A **rev02 DRAFT** exists in `hardware/enclosure-3d/` (OpenSCAD, delegated to a subagent): **74.6 × 69.5 × 30.5 mm**, two modules side by side with a divider, BME680 at the bottom upstream of a chimney airflow, six hidden snap hooks released from the back (no screws), boards held by clips, rounded vertical corners, keyholes + tape recess + wall-screw holes, a USB dust plug, antennas glued inside for both modules (antenna centre distance 70.9 mm). rev01 was removed. Everything is **computed only - not printed, not fitted to real boards, no strength, thermal or RF measurement**; the board details are `ASSUMED - verify` parameters (`py -3.12 hardware/enclosure-3d/scadparams.py --assumed`), the C6 is assumed equal to the S3.
**rev03 (2026-11-27, supersedes the rev02 description above; ACCEPTED by the owner as the concept, "akceptuję rev03"):** **78.8 × 69.5 × 30.5 mm**, layout A (host S3 bottom right with its single USB-C opening in the BOTTOM wall, C6 top left without USB opening, BME680 bottom left under a double-wall baffle, chimney airflow, antenna distance 75.1 mm, 10.5 mm keep-out), no BOOT/RESET holes, nothing on the top face, engraved name `esp32-matter-gateway` in three lines on the lid (Bahnschrift Bold: Liberation Sans Bold made the "e" read as "o"; Bahnschrift is a Windows system font, not bundled), two keyholes **on one horizontal line 36 mm apart** with a recessed dimension line and the number "36 mm" on the back (R17), tape cells shortened to z 6-30. 66 assembly checks and 134 unit tests pass. **Still only computed: nothing printed, no board measured, no thermal, airflow or RF test; layouts B and C exist as paper estimates only; R2 (sensor upstream of all heat) is met only for the C6, not for the S3 column.** Open after acceptance: the unmeasured items below (keep-out/RF, thermal test of the baffle with foam-sealed divider slots, real board dimensions, USB-C height, antenna choice, 20-cycle snap test, fit samples). The owner did not individually answer the agent's list (cable anchor by tie slots instead of a clamp, who runs the 90 min thermal test and the pass criterion, tape at the lid top corners): treat those as open.
**Added later (2026-11-27): R12 service model, R13 one side USB-C opening for the host only (conflicts with the antenna walls - three options), R14 bench use with the lid off, R15 engraved device name (the text is still to be given by the owner) - `docs/ENCLOSURE_3D.md` section 3a. rev02 meets none of R13-R15; the next revision (rev03) waits for the name, the position and the choice of the USB option.**
Owner's decisions still needed (the subagent's list): accept the size and the 10.5 mm antenna keep-out (a 65 mm case would need 3-6 mm, with the RF risk unmeasured); ~~accept that the case must come off the wall to open~~ (accepted 2026-11-27 with the service model R12 in `docs/ENCLOSURE_3D.md`: about 12 closings in the product's life - 10 at the start, 2 later; Wi-Fi updates, so the case is not opened in normal use; a failure means taking it down and opening it from the back - **but the Wi-Fi update path is not implemented yet**); confirm the mounting orientation (vertical, sensor down, USB-C up); print the six fit samples and run the cycle test; measure the real boards (C6 buttons/U.FL/corners, BME680 corners and holes, USB-C height); final BME680 module and wires vs. pin headers; BOM antenna or the one from the S3 box; the lid has no hook at its top corners - accept or add tape; hood or plug parking pocket (both dropped).

## 8. Security and provisioning

Matter test vs. production credentials (setup PIN, discriminator, DAC/PAI, factory partition), Wi-Fi credential provisioning (BLE/Matter commissioning vs. config file), secure boot/flash encryption — decide before the first non-lab unit.

## 9. BSEC integration

**BME680 is supported (checked 2026-11-27 in `boschsensortec/Bosch-BSEC2-Library`, v1.10.2610 = BSEC 2.6.1.0):** the library ships eight BME680 configuration sets, `src/config/bme680/bme680_iaq_{18v,33v}_{3s,300s}_{4d,28d}` (supply voltage, sample interval, calibration history), alongside the BME688 sets; `library.properties` lists `esp32s3` (not `esp32c6`), and `src/esp32s3/libalgobsec.a` exists. The README text says the library was "conceptualized for the BME688" and the click-through licence file name covers "bsec_bme680_bme688_bme690" — so BME680 is covered, just not the headline sensor.
For this gateway the matching set is **`bme680_iaq_33v_3s_4d` or `_28d`** (3.3 V from the S3's 3V3 pad or the Adafruit board's regulator; `BSEC_SAMPLE_RATE_LP`, 3 s). `bsec_datatypes.h` says the heat-compensated temperature in LP mode is only supported for 1.8 V by default; at 3.3 V the config file **must** be loaded (`bsec_set_configuration`). `BSEC_INPUT_HEATSOURCE` (module self-heating offset) needs a measurement in the finished enclosure.
Not checked: an ESP-IDF (non-Arduino) integration of the library; the licence terms (set aside, section 5).
Still open: which version/source of the library the build uses; calibration-state persistence in NVS; how "ventilate" maps to a Matter device type/cluster (air-quality sensor cluster) so Alexa can use it in routines; 4-day vs 28-day calibration history.

## 10. Process

* Where do hardware test results go (`tests/TEST_RESULTS.md`, dated) and who runs the long soak test?
* CI: GitHub Actions for `pytest tests/unit` + both IDF builds? (`TESTING.md` §4.)
* Git LFS or release assets for STL/STEP and fabrication packages?

## References

- esp-matter: <https://github.com/espressif/esp-matter> (examples, `zigbee_bridge`, release/IDF table)
- esp-zigbee-sdk: <https://github.com/espressif/esp-zigbee-sdk>
- Seeed XIAO ESP32-C6 / S3 Plus: <https://wiki.seeedstudio.com/>
- Bosch BSEC licence/download: <https://www.bosch-sensortec.com/software-tools/software/bme680-software-bsec/>
- Input material: `project_specification_and_requirements.md`, `Bramka Smarthome na ESP32-C6.pdf`
