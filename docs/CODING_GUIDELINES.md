# Coding guidelines (firmware)

Conventions carried over from the previous project, plus the mistakes that taught them. They are rules for the **agent and
the owner alike**; when a rule is wrong for a case, change the rule here in the same commit.

## 1. Principles

1. **Pure logic separated from hardware.** Anything that can be expressed without the ESP-IDF headers goes to `firmware/common/`
   (plain C99: `<stdint.h>`, `<stddef.h>`, `<string.h>`, …) and gets a host unit test. Hardware access (GPIO, UART, I2C, NVS, radio, FreeRTOS)
   lives in thin wrappers that call the pure code. The old project's VTarget calibration was moved this way (`vtarget_cal.c` pure,
   `vtarget_pwm.c` hardware) and ended up with 550+ host checks for ~230 lines.
2. **One source of truth** for every number: pins in one per-target header, protocol constants in one header shared by both chips, component
   values in the KiCad schematic. Never retype a value into a comment or a doc; link to it.
3. **Deterministic, reviewable generated code** (see `TESTING.md` §5). Never edit a generated file by hand.
4. **Prefer boring.** Use the vendor's reference architecture (esp-matter bridge example, Espressif RCP/Zigbee host components) and add
   only what the product needs. Divergence needs a written reason in the commit or a doc.
5. **Say what was measured.** Comments that explain a constant should cite the measurement or datasheet, not a feeling
   ("τ ≈ 145 ms with R4=22k, R5=43k, C2=10µF → wait ≥ 0.5 s").

## 2. Project structure

* Two IDF projects: `firmware/host-esp32s3/` and `firmware/rcp-esp32c6/`, each with `CMakeLists.txt`, `main/`, `sdkconfig.defaults` and
  `sdkconfig.defaults.<target>`. Shared pure code is pulled in as an IDF component (`EXTRA_COMPONENT_DIRS ../common`) — keep its
  `CMakeLists.txt` free of target-specific logic so the host `Makefile` and IDF compile the same files.
* One subsystem = one `.c`/`.h` pair, `snake_case` names, public API in the header only. Shared constants in one header (the old
  project's `constants.h`/`dap_configuration.h` pattern) — not scattered `#define`s.
* esp-matter code is C++; keep that layer thin (endpoint/cluster wiring) and call into C modules for decisions.
* Commit `dependencies.lock`; never commit `sdkconfig`, `managed_components/`, build output.

## 3. Per-target configuration and pins (the most expensive lesson)

In the old project one code base served ESP8266/ESP32/C3/S3. Hard-coded values that were correct on one chip were wrong on another:

| What the code said | C3 | S3 | ESP32 |
|---|---|---|---|
| `ADC1_CHANNEL_2` ("GPIO2") | GPIO2 ✔ | **GPIO3** ✘ (comment lied) | **GPIO38** ✘ (not even on the module pins) |
| PWM output on `GPIO3` | free | **same pad as the ADC input above** ✘ | **UART0 RX = console input** ✘ |

(from the IDF headers `soc/<chip>/include/soc/adc_channel.h`; verified 2026-11-25; the S3 and ESP32 builds only *compiled*, they were never run)

Rules:

* **No GPIO number or ADC channel outside the per-target pin header.** Name functions, not numbers: `GW_PIN_RCP_UART_TX`, `GW_PIN_I2C_SDA`.
  Select the header with the chip macro (`CONFIG_IDF_TARGET_ESP32S3` / `…ESP32C6`) in one thin file; the pure part of the header (the
  numbers) must be includable on the host so a test can read it.
* **Derive ADC channels from the GPIO**, not the other way round (`adc1_pad_get_io_num` / the `ADC1_CHANNEL_x_GPIO_NUM` macros), or assert
  at build time that the pair matches (`_Static_assert`).
* **Pin-map unit test** per target (write it before the first board is designed):
  1. no two functions on one GPIO; 2. none on the console UART (S3: GPIO43/44, C6: GPIO16/17 — XIAO D6/D7), none on USB D+/D− (S3 GPIO19/20),
  3. none on a strapping pin unless justified in a comment; 4. ADC functions only on ADC1 pads (ADC2 is unusable while Wi-Fi runs),
  5. every pin exists on the board/module that is actually used (XIAO C6/S3 expose a subset — see `MCU_NOTES.md`).
* Pins that are part of the **PCB** are set in the schematic first; the header follows the schematic (and a note in the PR says so).
  The old project froze its UART pins as "board-specific, never sync from upstream" — same principle.

## 4. The link between the two chips

* The **C6 is a radio co-processor**: use Espressif's standard RCP firmware and host components for 802.15.4 (Spinel over UART with HDLC-style
  framing) rather than inventing a protocol. Custom code only adds *supervision*: detect a dead/reset RCP, re-initialise, report versions.
  (Which RCP/host stack exactly — and whether the C6 is supported by the chosen example — is an open question, see `OPEN_QUESTIONS.md`.)
