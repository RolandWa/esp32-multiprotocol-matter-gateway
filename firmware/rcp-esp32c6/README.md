# rcp-esp32c6 - 802.15.4 radio co-processor image (XIAO ESP32-C6)

Espressif's standard OpenThread RCP (`ot_rcp`), built for the ESP32-C6, with the one setting the
Zigbee host needs. It is **not** custom code: Wi-Fi and BLE are not used on this chip, the S3 host runs the
Zigbee stack and talks Spinel to this image over UART.

## Provenance

Copied unmodified from **ESP-IDF v6.0.2** `examples/openthread/ot_rcp` (SPDX `CC0-1.0`, public domain):
`CMakeLists.txt`, `partitions.csv`, `sdkconfig.defaults`, `main/*`. The hashes are recorded in
`VENDOR_BASELINE.sha256`; `tests/unit/test_firmware_layout.py` fails if one of these files is edited by accident.

The only gateway-specific file is `sdkconfig.defaults.esp32c6` (`CONFIG_OPENTHREAD_NCP_VENDOR_HOOK=y`).

## Build

```powershell
& .\scripts\build.bat --project firmware/rcp-esp32c6 --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --merge
```

Forward slashes in `--project` and a quoted `~` are required in PowerShell (`docs/BUILD_AND_FLASH.md`). `--tools-path` keeps the old project's `~/.espressif` untouched. Output: `dist/esp32c6/rcp-esp32c6_full.bin` (flash at 0x0).

## Open points (nothing here was run on a board)

- UART number, pins, baud and RTS/CTS are the example's defaults, not the project's decision (`docs/OPEN_QUESTIONS.md` section 4).
- RF switch of the XIAO ESP32-C6 (external antenna) is not configured; the PDF's GPIO numbers are unverified (`docs/MCU_NOTES.md`).
- Whether the S3 host version handshake and the RCP update path work with this image is a hardware check (`tests/TEST_RESULTS.md`).

## References

- ESP-IDF `ot_rcp` example: <https://github.com/espressif/esp-idf/tree/v6.0.2/examples/openthread/ot_rcp>
- esp-zigbee-sdk `zigbee_gateway` (names ESP32-C6 as RCP SoC): <https://github.com/espressif/esp-zigbee-sdk/tree/main/examples/zigbee_gateway>
- `docs/OPEN_QUESTIONS.md` section 2, `docs/ENVIRONMENT.md` section 4
