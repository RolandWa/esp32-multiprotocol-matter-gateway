# Testing strategy

Distilled from the previous project, where this approach caught real problems (stale generated tables, a pin that was
both PWM output and ADC input on one chip, a settle time shorter than the circuit's time constant, BOM/schematic drift).
The key idea: **keep logic out of the code that touches hardware**, so almost everything can be tested on the PC in seconds,
and keep an explicit, honest list of what can only be tested on a board.

## 1. The layers

| # | Layer | Needs | Where | Run |
|---|---|---|---|---|
| 1 | **Host unit tests (C)** — pure logic: framing, state machines, math, tables, pin-map sanity | gcc + make (WSL) | `tests/unit/test_*.c`, code in `firmware/common/` | `make -C tests/unit test` / `san` |
| 2 | **Tool/script tests (Python)** — KiCad tools, flash/port scripts, generators | Python 3.12 + pytest | `tests/unit/test_*.py` | part of `pytest tests/unit` |
| 3 | **Generated-file freshness** — committed generated code equals what the generator produces | Python | a pytest next to the generator | `pytest tests/unit` |
| 4 | **Cross-language contract tests** — the same byte vector asserted in C and Python | both | one fixed vector in both test files | `pytest tests/unit` |
| 5 | **Build regression** — every image builds for its target with a clean build dir; other targets too if shared code changed | WSL + IDF | `scripts/build.bat` per image | see §4 |
| 6 | **Hardware tests** — radios, UART link, sensors, power, enclosure | boards (+ instruments) | `tests/hw/` *(planned)*, never collected by plain `pytest` | manual / scripted |

`python -m pytest tests/unit -v` runs layers 1–4 (the C tests are built and run by `tests/unit/test_c_unit_tests.py`: native gcc on
Linux/CI, WSL gcc on Windows; it also runs the **sanitizer build** and checks that every `RUN(...)` line really executed).
Verified 2026-11-25: 30 tests pass.

## 2. Writing host unit tests (C)

* Put logic in `firmware/common/*.c|h` with **no ESP-IDF include** (`<stdint.h>`, `<string.h>`, … only). The Makefile links every
  `tests/unit/test_<x>.c` with all `.c` files of `PURE_DIRS`; one include of `esp_log.h` and the file no longer builds on the host —
  that is the intended pressure.
* Use `tests/unit/minitest.h` (`CHECK`, `CHECK_EQ`, `RUN`, `MT_SUMMARY`). Keep each `RUN(test_x);` on its own line (the pytest runner counts them).
* Build flags are strict on purpose: `-std=c99 -Wall -Wextra -Werror -pedantic`; the `san` target adds ASan + UBSan.
* **Implemented (2026-11-27)**, one `tests/unit/test_gw_<module>.c` per module of `firmware/common`: BTHome parser (incl. every prefix of a valid
  packet and 20 000 random buffers under ASan/UBSan), Matter unit conversions, ventilation hysteresis, report gate, sensor table, RCP
  supervisor state machine. Python side: `test_bthome_contract.py` (C parser vs. an independent Python decoder on generated and damaged
  packets) and `test_firmware_layout.py` (vendor files unchanged, pure-C rule, CMake/test coverage, partition tables, size budget of a
  built image). Every wait loop in a test has a step limit (a broken module must fail, not hang).
* What else to test (examples for this product, not implemented yet):
  * **Inter-chip link supervision** (host ↔ RCP). If Espressif's standard RCP (Spinel over UART) is used, its framing belongs to Espressif's
    components — test only *our* code around it: dead-RCP detection and restart policy, version/handshake decision, reset/boot GPIO sequence
    (as a pure state machine with injected time). Only if a custom framing is ever added: frame encode/decode, CRC/FCS, escaping,
    resynchronisation after garbage, oversize frames, split reads — with fixed byte vectors, asserted in C and in any host-side tool.
  * **Zigbee/BLE → Matter mapping tables** (device type → endpoint/cluster), including unknown device types.
  * **Sensor math & debouncing**: BME680 value scaling, IAQ thresholds with hysteresis ("ventilate" flag must not flap), stale-data timeouts.
  * **Priority/queue logic** for high-priority events (water leak, valve/socket commands) vs. low-priority periodic scans.
  * **Per-target pin maps**: a test that includes each target's pin header and asserts *no two functions share a pin*, no function uses
    the console UART, USB pins or a strapping pin (see `CODING_GUIDELINES.md` §3 and `MCU_NOTES.md`).
* Test **boundaries and failure paths**, not only the happy path: min/max, one past the limit, NULL, empty, truncated, oversized.
* A test file is a template when it says so (`test_example_sat.c`): copy, then delete the template with its module.

## 3. Mutation sanity check (do it for every new test file)

A test that passes on the first run might test nothing. Before trusting new tests, break the code on purpose in a **temporary copy** and
confirm the tests fail, e.g.:

* invert a comparison or a flag, drop a boundary check, return the wrong end of an interpolation;
* corrupt one entry of a generated table;
* make a case-insensitive lookup case-sensitive.

The previous project ran 5–6 such mutations per module; all were caught, and the same method was used on the Python tools
(`kicad_lib`/`kicad_set_fields`/`kicad_bom_check`/`flash.bat`: 5 of 5 killed on 2026-11-25). Restore and verify the restore.
Never leave a mutated file behind; work on a copy (WSL `mktemp -d`) or back up and compare afterwards.

## 4. Build regression

A change in shared code can break a *different* image or target than the one you built. For this product the minimum is **both images**:

```powershell
& .\scripts\build.bat --project firmware/host-esp32s3 --target esp32s3 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --extra-export '~/esp/esp-matter/export.sh' --clean
& .\scripts\build.bat --project firmware/rcp-esp32c6  --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --clean
```

* Read the compiler warnings **of the files you touched**; pre-existing warnings from other components are not yours, but say so
  (compare with a baseline: `git stash`/worktree of the previous commit, same command).
* Each target needs its toolchain installed (`~/.espressif/tools`). A missing toolchain fails at *configure* time with
  "compiler not found" — that is an environment problem, not a code problem (install with `install.sh <target>`).
* If you also keep a dev-kit/other-target build (e.g. ESP32-C3), build it too whenever you touch `firmware/common/`.
* Use a **separate source copy and build dir** per experiment (`--work ~/work_exp`) so the main build dirs stay untouched; delete them afterwards (they are large).
* CI idea (not set up): GitHub Actions with `espressif/esp-idf-ci-action` for the IDF builds + a plain Ubuntu job for `pytest tests/unit`.
  The old project's CI mirrored the local WSL build for exactly this reason.

## 5. Generated code and data

If a table/header is generated from measurements or specs (the old project generated per-board calibration tables from CSV sweeps):

* the generator is **deterministic** (no timestamps) and has a `--check` mode that exits 1 when the committed file is stale;
* a pytest runs the generator in memory and compares with the committed file;
* a C test checks the generated data against the *source* data (here: the measured curves), not only against itself;
* the file header says "GENERATED – do not edit"; `AGENTS.md`/`copilot-instructions` repeat it.

## 6. Hardware tests (planned — keep this list honest)

Mark each item with date, firmware versions of **both** chips, and result. Do not tick an item that was only built or simulated.

- [ ] UART link S3 ↔ C6: bring-up, version handshake, throughput at the chosen baud, **RTS/CTS** back-pressure (host stalls while flashing/Wi-Fi bursts),
      garbage/disconnect recovery (pull the C6 reset)
- [ ] Zigbee: pair, rejoin after power cycle, 10+ end devices, **water-leak sensor event latency** under Wi-Fi + BLE load, channel plan vs. Wi-Fi channel
- [ ] BLE: passive scan duty cycle, packet loss while Zigbee is active (the reason for two chips)
- [ ] Matter: commission to Alexa over Wi-Fi, bridged endpoints visible/controllable, behaviour after router reboot and after host reboot
- [ ] BME680: readings sane vs. a reference, **self-heating from the enclosure/modules** (does temperature drift by minutes after power-on?), IAQ calibration state
      persisted in NVS across reboots
- [ ] Power: 5 V rail sag during Wi-Fi TX bursts (scope), brown-outs, behaviour on weak USB supplies
- [ ] RF: antenna isolation (target ≈ 10 cm, ≥ 6 cm acceptable — owner's decision; measure Zigbee RSSI/packet loss while the host runs Wi-Fi traffic at 6 / 10 / 15 cm), range test, receiver desensitisation of the C6 while the S3 transmits
- [ ] Enclosure: fit of PCB/standoffs/USB-C, SMA bulkheads, BME680 airflow/thermal isolation, temperature of the modules in the closed case
- [ ] Soak test (days) with logs; watchdog resets counted

Keep results in a dated `tests/TEST_RESULTS.md` (as the old project did): date, board id, firmware versions, instrument, raw numbers, verdict.
Hardware scripts take the **port/IP as an explicit argument** (never auto-pick between two identical USB devices) and live under `tests/hw/`
so that a plain `pytest` can never drive a board.

## 7. Reporting a result (what the owner expects to read)

* "N unit tests pass (C incl. ASan/UBSan + Python)", "both images build clean from scratch with warnings from my files: none",
* "not run: <hardware items / other targets / reasons>",
* mutation checks done (what was broken, what failed),
* anything surprising (pre-existing warnings, flaky tests).

## References

- Previous project's unit-test setup: `../wireless-esp8266-dap/tests/unit/` (C tests + pytest + generator `--check`)
- ESP-IDF unit testing and host tests: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/unit-tests.html>
- AddressSanitizer / UBSan (gcc): <https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html>
- GitHub Actions for ESP-IDF: <https://github.com/espressif/esp-idf-ci-action>
- esp-matter (Matter bridge/endpoint model): <https://docs.espressif.com/projects/esp-matter/>
