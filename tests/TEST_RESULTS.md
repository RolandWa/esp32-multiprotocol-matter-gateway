# Test results (dated)

"Built" is not "works on hardware". Hardware checks that are still pending are listed at the bottom.

## 2026-11-27 — environment acceptance test (spec §4A item 8)

Change under test: ESP-IDF v6.0.2 (`~/esp/esp-idf-v6.0.2`, `IDF_TOOLS_PATH=~/.espressif-gateway`) and esp-matter `release/v1.6.1` (`~/esp/esp-matter`) installed in WSL next to the old toolchain.

| Check | Result |
|---|---|
| Baseline of the old toolchain taken before the install (`~/work/baseline_old_toolchain_20261127.txt`) | done |
| `~/.espressif/tools/*/*` after install vs baseline | identical |
| `pip freeze` of `idf4.4_py3.10_env` after install vs baseline | identical |
| `git describe` of `~/esp/esp-idf-v4.4.2` | `v4.4.2` |
| `~/.bashrc` / `~/.profile` contain no IDF / esp-matter variables | confirmed (grep count 0) |
| Old project `wireless-esp8266-dap`: `build.bat --build` (esp32c3, IDF 4.4.2) | **success**; `wireless_esp_dap_full.bin` 786 384 B, same size as before. 109 bytes differ from the previous binary; the four groups inspected are build date/time strings, the rest (probably checksums/digests) was not inspected. Previous binary backed up: `~/work/backup/wireless_esp_dap_full_20251125.bin`, SHA256 `F6C72E14949D49ADDF1101B2E196D8DC9CEB4B9AC7641B9E1538C7A2BBEBE61C` |
| Old repo `git status` / HEAD after the build | unchanged (`m ESP8266_RTOS_SDK`, `?? run_test.bat` were already there; HEAD `fb4e241`) |

## 2026-11-27 — firmware builds (build only, nothing flashed)

| Image | Result |
|---|---|
| `ot_rcp` for `esp32c6`, IDF v6.0.2, `OPENTHREAD_NCP_VENDOR_HOOK=y`, UART | built, `esp_ot_rcp.bin` 246 112 B |
| esp-matter `examples/bridge_apps/zigbee_bridge` for `esp32s3`, IDF v6.0.2, esp-zigbee-lib 1.6.9 | built, `zigbee_bridge.bin` 1 842 784 B in a 1 900 544 B slot (3 % free); 1 project warning (`esp_zb_main_loop_iteration` deprecated). Example's `ZB_HOST` / `ZB_RADIO_MACSPLIT_UART` defaults are ignored by this library version (`OPEN_QUESTIONS.md` §2) |

Both builds above were throw-away copies of Espressif's examples in `~/work/src` / `~/work/build`.

## 2026-11-27 — project firmware (`firmware/`), unit and regression tests

Builds from a clean build directory with `scripts/build.bat` (IDF v6.0.2, `--tools-path ~/.espressif-gateway`). **Build only, nothing flashed.**

| Image | Result |
|---|---|
| `firmware/rcp-esp32c6` (vendor `ot_rcp` + `OPENTHREAD_NCP_VENDOR_HOOK=y`) | built; `esp_ot_rcp.bin` 246 112 B, merged image 311 648 B; no warnings from project files |
| `firmware/host-esp32s3` (vendor `zigbee_bridge` + `firmware/common` + boot banner) | built; `gateway_host.bin` 1 844 192 B in a 1 900 544 B slot = **3.0 % free** (+1 408 B vs. the vendor example's 1 842 784 B); 2 warnings, both in Espressif code (`esp_zb_main_loop_iteration` deprecated, `Optional.h`), none from `gw_*` files |

Tests (`py -3.12 -m pytest tests/unit -q`): **55 passed** (C unit tests with ASan/UBSan, BTHome C↔Python contract test, firmware layout / vendor-baseline / partition tests, KiCad and script tests from before). C checks: bthome 20 124, rcp supervisor 426, report 42, sensor table 93, units 69, ventilation 1 049.

Mutation checks (broken code in a temporary copy; each mutant must make a test fail):

| Suite | Mutants | Killed | Notes |
|---|---|---|---|
| C unit tests (`firmware/common`, 6 modules) | 53 | 52 | the survivor is an **equivalent mutant**: removing the early `return` for state FAILED in `gw_rcp_sup_step` changes nothing, because the `switch` case for FAILED also returns NONE |
| Python tests (contract + layout) | 20 | 20 | control run on an unmodified copy passes (so "killed" is not an artefact of copying) |

Found while testing: a first mutation run hung because several test loops had no step limit; the loops were bounded and the run repeated.
A generator guard test failed on its first run (only ~34 % of generated BTHome packets contained decoded objects) and the generator was fixed.

Not verified: behaviour of any of this on a board; the Matter pressure unit (0.1 kPa per count) against the Matter specification (the cluster XML does not state it);
the AirQuality class boundaries and the RCP supervisor timings are proposals, not measurements.

## Hardware checks pending

- First flash of both XIAO boards and port identification (`detect_port.py` has never seen a real XIAO).
- C6 RCP ↔ S3 host over UART (pins, baud, EN/BOOT wiring, RF switch): does the host read the RCP version and form a Zigbee network?
- Matter commissioning with Alexa; BLE scan while Wi-Fi is active.

## References

- `project_specification_and_requirements.md` §4A (acceptance test), `docs/OPEN_QUESTIONS.md` §1–§2, `docs/ENVIRONMENT.md` §2.
