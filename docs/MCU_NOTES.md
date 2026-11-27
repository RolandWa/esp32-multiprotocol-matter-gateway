# MCU notes: ESP32-S3, ESP32-C6 (and the C3/ESP32 of the previous project)

Facts for choosing pins, peripherals and tool versions. **Verified** rows were read from the ESP-IDF headers (`components/soc/<chip>/include/soc/*.h`
of `v4.4.2` and of the untagged `v6.1-dev-6354-gd0b65797c30`) or from the Seeed KiCad library on 2026-11-25. **Unverified** rows come from the AI-generated PDF
in the repo root — check them against the datasheets before relying on them.

## 1. Roles in this product

| | Module 1 — host | Module 2 — radio co-processor |
|---|---|---|
| Board | Seeed **XIAO ESP32-S3 Plus** | Seeed **XIAO ESP32-C6** |
| Chip | ESP32-S3 (2× Xtensa LX7) | ESP32-C6 (1× RISC-V) |
| Radios | Wi-Fi 2.4 GHz + BLE; **no 802.15.4** (verified: no `SOC_IEEE802154_SUPPORTED` for the S3) | Wi-Fi 6 + BLE + **IEEE 802.15.4** (verified: `SOC_IEEE802154_SUPPORTED 1`) — used *only* for 802.15.4, Wi-Fi/BLE off |
| Job | esp-matter bridge to Alexa, BLE scanner, Zigbee host, BME680 + BSEC | RCP for Zigbee (and optionally Thread) over UART |
| Memory (PDF, **unverified**) | 8 MB PSRAM, 16 MB flash (Plus) | 512 KB SRAM, no PSRAM, 4 MB flash |
| Clock (PDF, unverified) | 240 MHz | 160 MHz |
| Antenna | external via on-board U.FL (Plus; ship with an FPC antenna) | U.FL, selected by an RF switch (Seeed wiki, via search 2026-11-26: GPIO3 **LOW** powers the switch, then GPIO14 HIGH = U.FL; ESP-IDF does not do it for you — confirm on a board) |
| IDF support | v4.4.2 ✔ (and newer) | **v4.4.2 ✘** (no `esp32c6` in `components/soc`), needs a newer IDF |

