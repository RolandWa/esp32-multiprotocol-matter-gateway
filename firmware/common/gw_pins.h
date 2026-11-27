/**
 * gw_pins.h - GPIO numbers of the hand-wired gateway (numbers only, pure C, includable on the host).
 *
 * SINGLE SOURCE OF TRUTH is the KiCad schematic hardware/kicad/gw.kicad_sch (owner's decision 2026-11-27:
 * "pins as in the schematic"). This header follows it; tests/unit/test_pin_map.py exports the netlist with
 * kicad-cli and fails when a number here differs from the schematic. Change the schematic first, then this file.
 * Never write a GPIO number anywhere else in the firmware (docs/CODING_GUIDELINES.md section 3).
 *
 * Naming: GW_S3_* = U1 XIAO ESP32-S3 (host), GW_C6_* = U2 XIAO ESP32-C6 (802.15.4 RCP). The generic aliases
 * GW_PIN_* at the end select the right set from the IDF target macro.
 *
 * RTS/CTS: both wires exist in the schematic and the pins are reserved here, but the standard Espressif stack cannot
 * use them: esp_openthread_uart_config_t (RCP) and esp_zb_uart_config_t (host) carry only rx_pin/tx_pin, and the
 * vendor configs hard-code UART_HW_FLOWCTRL_DISABLE (ESP-IDF v6.0.2, esp-zigbee-lib 1.6.9). Flow control stays OFF.
 */
#ifndef GW_PINS_H
#define GW_PINS_H

/* ---- U1: XIAO ESP32-S3 (host) ------------------------------------------------------------------------------- */
#define GW_S3_PIN_RCP_UART_TX     43  /* D6, net S3_TX_C6_RX   -> C6 RX                                    */
#define GW_S3_PIN_RCP_UART_RX     44  /* D7, net C6_TX_S3_RX   <- C6 TX                                    */
#define GW_S3_PIN_RCP_UART_RTS     3  /* D2, net S3_RTS_C6_CTS (reserved, unused; GPIO3 is a strapping pin) */
#define GW_S3_PIN_RCP_UART_CTS     4  /* D3, net C6_RTS_S3_CTS (reserved, unused)                          */
#define GW_S3_PIN_I2C_SDA          5  /* D4, net I2C_SDA       BME680                                       */
#define GW_S3_PIN_I2C_SCL          6  /* D5, net I2C_SCL       BME680                                       */
#define GW_S3_PIN_C6_EN_DRIVE      1  /* D0, net C6_EN_DRV   -> R3 -> C6 CHIP_EN                            */
#define GW_S3_PIN_C6_BOOT_DRIVE    2  /* D1, net C6_BOOT_DRV -> R4 -> C6 BOOT                               */
#define GW_S3_RCP_UART_PORT        1  /* UART_NUM_1 as in the vendor app_zboss.h (UART0 stays the console)  */

/* ---- U2: XIAO ESP32-C6 (RCP) -------------------------------------------------------------------------------- */
#define GW_C6_PIN_RCP_UART_TX     16  /* D6, net C6_TX_S3_RX   = the chip's UART0 default TX                 */
#define GW_C6_PIN_RCP_UART_RX     17  /* D7, net S3_TX_C6_RX   = the chip's UART0 default RX                 */
#define GW_C6_PIN_RCP_UART_RTS     2  /* D2, net C6_RTS_S3_CTS (reserved, unused)                           */
#define GW_C6_PIN_RCP_UART_CTS    21  /* D3, net S3_RTS_C6_CTS (reserved, unused)                           */
#define GW_C6_PIN_BOOT             9  /* BOOT pad = GPIO9 (strapping), driven by the S3 through R4           */
#define GW_C6_RCP_UART_PORT        0  /* ot_rcp uses UART0 (esp_ot_config.h)                                 */

/* ---- Link parameters shared by both sides -------------------------------------------------------------------- */
#define GW_RCP_UART_BAUD      460800  /* vendor default of ot_rcp (esp_ot_config.h) and of the host (app_zboss.h) */

/* ---- Generic aliases for the image being built --------------------------------------------------------------- */
#if defined(CONFIG_IDF_TARGET_ESP32S3)
#define GW_PIN_RCP_UART_TX GW_S3_PIN_RCP_UART_TX
#define GW_PIN_RCP_UART_RX GW_S3_PIN_RCP_UART_RX
#define GW_PIN_I2C_SDA     GW_S3_PIN_I2C_SDA
#define GW_PIN_I2C_SCL     GW_S3_PIN_I2C_SCL
#elif defined(CONFIG_IDF_TARGET_ESP32C6)
#define GW_PIN_RCP_UART_TX GW_C6_PIN_RCP_UART_TX
#define GW_PIN_RCP_UART_RX GW_C6_PIN_RCP_UART_RX
#endif

#endif /* GW_PINS_H */
