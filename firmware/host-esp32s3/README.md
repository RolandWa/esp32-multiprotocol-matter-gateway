# host-esp32s3 - host image (XIAO ESP32-S3 Plus): Matter bridge + Zigbee host

Baseline: Espressif's **`zigbee_bridge`** example from **esp-matter `release/v1.6.1`** (commit `4645784`,
SPDX/notice: public domain / CC0), built with **ESP-IDF v6.0.2**. This is the vendor reference architecture
(`docs/CODING_GUIDELINES.md` section 1.4); the product features are added on top, one reviewed step at a time.

## What differs from the vendor example

| File | Change |
|---|---|
| `CMakeLists.txt` | project renamed `gateway_host`; `../common` added to `EXTRA_COMPONENT_DIRS` |
| `main/app_main.cpp` | `#include "gw_boot.h"` and one call `gw_boot_banner();` after `nvs_flash_init()` |
| `main/gw_boot.c`, `main/gw_boot.h` | new: version banner + fixed-vector self-test of `firmware/common` on the target (log only) |

`main/CMakeLists.txt` is deliberately the vendor file: a `main` without `REQUIRES` depends on every component in the build
(including `common`), and adding a `PRIV_REQUIRES` line removed that and broke the include paths of the Matter headers (found when building).
Every other file is byte-identical to the vendor example; `VENDOR_BASELINE.sha256` records the hashes and
`tests/unit/test_firmware_layout.py` fails when one of them changes unnoticed.

## Not implemented yet (needs the owner's decision or a board)

- BLE passive scanner (NimBLE) feeding `gw_bthome` / `gw_sensor_table`, and the Matter bridged Temperature/Humidity endpoints for the
  Xiaomi sensors (decision 3a; BTHome encryption/bindkey is still open).
- BME680 + BSEC, Air Quality endpoint and the "ventilate" flag wiring (`gw_ventilation`); BSEC licence is open (section 5).
- RCP supervision loop around `gw_rcp_supervisor` (needs the EN/BOOT GPIOs, i.e. the pin map, section 4).
- Partition table: the vendor 4 MB layout is used unchanged; the app already fills **97 %** of its 1.8 MB slot, so a 16 MB layout
  (S3 Plus flash size still unverified) is needed before BSEC and the scanner are added.
- The vendor `sdkconfig.defaults` request `ZB_HOST` / `ZB_RADIO_MACSPLIT_UART`, which `esp-zigbee-lib` 1.6.x does not have; they are ignored
  and the library falls back to `ZB_RADIO_SPINEL_UART` (`docs/OPEN_QUESTIONS.md` section 2).

## Build

```powershell
& .\scripts\build.bat --project firmware/host-esp32s3 --target esp32s3 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --extra-export '~/esp/esp-matter/export.sh' --merge
```

Forward slashes in `--project` and a quoted `~` are required in PowerShell (`docs/BUILD_AND_FLASH.md`). Output:
`dist/esp32s3/host-esp32s3_full.bin` (flash at 0x0). `dependencies.lock` is pinned in this directory; when a dependency changes, the build prints the `cp` command to refresh it.

## References

- esp-matter `zigbee_bridge`: <https://github.com/espressif/esp-matter/tree/release/v1.6.1/examples/bridge_apps/zigbee_bridge>
- `docs/ENVIRONMENT.md` section 4, `docs/OPEN_QUESTIONS.md` sections 1-3a, `tests/TEST_RESULTS.md`
