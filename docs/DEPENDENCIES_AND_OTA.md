# Dependencies: are they all reachable, and can the device update itself over Wi-Fi?

Checked on **2026-11-26** from the owner's PC with the GitHub API (`gh api`), `curl`-style HEAD requests and the repositories' own README files.
"Verified" = read from the source named in the row; "unverified" = not checked or only seen in a search result. Nothing was built or flashed.

## 1. Reachability

HTTP 200 from this PC: `github.com`, `components.espressif.com` (ESP Component Registry), `dl.espressif.com` (toolchain downloads), `pypi.org`, `registry.npmjs.org`.
Nothing the build needs is behind a login. **The one exception is licensing, not access: Bosch BSEC** (see below).

## 2. Libraries (GitHub API, verified 2026-11-26)

| Library | Role | Licence | State |
|---|---|---|---|
| `espressif/esp-matter` | Matter SDK, host app | Apache-2.0 | active (pushed 2026-11-26). No GitHub "release" objects — it is **branch-based**: `release/v1.4.2` → IDF **v5.4.1**, `release/v1.5` → IDF **v5.5.5**, `release/v1.6.1` and `main` (v1.7, ongoing) → IDF **v6.0.2** (each branch's own README). This settles the "sources disagree" note in `OPEN_QUESTIONS.md` §1. Pulls `espressif/connectedhomeip` (Apache-2.0, several GB of submodules) |
| `espressif/esp-idf` | framework | Apache-2.0 | latest release **v6.1.1**; esp-matter asks for **v6.0.2** |
| `examples/bridge_apps/zigbee_bridge` (in esp-matter) | host app base | Apache-2.0 | **path differs from earlier notes** (`examples/zigbee_bridge` does not exist on main or `release/v1.6.1` — the example README still shows the old path). README: RCP on **ESP32-H2** + bridge on ESP32-S3 over UART; RCP built from IDF `examples/openthread/ot_rcp` with `OPENTHREAD_NCP_VENDOR_HOOK=y`. **The example never mentions the C6** |
| `espressif/esp-idf` `examples/openthread/ot_rcp` | RCP image | Apache-2.0 | its README lists **ESP32-C6** among supported targets (binary ≈ 299 KB). So the C6 RCP image is buildable; **C6 as the RCP of the zigbee_bridge example is still unproven** (`OPEN_QUESTIONS.md` §2) |
| `espressif/esp-zigbee-sdk` | Zigbee stack, `zigbee_gateway`, `ota_upgrade` examples | Apache-2.0 | active (2026-11-24) |
| `espressif/esp-serial-flasher` | flash an Espressif chip from another MCU (UART, reset + boot pins) | Apache-2.0 | **v2.1.0**, supports ESP32-C6 as target — fits our EN/BOOT wiring |
| `boschsensortec/Bosch-BSEC2-Library` | IAQ from the BME680 | **proprietary** (GitHub: NOASSERTION) | **v1.10.2610**; `src/esp32s3/libalgobsec.a` is present, so the S3 is supported. Licence: see §4 |
| `boschsensortec/BME68x_SensorAPI` | raw sensor driver | BSD-3-Clause | v4.4.8 (last push 2023-12) — enough for raw data, **no IAQ** |
| `arendst/Tasmota` | reference only | GPL-3.0 | do not copy code into a differently licensed project |
| `firsttris/esp32c6-zigbee-router` | reference (U.FL switch on the XIAO C6) | MIT | active |

Component Registry packages (`idf_component.yml`) resolve online during the build, so **the first build needs internet access**; pin versions and commit `dependencies.lock`.

## 3. Updating the device over Wi-Fi (OTA)

**Host (XIAO ESP32-S3 Plus)** — possible.
* The `zigbee_bridge` example already has an OTA layout (`partitions.csv`: `otadata`, `ota_0`, `ota_1`, 0x1D0000 = 1.8 MB each, plus `zb_storage`, `fctry`). The S3 Plus has 16 MB flash (unverified, Seeed), so the slots can be enlarged for BSEC + BLE scanner. ESP-IDF's OTA needs ≥ 2 app slots + `otadata`.
* **Matter OTA** (`CONFIG_ENABLE_OTA_REQUESTOR`): needs an OTA *provider*. esp-matter has `examples/ota_provider`; for testing the candidate image must be listed in the DCL TestNet (MainNet for products). **Whether Alexa/Echo acts as an OTA provider for a DIY device is not known — do not count on it** (unverified).
* **Own update path** (works regardless of the controller): IDF's `esp_https_ota` from an HTTPS URL you control (or a local page that accepts an upload), trigger from a Matter custom command / CLI / web page. Enable app rollback (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`) so a bad image reverts; sign images / secure boot is an open item (`OPEN_QUESTIONS.md` §8).

**Radio co-processor (XIAO ESP32-C6)** — possible, but **not by Matter OTA**.
* Matter OTA updates the host only. The RCP image must be flashed **by the host**: `esp-serial-flasher` over the existing UART (TX/RX) while the host drives the C6 `CHIP_EN` and `BOOT` — exactly the wiring decided on 2026-11-26 (S3 D0/D1 → R3/R4 → C6 EN/BOOT). Library defaults: reset hold 100 ms, boot hold 50 ms. The C6 enters download mode with GPIO9 (BOOT) low at reset.
* Flow: host downloads/stores the RCP image (≈ 300 KB, in a data partition), resets the C6 into download mode, flashes, resets it, restarts the RCP link. Update host and RCP **together** (the RCP and host protocol versions must match).
* Prerequisites: the first C6 image goes in by USB; the S3's strapping pin D2/GPIO3 (RTS) and the 1 kΩ series resistors must not disturb boot — test on the real boards (`hardware/kicad/README.md`).

**Power-loss safety:** the supercap on `BAT` (C3) gives ≈ 6 s (calculated, unverified) to finish a flash write or save state; an interrupted OTA is still protected by the two-slot layout.

## 3a. Role of Wi-Fi (owner's clarification, 2026-11-26)

Wi-Fi is the **uplink to Alexa** (Matter over Wi-Fi), not a sensor protocol. The gateway aggregates **BLE** and **Zigbee** sensors (plus the on-board BME680), packages them as Matter Bridge devices and sends them over Wi-Fi. Wi-Fi sensors/actuators as such are out of scope unless the owner decides otherwise. Only Bluetooth **Low Energy** is available (ESP32-S3/C6 have no Bluetooth Classic — unverified here, check the datasheets). No ready-made esp-matter example covers generic BLE advertisement sensors (`blemesh_bridge` is BLE **Mesh**): that scanner is custom code (NimBLE) — see `OPEN_QUESTIONS.md`.

## 4. Open points from this check

1. **BSEC licence.** GitHub says `NOASSERTION`; the repository's LICENSE.md points to Bosch's click-through terms, and an issue in the repo (#60) reports the licence URL as 404. Secondary sources say the binary is proprietary and not redistributable without Bosch's permission; build-time download is the common practice. Read Bosch's current terms before publishing firmware that contains `libalgobsec.a` (`OPEN_QUESTIONS.md` §5).
2. **Is BME680 covered by BSEC2?** BSEC2 targets the BME688; the repo carries the S3 library, but the supported-sensor list for the BME680 was **not checked**.
3. **Alexa as OTA provider** — unknown (see above).
4. **C6 as RCP with `zigbee_bridge`** — unproven (only `ot_rcp` lists the C6).
5. **Flash size of the Plus (16 MB)** and the C6 (4 MB) — from the PDF/Seeed, unverified.

## References

- esp-matter (branches, IDF versions per README, examples): <https://github.com/espressif/esp-matter> — `examples/bridge_apps/zigbee_bridge`, `examples/ota_provider`
- ESP-IDF OTA and partition tables: <https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html>, <https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/partition-tables.html>
- `ot_rcp` example: <https://github.com/espressif/esp-idf/tree/master/examples/openthread/ot_rcp>
- esp-serial-flasher: <https://github.com/espressif/esp-serial-flasher> — registry: <https://components.espressif.com/components/espressif/esp-serial-flasher>
- ESP32-C6 download mode: <https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/download-guidelines.html>
- Bosch BSEC2 library and licence thread: <https://github.com/boschsensortec/Bosch-BSEC2-Library>, <https://github.com/boschsensortec/Bosch-BSEC2-Library/issues/60>
- Matter OTA on ESP32 (connectedhomeip guide): <https://github.com/project-chip/connectedhomeip/blob/master/docs/guides/esp32/ota.md>
