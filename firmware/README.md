# firmware/

State on 2026-11-27: both images exist and **build** (IDF v6.0.2, esp-matter `release/v1.6.1`); nothing was flashed or run on a board.

| Directory | Content | State |
|---|---|---|
| `host-esp32s3/` | ESP-IDF project for the host (XIAO ESP32-S3 Plus). Baseline: esp-matter `zigbee_bridge` + 3 small gateway changes (`README.md` there) | builds; Matter bridge, BLE scanner, BME680/BSEC **not implemented yet** |
| `rcp-esp32c6/` | ESP-IDF project for the 802.15.4 radio co-processor (XIAO ESP32-C6): Espressif's `ot_rcp` + `OPENTHREAD_NCP_VENDOR_HOOK=y` | builds; UART pins/baud are the example's defaults (open decision) |
| `common/` | **pure C99, no ESP-IDF includes**, host-unit-tested, also an IDF component named `common` | 6 modules, see below |

`common/` modules (all with `gw_` prefix, a header and `tests/unit/test_<module>.c`):

| Module | Purpose |
|---|---|
| `gw_bthome` | BTHome v2 service-data parser (pvvx sensors); encrypted packets rejected until the bindkey decision |
| `gw_units` | sensor units → Matter attribute units with range checks; IAQ → AirQuality class (proposal) |
| `gw_ventilation` | "ventilate" flag: on at IAQ > 150, off at IAQ < 110, holds while BSEC accuracy is 0 |
| `gw_report` | report a value on change ≥ delta or every N ms (injected, wrap-safe time) |
| `gw_sensor_table` | allow-list of BLE sensors by MAC, packet-id de-duplication, partial-packet merge, staleness |
| `gw_rcp_supervisor` | reset / boot-timeout / dead-RCP / backoff state machine for the C6 (no GPIO access; caller executes the action) |

Rules (details: `../docs/CODING_GUIDELINES.md`):

* every new decision/protocol/state machine goes to `common/` with a test in `../tests/unit/` — hardware access stays in thin wrappers;
* files copied from Espressif's examples stay **byte-identical**; the gateway's own changes are an explicit list in each project's `README.md` and `VENDOR_BASELINE.sha256` (`../tests/unit/test_firmware_layout.py` enforces it);
* no GPIO number outside the per-target pin header (not written yet: the pin map is an open decision); commit `sdkconfig.defaults*` and `dependencies.lock`, never `sdkconfig`;
* build with `..\scripts\build.bat` (WSL) — command lines in each project's README; flash with `..\scripts\flash.bat`; both images must build before a change is "done".

## References

- ESP-IDF project structure and components: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/build-system.html>
- esp-matter examples (bridge/zigbee_bridge): <https://github.com/espressif/esp-matter/tree/release/v1.6.1/examples/bridge_apps/zigbee_bridge>
- BTHome v2 format: <https://bthome.io/format/>