* Use **hardware flow control (RTS/CTS)** at ≥ 460 800 baud; the host must not lose bytes while Wi-Fi bursts or flash writes stall it.
* Route **EN (reset) and BOOT of the C6 to GPIOs of the S3** in the hardware design so the host can reset the RCP and update its firmware
  (esp-serial-flasher style). Decide this *before* the PCB is laid out; it cannot be fixed by firmware. (Suggestion — verify against Espressif's Zigbee gateway reference design.)
* Version handshake at start-up: host refuses an RCP whose protocol/firmware version it does not know, and says so on the console.
* Any custom framing (if ever needed) lives in `firmware/common/`, has fixed-vector tests in C **and** the tool language, handles resync after
  garbage, bounded lengths and CRC failure, and is versioned.

## 5. Tasks, timing, memory

* Decide task priorities and core affinity once, in one place, and write them down (the old S3 build pinned the DAP task to core 1 to keep it
  away from Wi-Fi; a Matter bridge has its own recommendations — follow esp-matter's example configuration first).
* **High-priority events** (water leak, valve/socket commands) are never queued behind low-priority work (periodic BLE scans, sensor polling,
  logging). Use separate queues/priorities and a unit-tested policy function for "what to do next".
* No blocking calls in callbacks/ISRs; every wait has a timeout and a defined failure behaviour; a watchdog covers the main loops.
* **Settling and RC time constants are real**: when something analog changes, wait for it (the old VTarget filter needed ≈ 1 s; scripts that
  waited 0.4 s measured nonsense for weeks). Expose a "settled" state instead of guessing in the client.
* Budget RAM/flash early. PDF numbers (Wi-Fi+lwIP 120–160 KB, NimBLE 60–90 KB, ZBOSS 100–150 KB, CHIP 180–250 KB on a 512 KB-SRAM C6) are **unverified**;
  measure with `idf.py size-components` and `heap_caps_get_free_size`, and keep the figures in a doc.

## 6. Configuration, secrets, persistence

* Feature toggles and tunables: **Kconfig** (`main/Kconfig.projbuild`) with defaults in `sdkconfig.defaults*`; avoid hand-edited `#define` headers.
  (The old project used a git-ignored `wifi_configuration.h` for credentials *and* toggles — mixing them hid configuration from review.)
* **Secrets never enter git:** Wi-Fi credentials, Matter setup PIN/discriminator, commissioning/DAC material. Use `secrets.h`, `sdkconfig.local` or NVS
  provisioning (all git-ignored already). Production Matter credentials need the manufacturing flow of esp-matter (factory partition), not the test values.
* **NVS**: one namespace per module, documented keys, versioned values, graceful handling of a missing key (first boot) and of a corrupt value.
  Persist BSEC calibration state periodically (not every sample; flash wear) and restore it at boot.
* The old project stored the selected calibration table in NVS and re-applied the last request when it changed — copy that pattern for "which RCP"/"which profile" settings.

## 7. Errors and logging

* Return `esp_err_t` from hardware wrappers; `ESP_ERROR_CHECK` only for start-up code that cannot continue; never in a periodic path.
* One log tag per module; log **decisions and unusual states** at `W`/`E`, normal operation at `I`, chatty detail at `D`/`V` (rate-limit anything periodic).
* Log versions of both chips at start-up (IDF tag, esp-matter tag, firmware git describe, RCP version).
* Keep a tiny **line-based UART/USB console** for bring-up (`s` status, `v` versions, `reboot` — the full word, so stray bytes after flashing cannot reboot
  the board). It paid for itself repeatedly in the previous project.

## 8. Style

* C99 for pure modules (compiled with `-Wall -Wextra -Werror -pedantic` on the host); IDF's default standard for the rest; C++17 only where esp-matter requires it.
* `snake_case` for files/functions/variables, `UPPER_CASE` for macros/constants, project prefix (`gw_`) on public symbols of `common/`.
* Fixed-width integer types for anything on the wire or in NVS; explicit endianness; `static` by default; no global mutable state without a comment saying who owns it.
* Integer maths for table lookups/interpolation (state rounding), 32-bit intermediates for 16-bit products, explicit clamping — and tests for the edges.
* Comments explain **why**, cite evidence, and are kept in sync (stale comments that contradicted the schematic misled for weeks).

## 9. Documentation and commits

* Every new/changed document ends with `## References` (datasheets, vendor docs, standards by number).
* Commit in logical portions (firmware+tests+docs / regenerated production files / KiCad), imperative subject, body explains why, no surname/employer/e-mail.
  Never commit without the owner's approval (`AGENTS.md` §2).
* Don't mark anything "working" or tag a release before the hardware checks in `TESTING.md` §6 were done.

## 10. Licences to keep in mind (open question for the owner)

The repo's `LICENSE` file is **GPL-3.0** while the draft README says **MIT**. esp-matter/ESP-IDF are Apache-2.0; **Bosch BSEC is a proprietary, closed-source
library** with its own redistribution terms. Decide the project licence and check BSEC's terms before publishing binaries (`OPEN_QUESTIONS.md`).

## References

- ESP-IDF coding style: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/contribute/style-guide.html>
- ESP-IDF Kconfig project configuration: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/kconfig.html>
- ESP-IDF ADC and Wi-Fi/ADC2 limitation: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/adc.html>
- esp-matter bridge example and Zigbee bridge: <https://github.com/espressif/esp-matter/tree/main/examples>
- esp-zigbee-sdk (RCP/host): <https://github.com/espressif/esp-zigbee-sdk>
- Bosch BSEC: <https://www.bosch-sensortec.com/software-tools/software/bme680-software-bsec/>
- Previous project: `../wireless-esp8266-dap/main/vtarget_cal.c`, `tests/unit/`, `.github/copilot-instructions.md`
