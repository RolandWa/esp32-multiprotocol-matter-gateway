/* Unit tests for gw_bthome.c. Vectors marked [bthome.io] are examples from https://bthome.io/format/
 * (read 2026-11-27); the rest are derived from the same object table. */
#include <stdint.h>
#include <string.h>

#include "gw_bthome.h"
#include "minitest.h"

#define PARSE(arr, out) gw_bthome_parse((arr), sizeof(arr), &(out))

static int is_zeroed(const gw_bthome_data_t *d)
{
    gw_bthome_data_t z;
    memset(&z, 0, sizeof z);
    return memcmp(d, &z, sizeof z) == 0;
}

static void test_official_example_temperature_and_humidity(void)
{
    /* [bthome.io] D2FC 40 02C409 03BF13 -> 25.00 C, 50.55 % */
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x02, 0xC4, 0x09, 0x03, 0xBF, 0x13};
    gw_bthome_data_t d;
    CHECK_EQ(PARSE(p, d), GW_BTHOME_OK);
    CHECK(d.has_temperature);
    CHECK_EQ(d.temperature_c100, 2500);
    CHECK(d.has_humidity);
    CHECK_EQ(d.humidity_pct100, 5055);
    CHECK(!d.has_packet_id);
    CHECK(!d.has_battery);
    CHECK(!d.has_pressure);
    CHECK(!d.has_voltage);
    CHECK(!d.trigger_based);
    CHECK(!d.stopped_at_unknown);
}

static void test_single_object_examples(void)
{
    gw_bthome_data_t d;
    static const uint8_t temp[] = {0xD2, 0xFC, 0x40, 0x02, 0xCA, 0x09};            /* [bthome.io] 25.06 C */
    static const uint8_t bat[] = {0xD2, 0xFC, 0x40, 0x01, 0x61};                    /* [bthome.io] 97 % */
    static const uint8_t pres[] = {0xD2, 0xFC, 0x40, 0x04, 0x13, 0x8A, 0x01};       /* [bthome.io] 1008.83 hPa */
    static const uint8_t volt[] = {0xD2, 0xFC, 0x40, 0x0C, 0x02, 0x0C};             /* [bthome.io] 3.074 V */
    static const uint8_t hum8[] = {0xD2, 0xFC, 0x40, 0x2E, 0x23};                   /* [bthome.io] 35 % */
    static const uint8_t temp01[] = {0xD2, 0xFC, 0x40, 0x45, 0x11, 0x01};           /* [bthome.io] 27.3 C (0.1 C steps) */
    static const uint8_t pid[] = {0xD2, 0xFC, 0x40, 0x00, 0x09};                    /* [bthome.io] packet id 9 */

    CHECK_EQ(PARSE(temp, d), GW_BTHOME_OK);
    CHECK(d.has_temperature);
    CHECK_EQ(d.temperature_c100, 2506);

    CHECK_EQ(PARSE(bat, d), GW_BTHOME_OK);
    CHECK(d.has_battery);
    CHECK_EQ(d.battery_pct, 97);

    CHECK_EQ(PARSE(pres, d), GW_BTHOME_OK);
    CHECK(d.has_pressure);
    CHECK_EQ(d.pressure_pa, 100883); /* 0.01 hPa per count == 1 Pa */

    CHECK_EQ(PARSE(volt, d), GW_BTHOME_OK);
    CHECK(d.has_voltage);
    CHECK_EQ(d.voltage_mv, 3074);

    CHECK_EQ(PARSE(hum8, d), GW_BTHOME_OK);
    CHECK(d.has_humidity);
    CHECK_EQ(d.humidity_pct100, 3500);

    CHECK_EQ(PARSE(temp01, d), GW_BTHOME_OK);
    CHECK(d.has_temperature);
    CHECK_EQ(d.temperature_c100, 2730);

    CHECK_EQ(PARSE(pid, d), GW_BTHOME_OK);
    CHECK(d.has_packet_id);
    CHECK_EQ(d.packet_id, 9);
}

