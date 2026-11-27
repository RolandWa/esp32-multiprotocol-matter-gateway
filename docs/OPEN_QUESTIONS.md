# Open questions and decisions (owner's call)

Ordered by how much they block. For each: what is known, what the options are, and a default the agent may assume **only if the owner agrees**
(say which default you used in your report). Strike items through / move them to a "Decided" section with date and reason when resolved.

## 1. ESP-IDF and esp-matter versions — blocks all firmware work

* Known: IDF v4.4.2 cannot build for the ESP32-C6. The IDF on this PC at `~/esp/esp-idf` is an untagged v6.1-dev checkout without the Xtensa toolchain. esp-matter pins its
  own IDF release. **Update 2026-11-26 (each branch's README, `DEPENDENCIES_AND_OTA.md` §2):** `release/v1.4.2` → IDF v5.4.1, `release/v1.5` → v5.5.5, `release/v1.6.1` and `main` (v1.7, ongoing) → **v6.0.2**; latest IDF release is v6.1.1. The older "registry page → v5.2.3" figure belonged to an older release.
* Options: (a) newest esp-matter release + the IDF it names; (b) esp-matter `main` + IDF v6.x; (c) an older pair that is known to support the C6 *and* the bridge example.
* Default if undecided: **(a)** — take the exact IDF tag from the README of the esp-matter release you check out, install it side by side (`ENVIRONMENT.md` §4), pin tags in `ENVIRONMENT.md`.
* **Progress 2026-11-27 (default (a) assumed — owner to confirm):** ESP-IDF **v6.0.2** installed side by side in `~/esp/esp-idf-v6.0.2` with its own `IDF_TOOLS_PATH=~/.espressif-gateway` (Python 3.14 env `idf6.0_py3.14_env`; targets esp32s3, esp32c6). The old toolchain baseline (`~/work/baseline_old_toolchain_20261127.txt`) was compared after the install: unchanged. **Owner confirmed option (a) the same day.** esp-matter `release/v1.6.1` (tip `4645784`, connectedhomeip `0998b87db7`) cloned shallow to `~/esp/esp-matter`; its README names IDF v6.0.2 and the build below succeeded with it. Acceptance test of the old project (spec §4A item 8) passed — see `tests/TEST_RESULTS.md`. **Build of `zigbee_bridge` for `esp32s3` succeeded** (IDF v6.0.2 + esp-matter v1.6.1, build only, nothing flashed). Caveats: (1) connectedhomeip's `bootstrap.sh` pigweed Python env could **not** be completed (Python 3.14 → PyGObject needs `pkg-config`/cairo dev packages; `sudo` unavailable; retry with Python 3.10 ignored `PW_BOOTSTRAP_PYTHON`) — it is not needed for firmware builds (`export.sh` only adds the cipd `gn`/`zap` to `PATH`), so `install.sh --no-bootstrap --no-host-tool` was used; **`chip-tool`/host tools are not built** and will need that env (or `apt install pkg-config libcairo2-dev` by the owner). (2) The app is **1 842 784 B in a 1 900 544 B slot (3 % free)**: the example's 4 MB partition table must be replaced by a 16 MB layout before adding BSEC and the BLE scanner (S3 Plus flash size still unverified).

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

## 3a. BLE sensors: Xiaomi LYWSD03MMC (chosen by the owner 2026-11-26)

Decided: Xiaomi Mijia `LYWSD03MMC` temperature/humidity sensors; the gateway scans them passively and exposes each as a Matter bridged Temperature Sensor + Humidity Sensor (details and sources: `project_specification_and_requirements.md` §3, BLE sensors).
**Decided by the owner (2026-11-26): the sensors' firmware will be replaced with custom `pvvx/ATC_MiThermometer` (BTHome v2)**; the stock firmware (encrypted MiBeacon, Mi Home bindkey) is not used. Flashing from the browser is the owner's action on each sensor — not done yet; the gateway code must parse BTHome v2 (optionally with a bindkey, if the owner enables encryption — to decide).
Open: (1) ~~stock vs. custom firmware~~ decided (see above); whether to enable BTHome **encryption** (bindkey) or send unencrypted; (2) the hardware revision of the sensors bought (**B1.5/B1.6 not recommended** by the pvvx README); (3) how many sensors and the advertising interval; (4) the S3's passive scan reliability with Wi-Fi active (measure); (5) battery reporting in Alexa (unverified); (6) code: **custom NimBLE scanner + BTHome v2 parser** (no esp-matter example; reference parsers: ESPHome `atc_mithermometer`/`xiaomi_ble`, `custom-components/ble_monitor` MIT).

## 4. Inter-chip link parameters

UART number and pins on both sides (must avoid console UART0, USB, strapping pins), baud (PDF suggests 460 800 or 921 600), RTS/CTS wiring, whether SPI is preferable (Espressif supports UART and SPI for RCP). Decide together with §3.

## 5. Licence

`LICENSE` is GPL-3.0; the draft README says "MIT". esp-matter/ESP-IDF are Apache-2.0. **Bosch BSEC is proprietary** (binary-only, own redistribution terms) and may not be redistributable together with GPL code.
Decide the licence, fix the README/LICENSE mismatch, and read BSEC's terms before publishing binaries. Do not edit `LICENSE` without the owner.

## 6. `project_specification_and_requirements.md`

The merged requirements document (hardware spec, wiring table, functional requirements, enclosure requirements, source repositories; Polish; written from the Gemini session and the former README) replaces the planned `SPECIFICATION.md`.
Its numbers are **unverified** AI material. After §1–§4 are decided, re-check it and make sure the wiring table is generated from/checked against the per-target pin header and the schematic, not typed twice.

## 7. Enclosure

CAD tool (FreeCAD / Fusion / other), antenna connector type and positions, wall-mount vs. desk, ventilation/BME680 chamber concept, colour/material (PETG white per the owner's guidelines), dimensions — after §3.

## 8. Security and provisioning

Matter test vs. production credentials (setup PIN, discriminator, DAC/PAI, factory partition), Wi-Fi credential provisioning (BLE/Matter commissioning vs. config file), secure boot/flash encryption — decide before the first non-lab unit.

## 9. BSEC integration

Which BSEC version and how it is obtained for the S3 (Xtensa); calibration-state persistence in NVS; how "ventilate" maps to a Matter device type/cluster (air-quality sensor cluster) so Alexa can use it in routines.

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