Why two chips (PDF, plausible and consistent with Espressif's own Zigbee-gateway design): one RF path and one antenna per SoC means Wi-Fi/BLE time-slicing cannot starve a
Zigbee coordinator that must listen continuously; and a single C6 lacks RAM/flash for Wi-Fi + BLE + Zigbee + Matter together. A *second S3* cannot replace the C6 — the S3
has no 802.15.4 radio. ESP32-H2 is the other 802.15.4 chip (no Wi-Fi) but the XIAO H2 has no U.FL.
Whether **the C6 is a supported RCP for Espressif's `zigbee_bridge` example** is *not settled*: an old GitHub issue says that example did not support the C6, the official
material points to an H2 RCP, the PDF says C6 works. Check the example's README on the release you choose (`OPEN_QUESTIONS.md`).

## 2. Peripherals and ADC (verified)

| | ESP32-S3 | ESP32-C6 | ESP32-C3 (old project) | ESP32 (classic) |
|---|---|---|---|---|
| CPU cores | 2 | 1 | 1 | 2 |
| `SOC_GPIO_PIN_COUNT` | 49 | 31 | — | — |
| UART controllers | 3 | 2 HP + 1 LP | 2 | 3 |
| I2C | 2 | 2 | 1 | 2 |
| LEDC channels | 8 (+4 timers) | 6 (+4 timers) | 6 | 8 + 8 (high/low speed) |
| ADC units | **2** | **1** | **2** | **2** |
| ADC1 channels → GPIO | 10: CH0–9 = GPIO1–10 | 7: CH0–6 = GPIO0–6 | 5: CH0–4 = GPIO0–4 | 8: GPIO36,37,38,39,32,33,34,35 |
| ADC2 channels → GPIO | 10: CH0–9 = GPIO11–20 | — | 1: GPIO5 | 10: GPIO4,0,2,15,13,12,14,27,25,26 |
| Console UART0 default | TX GPIO43 / RX GPIO44 | TX GPIO16 / RX GPIO17 | TX GPIO21 / RX GPIO20 | TX GPIO1 / RX GPIO3 |

*Source of the table:* S3 and C6 columns from the IDF 6.1-dev headers; ADC and LEDC rows of C3/ESP32 from the IDF 4.4.2 headers; the UART/I2C/core counts and console pins of the **C3 and
classic ESP32 are from memory/the XIAO-C3 library** (not re-read from headers).

* **Use ADC1 only.** ADC2 shares hardware with Wi-Fi and its reads can fail/return garbage while Wi-Fi is running (IDF's ADC2 arbiter priority is Wi-Fi > RTC > digital).
  This product runs Wi-Fi continuously on the S3. The C6 has no ADC2 anyway. The BME680 is I2C, so the product needs **no ADC** — only if a supply/battery monitor is added.
* **`ADC1_CHANNEL_2` is a different GPIO on every chip** (C3 → GPIO2, S3 → GPIO3, ESP32 → GPIO38). The previous project hard-coded it and silently used the wrong pad on the S3. Derive the
  channel from the pin with the `ADC1_CHANNEL_x_GPIO_NUM` macros (or `adc1_pad_get_io_num`) and assert it.
* LEDC on the ESP32 has high- and low-speed groups; S3/C6/C3 only low speed.
* ESP32 ADC accuracy is poorer (non-linear, noisy) than S3/C6/C3; use `esp_adc_cal`/the newer calibration and verify with a DMM (the old project's C3 ADC agreed with a DMM within ≈ 11–32 mV).

## 3. XIAO pinouts (verified from the Seeed KiCad library; full table in `HARDWARE_KICAD.md` §5)

* **C6:** D0 = GPIO0 (A0), D1 = GPIO1, D2 = GPIO2, D3 = GPIO21, D4 = GPIO22 (SDA), D5 = GPIO23 (SCL), D6 = **GPIO16 (TX)**, D7 = **GPIO17 (RX)**, D8 = GPIO19 (SCK), D9 = GPIO20 (MISO), D10 = GPIO18 (MOSI).
  ADC pins on the header: D0–D2 (GPIO0–2).
* **S3 (plain):** D0 = GPIO1 … D3 = GPIO4 (all ADC1), D4 = GPIO5 (SDA), D5 = GPIO6 (SCL), D6 = **GPIO43 (TX)**, D7 = **GPIO44 (RX)**, D8 = GPIO7 (SCK), D9 = GPIO8 (MISO), D10 = GPIO9 (MOSI). Pins 23/24 = USB D−/D+.
* **S3 Plus:** adds GPIOs beyond D10 (PDF: "18 GPIO instead of 11"). Pin names/numbers are **not in the library** — get them from Seeed's schematic/footprint (the RTS/CTS lines depend on it).
* UART pins D6/D7 are the *console* UART0 on both boards. For the inter-chip link use a **second UART** with remapped pins (the ESP32 GPIO matrix allows any free GPIO) and keep UART0/USB for service.

## 4. Pin hygiene checklist (apply to both chips; enforced by a host test, `CODING_GUIDELINES.md` §3)

1. Not on the console UART0 pins (S3 GPIO43/44, C6 GPIO16/17) unless the console moves to USB-Serial/JTAG.
2. Not on USB D+/D− (S3: GPIO19/20) when native USB is used (it is, for flashing).
3. **Strapping pins** (boot mode, flash voltage, JTAG source): avoid driving them at reset. The exact lists are in the datasheets — they are **not** in the IDF `soc_caps` headers
   (searched), so copy them from the datasheet into `board_pins.h` with a citation. (From memory, unverified: S3 GPIO0/3/45/46; C6 GPIO4/5/8/9/15.)
4. ADC functions only on ADC1 pads (§2).
5. Exposed on the board that is really used: the XIAO exposes a subset of the chip's pins (the C6 symbol has 11 GPIO pads; the plain S3 has 11).
6. Leave pins for: reset/boot lines of the C6 (from the S3), status LED, I2C pull-up-friendly pins, test points.

## 5. Memory and flash planning (all unverified — measure)

PDF figures for a C6 running everything: Wi-Fi+lwIP+mDNS ≈ 120–160 KB, NimBLE ≈ 60–90 KB, ZBOSS ≈ 100–150 KB, Matter bridge incl. mbedTLS ≈ 180–250 KB of 512 KB SRAM,
and an app image of 2.2–2.8 MB on 4 MB flash (no room for two OTA slots) — the reasons for the split. On the S3 side budget two OTA slots of the Matter image
(PDF: 3–4 MB each) plus NVS/LittleFS for fabric/commissioning data. Replace these numbers with `idf.py size-components` results as soon as images exist.

## 6. Tool-version consequences

* IDF v4.4.2: S3 ✔ C6 ✘ → not for this product. Newer IDF: both ✔ (verified in v6.1-dev headers; the release tag must also match esp-matter, `ENVIRONMENT.md` §3).
* Toolchains: S3 → `xtensa-esp-elf`, C6 → `riscv32-esp-elf`, both of the generation the chosen IDF expects. On this machine the RISC-V toolchain for IDF 6 is installed, the Xtensa one is not.

## References

- ESP32-S3 datasheet / TRM (strapping pins, GPIO matrix, USB): <https://www.espressif.com/en/support/documents/technical-documents>
- ESP32-C6 datasheet / TRM (802.15.4, strapping pins, ADC): same page
- ESP-IDF ADC (ADC2 vs Wi-Fi), GPIO, UART, LEDC API docs: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/>
- Seeed XIAO ESP32-S3 Plus / ESP32-C6 wiki (pinout, U.FL, RF switch): <https://wiki.seeedstudio.com/>
- Espressif Zigbee SDK and RCP examples: <https://github.com/espressif/esp-zigbee-sdk>
- Input material: `Bramka Smarthome na ESP32-C6.pdf` (AI chat export — unverified claims marked above)
