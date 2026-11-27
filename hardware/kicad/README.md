# hardware/kicad — gateway wiring schematic (draft v0.2, no PCB)

`gw.kicad_sch` (**KiCad 9 format**, version 20250114 — the owner's GUI is KiCad 9; also loads in 10; A3, one sheet) was **bootstrapped by a script** on 2026-11-26 and is edited in KiCad from now on — the schematic is the source of truth
(`../../docs/HARDWARE_KICAD.md`). Close KiCad before scripted edits (`../../scripts/kicad_*.py`).

**There is no PCB.** The owner decided (2026-11-26) to solder the two XIAO modules and the BME680 board together with wires or pin headers inside one 3D-printed
enclosure (`../../project_specification_and_requirements.md`, "Decyzje konstrukcyjne"). The schematic is therefore a **wiring diagram + BOM**; footprints are
empty for the modules and only suggested (through-hole) for the few passives. The JLCPCB/LCSC workflow in `HARDWARE_KICAD.md` §2–§3 does not apply unless a PCB is added later.

## What is drawn

| Ref | Part | Role |
|---|---|---|
| U1 | XIAO ESP32-S3 (SMD symbol, **placeholder for the S3 Plus**) | host; its USB-C is the only power input |
| U2 | XIAO ESP32-C6 (SMD symbol) | 802.15.4 RCP, powered from U1's 5V pad |
| J2 | 4 soldered wires | BME680 module: 3V3, GND, SDA, SCL |
| C1 (100 µF), C2 (100 nF) | at the C6 end of the 5 V wire | decoupling |
| C3 (1 F, 5.5 V supercap) | on U1 `BAT` (pin 15) to GND | hold-up for a clean shutdown on mains loss; charged to 4.2 V by the XIAO's own charger (**unverified**), see "Open items" |
| R1, R2 (4k7) | I2C pull-ups to 3V3 | omit if the sensor module already has them |
| R3, R4 (1k) | series resistors, S3 → C6 CHIP_EN / BOOT | |

Nets (checked against the exported netlist; ERC: 0 violations):

| Net | U1 (S3) | U2 (C6) |
|---|---|---|
| `S3_TX_C6_RX` | pin 7 D6/GPIO43 TX | pin 8 D7/GPIO17 RX |
| `C6_TX_S3_RX` | pin 8 D7/GPIO44 RX | pin 7 D6/GPIO16 TX |
| `S3_RTS_C6_CTS` | pin 3 D2/GPIO3 | pin 4 D3/GPIO21 |
| `C6_RTS_S3_CTS` | pin 4 D3/GPIO4 | pin 3 D2/GPIO2 |
| `I2C_SDA` / `I2C_SCL` | pin 5 D4/GPIO5, pin 6 D5/GPIO6 | — (J2, R1, R2) |
| `C6_EN_DRV` → R3 → C6 CHIP_EN | pin 1 D0/GPIO1 | pin 19 |
| `C6_BOOT_DRV` → R4 → C6 BOOT | pin 2 D1/GPIO2 | pin 23 |
| `+5V` | pin 14 (source: USB-C of U1) | pin 14 (input), C1, C2 |
| `Net-(U1-BAT)` | pin 15 BAT → C3 (+) | — (U2 BAT stays unconnected) |
| `GND` | pins 13, 16, 20 (+ C3) | pins 13, 16, 20 |
| `+3V3` | pin 12 (feeds J2, R1, R2) | pins 12 and 24 deliberately **not connected** |

Unused pins carry no-connect flags. `lib/seeed/` is a copy of the previous project's Seeed XIAO library. `documentations/gw_schematic.pdf` is the exported
schematic (regenerate after every change). Every part has hidden fields `Manufacturer`, `MPN`, `TME`, `Mouser`, `Farnell` — only the MPNs of U1 (102010671) and U2 (113991254) are filled so far.

## Open items

* **XIAO ESP32-S3 *Plus* is not in the library.** U1 uses the plain S3 symbol as a placeholder. Seeed wiki (via search, **unverified — check the official pinout**):
  Plus adds D11–D17 = GPIO38/39/40/41/42/10/13. The wiring above only needs D0–D7, which the plain S3 also has.
* **Library quirk:** the Seeed `XIAO-ESP32-S3-DIP` symbol names pin 6 `GPIO9/D5/I2C_SCL` (should be GPIO6). The SMD symbol used here is correct.
* **Power path (not verified):** how the XIAO routes VBUS to its `5V` pad (diode? current limit?) decides whether the S3's 5V pad can carry the C6's current (≈ 100–150 mA, PDF, unverified)
  and whether USB on the C6 back-feeds the host. Read Seeed's schematics. Until then: never plug USB into U2 while U1 is powered, or add a series Schottky in the U1→U2 5 V wire.
* **C6 EN/BOOT pads:** on the XIAO ESP32-C6 these are small pads; check on the real board (Seeed schematic/photos) where to solder the wires and whether the on-board buttons share them.
* **Stacking:** pin headers alone cannot stack the modules (TX↔RX and RTS↔CTS are crossed) — wires or a small perfboard in between. Decide before designing the enclosure.
* **Strapping pins:** S3 D2 = GPIO3 (RTS) is a strapping pin; C6 BOOT is GPIO9 — verify in the datasheets that the planned drivers do not disturb boot.
* **C6 RF switch:** per the Seeed wiki GPIO3 must be driven **LOW** to power the switch, then GPIO14 HIGH selects U.FL; ESP-IDF does not do it for you (forum reports). RCP firmware requirement.
* **Antennas (owner's pick 2026-11-26): adhesive FPC `2JF0802P-010MC137-UFL`, ≈ 1.7 dBi at 2.4 GHz (unconfirmed)** — this is not the "larger external whip" of the earlier decision: gain is about that of the antenna shipped with the XIAO modules (Botland lists an FPC antenna in the S3 Plus package), so the range gain over the bundled antenna is small, and the EIRP concern largely disappears. If range turns out insufficient, switch to SMA whips (pigtail row in the parts list).
* **Supercap C3 on U1 `BAT` (2026-11-26):** the XIAO's charger (reported as SGM40567-4.2, ≈ 110 mA — forum/devboards.info, **unverified**) charges the cap to 4.2 V. Needs a ≥ 5 V rated, **low-ESR** EDLC (Wi-Fi TX peaks ≈ 350 mA; ESR 30 Ω would sag ≈ 10 V). 1 F from 4.2 V to ≈ 3.5 V gives ≈ 6 s at ≈ 120 mA (assumed LDO threshold). U2 has no supply during that time. Check in Seeed's schematic: how the load is fed (charge current shared with the load?), whether `BAT` has under-voltage protection, whether the charger accepts an empty EDLC (start-up inrush).
* **Mains adapter IKEA SJÖSS 20 W** (USB-C only, PD, cable sold separately): needs a USB-C ↔ USB-C cable; a PD source gives 5 V only if the sink has 5.1 kΩ on both CC lines — **unverified for the XIAO ESP32-S3** (check Seeed's schematic; otherwise add 5.1 kΩ CC→GND or an adapter). Measure the 5V pad before connecting the modules. Keep the adapter outside the enclosure.
* **Antenna placement (owner's decision 2026-11-26):** small enclosure, ≈ 10 cm centre-to-centre, less acceptable (not below ≈ 6 cm). With the glued FPC antennas (flat, 39.6 mm long, 10 cm cable each) put them on the **inside of opposite walls** — the centre distance then equals the inner length between those walls, i.e. the enclosure needs ≈ 10 cm in one dimension (e.g. ≈ 10 × 4 × 4 cm); the 10 cm cable also bounds the module-to-wall distance. The "collinear tip-to-tip" rule applies to dipoles, **not** to a flat FPC antenna — its pattern is unknown, so use orthogonal orientation or opposite walls and measure. Wi-Fi ch 1/6 vs Zigbee ch 25, measure packet loss at 6 / 10 / 15 cm — details in `../../project_specification_and_requirements.md`, decision 4.
* Not drawn: status LED, test points, power protection.
* The RCP question (is the C6 a supported RCP for `zigbee_bridge`?) still gates building the final unit (`../../AGENTS.md` §1a #2).

## Parts (TME / Mouser / Farnell only) — status 2026-11-26

Order codes were looked up with a web search, **not on the shops' own pages**; "—" means nothing confirmed. A second attempt (2026-11-26) to read the shop pages failed: TME returns HTTP 403 to automated fetches, Mouser and Farnell timed out. Check them in a browser. Search found no TME / Farnell listing of the S3 Plus or C6, and no Mouser listing of the Plus. Check stock and the exact order code on each shop before buying,
then write the result into the schematic fields (`MPN`, `TME`, `Mouser`, `Farnell`).

| Part | Qty | Found | Not confirmed / to do |
|---|---|---|---|
| Seeed XIAO ESP32-S3 **Plus** | 1 | Seeed MPN **102010671** (Botland listing) | TME / Mouser / Farnell codes: nothing found. For reference: the plain XIAO ESP32S3 (113991114) is at Mouser and TME (TME symbol `SEEED-113991114`); Farnell lists the *Sense* (4200197) — **neither is the Plus** |
| Seeed XIAO ESP32-C6 | 1 | single-unit Seeed MPN **113991254** (search hits: Mouser product page, DigiKey 1597-113991254-ND; Seeed SKU 102010574 is the 3-pack) | Mouser order code (shop pages timed out), TME and Farnell codes: nothing found |
| BME680 module | 1 | Adafruit BME680 breakout (product 3660) and Pimoroni PIM357 exist; Mouser carries Adafruit's STEMMA QT BME680 board | the CJMCU-680 from the requirements is **not** a TME/Mouser/Farnell part. Adafruit's board has its own regulator, level shifting, default address **0x77** (SDO→GND = 0x76) and no CS strap — the strap/pull-up notes in this draft apply to a bare-style module, adjust when the module is chosen. BSEC licence still open (`../../AGENTS.md` §1a #3) |
| Mains adapter IKEA **SJÖSS 20 W** (art. 506.217.28) | 1 | IKEA PL page: 15 zł, USB-C, PD, "up to 3.0 A / 20 W", no cable, 5–35 °C; **not** a TME/Mouser/Farnell part (exception chosen by the owner) | output voltage not stated on the page; manual PDF not read |
| ~~IKEA SITTBRUNN USB-A → USB-C, lilac, 1.0 m, art. 605.959.84, 7 zł~~ | 0 | dropped 2026-11-26: it does not fit the SJÖSS charger (USB-C socket only) | — |
| **USB-C ↔ USB-C cable, IKEA SITTBRUNN, 1.0 m** (owner's decision 2026-11-26: keep the SJÖSS charger, buy this cable) — white **906.185.40** (`ikea.com/pl/pl/p/sittbrunn-usb-c-na-usb-c-bialy-90618540/`) or light green **305.959.85** (≈ 10 zł on the PL listing) | 1 | IKEA PL (web search, product pages not opened): SITTBRUNN 1 m ≈ 10 zł; LILLHULT 60 W 1.5 m 19.99 zł; RUNDHULT 100 W 1.5 m 29.99 zł — the cheapest/shortest is enough | IKEA article number: copy from the product page; the owner assumes the XIAO has 5.1 kΩ on CC (unconfirmed — measure 5 V first) |
| Supercap C3, ≥ 5 V, low ESR (≈ 1 F) | 1 | search hits only: Eaton PB-5R0V105-R (1 F, 5 V, ESR 0.5 Ω, Farnell 2148505 per URL); Kemet FT0H105ZF (1 F, 5.5 V, ESR 3.5 Ω, Mouser); Eaton KR-5R5V105-R is at TME but its ESR (30 Ω) is too high | none checked on shop pages (stock, rating, ESR); also consider the 5.0 V rating against the 4.2 V charge voltage |
| **Antenna, adhesive FPC, U.FL — 2J Antennas `2JF0802P-010MC137-UFL`** (owner's pick from TME) | 2 (one per module) | TME listing text pasted by the owner (shop pages return HTTP 403 to automated fetches): Bluetooth/ISM/LoRa/SIGFOX/WiFi/ZigBee, 2.41–2.49 GHz and 4.92–7.125 GHz, 39.6 × 8.4 × 0.2 mm, glued, cable MC137 0.1 m, U.FL plug, gain "1.7 / 4.6 / 5.1 dBi". TME symbol = the part number as given by the owner. A second TME listing "2JF0802P-010MC137-UFL TRALO" (web search) exists — check which one is in stock | gain **per band is not stated** (1.7 dBi is probably the 2.4 GHz value — unconfirmed; manufacturer datasheet not found); the plug goes straight into the module's U.FL socket → **no SMA pigtail / bulkhead needed**; stock and price on TME; Mouser/Farnell codes not looked up |
| ~~U.FL → SMA bulkhead pigtail~~ | 0 | not needed with the adhesive antennas; only if the owner later switches to external SMA whips | — |
| R1, R2 4k7; R3, R4 1k (through-hole, 0.25 W) | 2 + 2 | candidates *from memory, stock not checked*: Yageo CFR-25JB-52-4K7, CFR-25JB-52-1K | verify |
| C1 100 µF (radial electrolytic, ≥ 10 V), C2 100 nF (ceramic) | 1 + 1 | candidates *from memory, stock not checked*: Panasonic EEU-FR1C101, Kemet C320C104K5R5TA | verify |
| 2.54 mm pin headers, hook-up wire (AWG 26–28), heat-shrink, optional Schottky diode | — | — | pick when the wiring/stacking method is decided |

## References

- Seeed XIAO ESP32-C6 wiki (RF switch GPIO3/GPIO14): <https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/>
- Seeed XIAO ESP32-S3 pin multiplexing (Plus pin map): <https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/>
- Seeed forum thread on switching the C6 antenna: <https://forum.seeedstudio.com/t/xiao-esp32c6-switching-between-builtin-and-external-antenna/276374>
- Mouser XIAO ESP32-S3 113991114: <https://www.mouser.com/ProductDetail/Seeed-Studio/113991114?qs=3Rah4i%2BhyCEHk7Z4Wa73Xg%3D%3D> — TME: <https://www.tme.com/us/en-us/details/seeed-113991114/development-kits-for-data-transmission/seeed-studio/xiao-esp32s3/> — Farnell (Sense): <https://uk.farnell.com/seeed-studio/113991115/development-board-32bit-xtensa/dp/4200197>
- Seeed XIAO ESP32-C6 on Mouser: <https://www.mouser.com/en/new/seeed-studio/seeed-studio-xiao-esp32c6-mcu/> — Seeed 3-pack SKU 102010574: <https://www.seeedstudio.com/Seeed-StudioXIAO-ESP32C6-3PCS-p-5918.html>
- Botland, XIAO ESP32-S3 Plus (MPN 102010671): <https://botland.store/xiao/29648-seeed-xiao-esp32-s3-plus-wifi-bluetooth-16-mb-flash-arduino-micropython-seeedstudio-102010671.html>
- Adafruit BME680 guide (hosted by Mouser): <https://www.mouser.com/datasheet/2/737/adafruit_bme680_humidity_temperature_barometic_pre-1396558.pdf>
- Pigtail loss figures: <https://tejte.com/blog/ufl-to-sma-adapter-cable-guide/>
- Pin tables of the modules: `../../docs/MCU_NOTES.md` §3, `../../docs/HARDWARE_KICAD.md` §5
- Requirements: `../../project_specification_and_requirements.md`