static void test_typical_pvvx_packet_with_all_objects(void)
{
    /* packet id, battery, temperature, humidity, voltage - ascending ids as the spec requires */
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x00, 0x09, 0x01, 0x61, 0x02, 0xCA, 0x09,
                                0x03, 0xBF, 0x13, 0x0C, 0x02, 0x0C};
    gw_bthome_data_t d;
    CHECK_EQ(PARSE(p, d), GW_BTHOME_OK);
    CHECK(d.has_packet_id && d.has_battery && d.has_temperature && d.has_humidity && d.has_voltage);
    CHECK_EQ(d.packet_id, 9);
    CHECK_EQ(d.battery_pct, 97);
    CHECK_EQ(d.temperature_c100, 2506);
    CHECK_EQ(d.humidity_pct100, 5055);
    CHECK_EQ(d.voltage_mv, 3074);
    CHECK(!d.stopped_at_unknown);
}

static void test_negative_temperature_and_extremes(void)
{
    gw_bthome_data_t d;
    static const uint8_t neg[] = {0xD2, 0xFC, 0x40, 0x02, 0x0C, 0xFE};   /* 0xFE0C = -500 = -5.00 C */
    static const uint8_t min[] = {0xD2, 0xFC, 0x40, 0x02, 0x00, 0x80};   /* INT16_MIN */
    static const uint8_t max[] = {0xD2, 0xFC, 0x40, 0x02, 0xFF, 0x7F};   /* INT16_MAX */
    static const uint8_t hum_max[] = {0xD2, 0xFC, 0x40, 0x03, 0xFF, 0xFF};
    static const uint8_t p24[] = {0xD2, 0xFC, 0x40, 0x04, 0xFF, 0xFF, 0xFF};
    static const uint8_t hum8_max[] = {0xD2, 0xFC, 0x40, 0x2E, 0xFF};

    CHECK_EQ(PARSE(neg, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, -500);
    CHECK_EQ(PARSE(min, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, INT16_MIN);
    CHECK_EQ(PARSE(max, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, INT16_MAX);
    CHECK_EQ(PARSE(hum_max, d), GW_BTHOME_OK);
    CHECK_EQ(d.humidity_pct100, 65535);          /* raw; gw_units rejects > 10000 */
    CHECK_EQ(PARSE(p24, d), GW_BTHOME_OK);
    CHECK_EQ(d.pressure_pa, 16777215);           /* uint24 max, no sign extension */
    CHECK_EQ(PARSE(hum8_max, d), GW_BTHOME_OK);
    CHECK_EQ(d.humidity_pct100, 25500);          /* 255 % x 100 fits in 16 bit */
}

static void test_temperature_0x45_is_scaled_and_saturates(void)
{
    gw_bthome_data_t d;
    static const uint8_t neg[] = {0xD2, 0xFC, 0x40, 0x45, 0xFB, 0xFF};   /* -5 x 0.1 = -0.5 C = -50 */
    static const uint8_t big[] = {0xD2, 0xFC, 0x40, 0x45, 0xFF, 0x7F};   /* 3276.7 C does not fit 0.01 C int16 */
    static const uint8_t small[] = {0xD2, 0xFC, 0x40, 0x45, 0x00, 0x80};
    CHECK_EQ(PARSE(neg, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, -50);
    CHECK_EQ(PARSE(big, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, INT16_MAX);
    CHECK_EQ(PARSE(small, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, INT16_MIN);
}

static void test_flags_in_device_info(void)
{
    gw_bthome_data_t d;
    static const uint8_t trigger[] = {0xD2, 0xFC, 0x44, 0x01, 0x61};      /* v2, bit 2 = trigger based */
    static const uint8_t enc[] = {0xD2, 0xFC, 0x41, 0x01, 0x61};          /* v2, bit 0 = encrypted */
    static const uint8_t v1[] = {0xD2, 0xFC, 0x20, 0x01, 0x61};           /* version bits 001 */
    static const uint8_t v0[] = {0xD2, 0xFC, 0x00, 0x01, 0x61};
    static const uint8_t v3[] = {0xD2, 0xFC, 0x60, 0x01, 0x61};

    CHECK_EQ(PARSE(trigger, d), GW_BTHOME_OK);
    CHECK(d.trigger_based);
    CHECK(d.has_battery);

    CHECK_EQ(PARSE(enc, d), GW_BTHOME_ERR_ENCRYPTED);
    CHECK(is_zeroed(&d));
    CHECK_EQ(PARSE(v1, d), GW_BTHOME_ERR_VERSION);
    CHECK_EQ(PARSE(v0, d), GW_BTHOME_ERR_VERSION);
    CHECK_EQ(PARSE(v3, d), GW_BTHOME_ERR_VERSION);
}

static void test_header_errors(void)
{
    gw_bthome_data_t d;
    static const uint8_t wrong_uuid[] = {0xD3, 0xFC, 0x40, 0x01, 0x61};
    static const uint8_t swapped_uuid[] = {0xFC, 0xD2, 0x40, 0x01, 0x61};  /* byte order matters */
    static const uint8_t two[] = {0xD2, 0xFC};
    static const uint8_t one[] = {0xD2};
    static const uint8_t ok[] = {0xD2, 0xFC, 0x40};

    CHECK_EQ(PARSE(wrong_uuid, d), GW_BTHOME_ERR_UUID);
    CHECK_EQ(PARSE(swapped_uuid, d), GW_BTHOME_ERR_UUID);
    CHECK_EQ(PARSE(two, d), GW_BTHOME_ERR_TOO_SHORT);
    CHECK_EQ(PARSE(one, d), GW_BTHOME_ERR_TOO_SHORT);
    CHECK_EQ(gw_bthome_parse(ok, 0, &d), GW_BTHOME_ERR_TOO_SHORT);
    CHECK_EQ(gw_bthome_parse(NULL, 5, &d), GW_BTHOME_ERR_ARG);
    CHECK_EQ(gw_bthome_parse(ok, sizeof ok, NULL), GW_BTHOME_ERR_ARG);
    /* header only: valid, no measurements */
    CHECK_EQ(PARSE(ok, d), GW_BTHOME_OK);
    CHECK(is_zeroed(&d));
}

static void test_truncated_object_is_malformed_and_leaves_no_partial_result(void)
{
    gw_bthome_data_t d;
    static const uint8_t cut_value[] = {0xD2, 0xFC, 0x40, 0x01, 0x61, 0x02, 0xC4};  /* temp needs 2 bytes */
    static const uint8_t no_value[] = {0xD2, 0xFC, 0x40, 0x03};
    static const uint8_t cut24[] = {0xD2, 0xFC, 0x40, 0x04, 0x13, 0x8A};

    memset(&d, 0xAA, sizeof d);
    CHECK_EQ(PARSE(cut_value, d), GW_BTHOME_ERR_MALFORMED);
    CHECK(is_zeroed(&d));   /* the battery decoded before the broken object is NOT leaked */
    CHECK_EQ(PARSE(no_value, d), GW_BTHOME_ERR_MALFORMED);
    CHECK_EQ(PARSE(cut24, d), GW_BTHOME_ERR_MALFORMED);
}

static void test_unknown_object_ends_parse_but_keeps_earlier_values(void)
{
    gw_bthome_data_t d;
    /* temperature, then an id this parser does not know, then humidity (must NOT be read) */
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x02, 0xC4, 0x09, 0x77, 0x01, 0x03, 0xBF, 0x13};
    CHECK_EQ(PARSE(p, d), GW_BTHOME_OK);
    CHECK(d.has_temperature);
    CHECK(!d.has_humidity);
    CHECK(d.stopped_at_unknown);
}

static void test_known_but_unused_object_is_skipped_by_its_length(void)
{
    gw_bthome_data_t d;
    /* count uint8 (0x09), co2 uint16 (0x12), then temperature */
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x09, 0x60, 0x12, 0xE2, 0x04, 0x45, 0x11, 0x01};
    CHECK_EQ(PARSE(p, d), GW_BTHOME_OK);
    CHECK(d.has_temperature);
    CHECK_EQ(d.temperature_c100, 2730);
    CHECK(!d.stopped_at_unknown);
}

static void test_duplicate_object_later_wins(void)
{
    gw_bthome_data_t d;
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x02, 0xC4, 0x09, 0x02, 0xCA, 0x09};
    CHECK_EQ(PARSE(p, d), GW_BTHOME_OK);
    CHECK_EQ(d.temperature_c100, 2506);
}

static void test_moisture_binary_sensor(void)
{
    gw_bthome_data_t d;
    static const uint8_t wet[] = {0xD2, 0xFC, 0x40, 0x20, 0x01};
    static const uint8_t dry[] = {0xD2, 0xFC, 0x40, 0x20, 0x00};
    CHECK_EQ(PARSE(wet, d), GW_BTHOME_OK);
    CHECK(d.has_moisture && d.moisture_wet);
    CHECK_EQ(PARSE(dry, d), GW_BTHOME_OK);
    CHECK(d.has_moisture && !d.moisture_wet);
}

static void test_every_prefix_of_a_valid_packet_is_handled(void)
{
    static const uint8_t p[] = {0xD2, 0xFC, 0x40, 0x00, 0x09, 0x01, 0x61, 0x02, 0xCA, 0x09,
                                0x03, 0xBF, 0x13, 0x0C, 0x02, 0x0C};
    for (size_t n = 0; n <= sizeof p; n++) {
        gw_bthome_data_t d;
        gw_bthome_status_t st = gw_bthome_parse(p, n, &d);
        if (n < 3) {
            CHECK_EQ(st, GW_BTHOME_ERR_TOO_SHORT);
        } else {
            CHECK(st == GW_BTHOME_OK || st == GW_BTHOME_ERR_MALFORMED);
        }
        if (st != GW_BTHOME_OK) {
            CHECK(is_zeroed(&d));
        }
    }
}

static void test_random_buffers_never_crash(void)
{
    /* deterministic LCG; the point is ASan/UBSan finding an over-read, not the verdicts */
    uint32_t x = 12345u;
    for (int i = 0; i < 20000; i++) {
        uint8_t buf[40];
        size_t n;
        x = x * 1664525u + 1013904223u;
        n = (x >> 24) % (sizeof buf + 1);
        for (size_t k = 0; k < n; k++) {
            x = x * 1664525u + 1013904223u;
            buf[k] = (uint8_t)(x >> 24);
        }
        if (n >= 3 && (i & 1)) { /* half of the inputs get a valid header so objects are reached */
            buf[0] = 0xD2; buf[1] = 0xFC; buf[2] = 0x40;
        }
        {
            gw_bthome_data_t d;
            gw_bthome_status_t st = gw_bthome_parse(buf, n, &d);
            CHECK(gw_bthome_status_str(st) != NULL);
        }
    }
}

static void test_status_strings_exist(void)
{
    CHECK(strcmp(gw_bthome_status_str(GW_BTHOME_OK), "ok") == 0);
    CHECK(strlen(gw_bthome_status_str(GW_BTHOME_ERR_ENCRYPTED)) > 0);
    CHECK(strlen(gw_bthome_status_str((gw_bthome_status_t)99)) > 0);
}

int main(void)
{
    RUN(test_official_example_temperature_and_humidity);
    RUN(test_single_object_examples);
    RUN(test_typical_pvvx_packet_with_all_objects);
    RUN(test_negative_temperature_and_extremes);
    RUN(test_temperature_0x45_is_scaled_and_saturates);
    RUN(test_flags_in_device_info);
    RUN(test_header_errors);
    RUN(test_truncated_object_is_malformed_and_leaves_no_partial_result);
    RUN(test_unknown_object_ends_parse_but_keeps_earlier_values);
    RUN(test_known_but_unused_object_is_skipped_by_its_length);
    RUN(test_duplicate_object_later_wins);
    RUN(test_moisture_binary_sensor);
    RUN(test_every_prefix_of_a_valid_packet_is_handled);
    RUN(test_random_buffers_never_crash);
    RUN(test_status_strings_exist);
    return MT_SUMMARY();
}
