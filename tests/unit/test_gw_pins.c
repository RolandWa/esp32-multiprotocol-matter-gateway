/* Pin-map sanity (docs/CODING_GUIDELINES.md section 3). The numbers themselves are checked against the KiCad
 * schematic by tests/unit/test_pin_map.py; this file checks the rules that hold for any map.
 *
 * Sets below: exposed pads from the Seeed XIAO KiCad library (docs/MCU_NOTES.md section 3, verified there);
 * USB / strapping / RF-switch pins are datasheet / Seeed-wiki knowledge that is NOT machine-checked here. */
#include <stdbool.h>
#include <stddef.h>

#include "gw_pins.h"
#include "minitest.h"

typedef struct {
    const char *name;
    int gpio;
} pin_t;

static const pin_t S3_PINS[] = {
    {"RCP_UART_TX", GW_S3_PIN_RCP_UART_TX}, {"RCP_UART_RX", GW_S3_PIN_RCP_UART_RX},
    {"RCP_UART_RTS", GW_S3_PIN_RCP_UART_RTS}, {"RCP_UART_CTS", GW_S3_PIN_RCP_UART_CTS},
    {"I2C_SDA", GW_S3_PIN_I2C_SDA}, {"I2C_SCL", GW_S3_PIN_I2C_SCL},
    {"C6_EN_DRIVE", GW_S3_PIN_C6_EN_DRIVE}, {"C6_BOOT_DRIVE", GW_S3_PIN_C6_BOOT_DRIVE},
};

static const pin_t C6_PINS[] = {
    {"RCP_UART_TX", GW_C6_PIN_RCP_UART_TX}, {"RCP_UART_RX", GW_C6_PIN_RCP_UART_RX},
    {"RCP_UART_RTS", GW_C6_PIN_RCP_UART_RTS}, {"RCP_UART_CTS", GW_C6_PIN_RCP_UART_CTS},
    {"BOOT", GW_C6_PIN_BOOT},
};

#define N(a) (sizeof(a) / sizeof((a)[0]))

static bool in_set(int gpio, const int *set, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        if (set[i] == gpio) {
            return true;
        }
    }
    return false;
}

/* XIAO ESP32-S3 pads D0..D10 = GPIO1,2,3,4,5,6,43,44,7,8,9 ; XIAO ESP32-C6 D0..D10 = GPIO0,1,2,21,22,23,16,17,19,20,18
 * (the C6 BOOT pad is GPIO9, exposed as a small pad, not as a D-pin). */
static const int S3_EXPOSED[] = {1, 2, 3, 4, 5, 6, 43, 44, 7, 8, 9};
static const int C6_EXPOSED[] = {0, 1, 2, 21, 22, 23, 16, 17, 19, 20, 18, 9};
static const int S3_USB[] = {19, 20};
static const int C6_USB[] = {12, 13};
static const int C6_RF_SWITCH[] = {3, 14};         /* GPIO3 powers the U.FL switch, GPIO14 selects the antenna (Seeed wiki) */
static const int S3_STRAPPING[] = {0, 3, 45, 46};  /* datasheet; GPIO3 = JTAG source select */
static const int C6_STRAPPING[] = {4, 5, 8, 9, 15};

static void test_no_gpio_is_used_twice(void)
{
    for (size_t i = 0; i < N(S3_PINS); i++) {
        for (size_t j = i + 1; j < N(S3_PINS); j++) {
            CHECK(S3_PINS[i].gpio != S3_PINS[j].gpio);
        }
    }
    for (size_t i = 0; i < N(C6_PINS); i++) {
        for (size_t j = i + 1; j < N(C6_PINS); j++) {
            CHECK(C6_PINS[i].gpio != C6_PINS[j].gpio);
        }
    }
}

static void test_every_pin_is_exposed_on_the_xiao_it_belongs_to(void)
{
    for (size_t i = 0; i < N(S3_PINS); i++) {
        CHECK(in_set(S3_PINS[i].gpio, S3_EXPOSED, N(S3_EXPOSED)));
    }
    for (size_t i = 0; i < N(C6_PINS); i++) {
        CHECK(in_set(C6_PINS[i].gpio, C6_EXPOSED, N(C6_EXPOSED)));
    }
}

static void test_no_pin_is_on_usb_or_on_the_c6_rf_switch(void)
{
    for (size_t i = 0; i < N(S3_PINS); i++) {
        CHECK(!in_set(S3_PINS[i].gpio, S3_USB, N(S3_USB)));
    }
    for (size_t i = 0; i < N(C6_PINS); i++) {
        CHECK(!in_set(C6_PINS[i].gpio, C6_USB, N(C6_USB)));
        CHECK(!in_set(C6_PINS[i].gpio, C6_RF_SWITCH, N(C6_RF_SWITCH)));
    }
}

static void test_strapping_pins_are_only_the_justified_ones(void)
{
    /* S3 GPIO3 = RTS: reserved and unused by the firmware (the vendor stack has no flow control), so nothing drives it.
     * C6 GPIO9 = BOOT: strapping on purpose; the S3 pulls it through R4 only while the host flashes the RCP. */
    for (size_t i = 0; i < N(S3_PINS); i++) {
        if (in_set(S3_PINS[i].gpio, S3_STRAPPING, N(S3_STRAPPING))) {
            CHECK_EQ(S3_PINS[i].gpio, GW_S3_PIN_RCP_UART_RTS);
        }
    }
    for (size_t i = 0; i < N(C6_PINS); i++) {
        if (in_set(C6_PINS[i].gpio, C6_STRAPPING, N(C6_STRAPPING))) {
            CHECK_EQ(C6_PINS[i].gpio, GW_C6_PIN_BOOT);
        }
    }
}

static void test_the_link_crosses_tx_and_rx_and_the_c6_uses_its_default_uart0_pins(void)
{
    CHECK(GW_S3_PIN_RCP_UART_TX != GW_S3_PIN_RCP_UART_RX);
    CHECK(GW_C6_PIN_RCP_UART_TX != GW_C6_PIN_RCP_UART_RX);
    /* IDF v6.0.2 soc/esp32c6/include/soc/uart_pins.h: U0TXD = 16, U0RXD = 17; esp32s3: U0TXD = 43, U0RXD = 44 */
    CHECK_EQ(GW_C6_PIN_RCP_UART_TX, 16);
    CHECK_EQ(GW_C6_PIN_RCP_UART_RX, 17);
    CHECK_EQ(GW_S3_PIN_RCP_UART_TX, 43);
    CHECK_EQ(GW_S3_PIN_RCP_UART_RX, 44);
}

static void test_s3_link_runs_on_uart1_so_uart0_can_stay_the_console_peripheral(void)
{
    CHECK_EQ(GW_S3_RCP_UART_PORT, 1);
    CHECK_EQ(GW_C6_RCP_UART_PORT, 0);
}

static void test_baud_is_a_standard_rate_supported_by_both_sides(void)
{
    CHECK_EQ(GW_RCP_UART_BAUD, 460800);
}

int main(void)
{
    RUN(test_no_gpio_is_used_twice);
    RUN(test_every_pin_is_exposed_on_the_xiao_it_belongs_to);
    RUN(test_no_pin_is_on_usb_or_on_the_c6_rf_switch);
    RUN(test_strapping_pins_are_only_the_justified_ones);
    RUN(test_the_link_crosses_tx_and_rx_and_the_c6_uses_its_default_uart0_pins);
    RUN(test_s3_link_runs_on_uart1_so_uart0_can_stay_the_console_peripheral);
    RUN(test_baud_is_a_standard_rate_supported_by_both_sides);
    return MT_SUMMARY();
}
