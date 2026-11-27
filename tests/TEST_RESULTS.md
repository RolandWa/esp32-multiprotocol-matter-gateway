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

## 2026-11-27 (later) — pins as in the KiCad schematic

Owner's decision: link pins follow the schematic; BTHome stays unencrypted; licence set aside. Implemented in `firmware/common/gw_pins.h`,
`firmware/host-esp32s3/sdkconfig.defaults.gateway`, `firmware/rcp-esp32c6/sdkconfig.defaults.esp32c6`. **Build only, nothing flashed.**

| Check | Result |
|---|---|
| Both images rebuilt from clean directories | built. RCP `esp_ot_rcp.bin` 246 112 B (unchanged); host `gateway_host.bin` 1 846 384 B (+2 192 B for the link banner and pin checks), 54 160 B = 2.8 % of the slot free |
| Resulting host `sdkconfig` | `PIN_TO_RCP_TX=44`, `PIN_TO_RCP_RX=43`, console `USB_SERIAL_JTAG` (UART console off), `ZB_RADIO_SPINEL_UART=y` — read from the generated file, not only from the defaults |
| Resulting RCP `sdkconfig` | `OPENTHREAD_UART_PIN_MANUAL=y`, RX 17, TX 16, `NCP_VENDOR_HOOK=y` |
| Compile-time guard in `gw_boot.c` | sdkconfig pins equal `gw_pins.h` (`_Static_assert`; the build passed) |
| `py -3.12 -m pytest tests/unit` | **75 passed** (includes the schematic netlist comparison with the KiCad 9.0.9 CLI) |
| C checks | pins 80, bthome 20 124, rcp supervisor 433, report 42, sensor table 93, units 69, ventilation 1 049; all 0 failures |
| Mutation check of the new tests (broken header, sdkconfig, CMake, schematic, vendor baud, a duplicated pin number) | 17 of 17 killed; control run on unmodified copies passes. First run: 15 of 16 — the survivor exposed a real gap (a second `SDKCONFIG_DEFAULTS` line went unnoticed), fixed by asserting exactly one |

Not verified: anything on a board. Found while implementing (details in `docs/OPEN_QUESTIONS.md` section 4): the schematic's RTS/CTS wires cannot be used by the standard
stack (no RTS/CTS pins in the vendor UART configs), the S3's GPIO43/44 are its default console pads (console moved to USB Serial/JTAG), ROM boot messages on the link at reset are expected.

## 2026-11-27 (evening) — enclosure rev02 and the snap-strain test (R11)

The enclosure was redesigned by a subagent against the owner's requirements R1-R11 (`docs/ENCLOSURE_3D.md` section 3a); I re-ran its checks and the whole suite. **Nothing printed, nothing measured.**

| Check | Result |
|---|---|
| `py -3.12 -m pytest tests/unit` after rev02 and after removing the rev01 files | 102 passed (one test fewer than the 103 before: the one that demanded a rev01 archive); with the 25 new snap-strain tests added: **127 passed** (final run) |
| Final STLs in step with `params.scad` | yes (STLs 16:57, parameters 16:56); my own render of the STLs measures 74.6 x 69.5 x 30.5 mm, the same as the agent's report |
| `tests/unit/test_snap_strain.py` (new, R11): 25 tests | **passed**: lid hook 1.8 x 19.0 mm, deflection 0.75 mm → strain 0.56 %, stress 14.3 MPa = 41 % of the Z strength, margin to break 9.3; board clip 1.6 x 16.8 mm, deflection 0.80 mm → 0.68 %, 17.3 MPa = 50 %, margin 7.6; Z-direction Bambu PETG Basic data (E 2550 MPa, 35 MPa, 5.2 %) |
| Formula check | closed form vs. an independent numerical beam model (double differentiation of the deflection curve): agree within 3 % on four geometries |
| Hook geometry vs. the saved lid STL | lowest hook point of the STL equals the value derived from the parameters (±0.05 mm) |
| Mutation check of the new test (thicker hook/clip arm, deeper overlap, longer lip, wrong modulus, wrong strength) | 6 of 6 killed; control run passes |
| Finding | the **0.9 mm clip-lip variant of the fit sample exceeds the chosen-variant limit** (0.85 % strain, 21.7 MPa = 62 % of the Z strength, limit 0.8 % / 60 %); it passes the looser variant tier (stress ≤ 80 %). My first variant criterion ("1/3 of the elongation at break") was inconsistent (it would allow 44 MPa, above the 35 MPa strength) and was replaced by the stress criterion before the final run |

Not verified: strength and fatigue of printed hooks and clips (typical datasheet values, not guaranteed minima; the margins are design choices), friction forces, fit of real boards, airflow, thermal and RF behaviour.

## 2026-11-27 (night) — enclosure rev03 (accepted by the owner as the concept) and R17

rev03 was designed by a subagent (R1-R16), then changed by me on the owner's requests (engraved name font, keyholes, R17). **Nothing printed, nothing measured.**

| Check | Result |
|---|---|
| `py -3.12 hardware/enclosure-3d/build.py` (all 8 STLs) + `mesh_check` | all PASS; lid: 0 open edges, 0 degenerate faces, thinnest wall 0.93 mm (the first font attempt left a 0.80 mm spot, closing radius raised to 0.45 mm; 0.43 produced a degenerate sliver) |
| `py -3.12 hardware/enclosure-3d/assembly_check.py --png` | **66 / 66** (includes the new R17 checks: both keyholes on one horizontal line, symmetric, spacing = printed number; marks recessed 0.4 mm, probed on the saved STL) |
| `py -3.12 -m pytest tests/unit` | **134 passed** (133 + the new R17 parameter test) |
| Mounted size from my own render of the STLs | 78.8 x 69.5 x 30.5 mm, equal to the agent's report |
| Finding 1 (fixed) | the agent's engraved name read "gatoway" in the proof: Liberation Sans Bold closed the aperture of the "e" under the 0.8 mm closing; ~10 fonts tried, Bahnschrift Bold at size 10, outline shift 0.0 keeps the "e" open (judged on renders; strokes at the recess floor >= 2 mm: 0.38 % narrower, limit 0.5 %) |
| Finding 2 | Bahnschrift is a Windows system font: rebuilding on another machine changes the text; the committed STLs are fine |

Not verified: legibility of the 0.6 mm engraving and the 0.4 mm drilling marks on a real print, thermal separation of the baffle, airflow, RF with the 10.5 mm keep-out, fit of real boards (C6 dimensions assumed equal to the S3), snap-fit cycle life.

## Hardware checks pending

- First flash of both XIAO boards and port identification (`detect_port.py` has never seen a real XIAO).
- C6 RCP ↔ S3 host over UART (pins, baud, EN/BOOT wiring, RF switch): does the host read the RCP version and form a Zigbee network?
- Matter commissioning with Alexa; BLE scan while Wi-Fi is active.

## References

- `project_specification_and_requirements.md` §4A (acceptance test), `docs/OPEN_QUESTIONS.md` §1–§2, `docs/ENVIRONMENT.md` §2.
