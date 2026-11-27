/* Unit tests for gw_sensor_table.c: allow-list, packet-id dedup, merge of partial packets, staleness. */
#include <stdint.h>
#include <string.h>

#include "gw_sensor_table.h"
#include "minitest.h"

static const uint8_t MAC_A[6] = {0xA4, 0xC1, 0x38, 0x00, 0x00, 0x01};
static const uint8_t MAC_B[6] = {0xA4, 0xC1, 0x38, 0x00, 0x00, 0x02};
static const uint8_t MAC_X[6] = {0xA4, 0xC1, 0x38, 0x00, 0x00, 0x99};

static gw_bthome_data_t pkt_th(uint8_t pid, int16_t t, uint16_t h)
{
    gw_bthome_data_t d;
    memset(&d, 0, sizeof d);
    d.has_packet_id = true;  d.packet_id = pid;
    d.has_temperature = true; d.temperature_c100 = t;
    d.has_humidity = true;    d.humidity_pct100 = h;
    return d;
}

static void test_add_find_count(void)
{
    gw_sensor_table_t t;
    gw_sensor_table_init(&t, 1000);
    CHECK_EQ(gw_sensor_count(&t), 0);
    CHECK_EQ(gw_sensor_find(&t, MAC_A), -1);
    CHECK_EQ(gw_sensor_add(&t, MAC_A), 0);
    CHECK_EQ(gw_sensor_add(&t, MAC_B), 1);
    CHECK_EQ(gw_sensor_add(&t, MAC_A), 0);          /* idempotent: same slot, no second entry */
    CHECK_EQ(gw_sensor_count(&t), 2);
    CHECK_EQ(gw_sensor_find(&t, MAC_B), 1);
    CHECK_EQ(gw_sensor_find(&t, MAC_X), -1);
}

static void test_table_full_and_bad_arguments(void)
{
    gw_sensor_table_t t;
    uint8_t mac[6] = {1, 2, 3, 4, 5, 0};
    gw_sensor_table_init(&t, 1000);
    for (int i = 0; i < GW_SENSOR_MAX; i++) {
        mac[5] = (uint8_t)i;
        CHECK_EQ(gw_sensor_add(&t, mac), i);
    }
    mac[5] = 200;
    CHECK_EQ(gw_sensor_add(&t, mac), -1);           /* full */
    CHECK_EQ(gw_sensor_count(&t), GW_SENSOR_MAX);
    mac[5] = 3;
    CHECK_EQ(gw_sensor_add(&t, mac), 3);            /* a known one is still found when full */

    CHECK_EQ(gw_sensor_add(NULL, MAC_A), -1);
    CHECK_EQ(gw_sensor_add(&t, NULL), -1);
    CHECK_EQ(gw_sensor_find(NULL, MAC_A), -1);
    CHECK_EQ(gw_sensor_find(&t, NULL), -1);
    CHECK_EQ(gw_sensor_count(NULL), 0);
    gw_sensor_table_init(NULL, 1);
}

static void test_mac_must_match_all_six_bytes(void)
{
    gw_sensor_table_t t;
    uint8_t mac[6];
    gw_sensor_table_init(&t, 1000);
    gw_sensor_add(&t, MAC_A);
    for (int i = 0; i < 6; i++) {
        memcpy(mac, MAC_A, 6);
        mac[i] ^= 0x01;
        CHECK_EQ(gw_sensor_find(&t, mac), -1);
    }
}

static void test_unknown_device_is_dropped(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(1, 2500, 5000);
    int slot = -7;
    gw_sensor_table_init(&t, 1000);
    gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_X, &d, 0, &slot), GW_SENSOR_UNKNOWN_DEVICE);
    CHECK_EQ(slot, -7);
    CHECK(!t.slots[0].seen);
    CHECK_EQ(gw_sensor_update(&t, NULL, &d, 0, &slot), GW_SENSOR_UNKNOWN_DEVICE);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, NULL, 0, &slot), GW_SENSOR_UNKNOWN_DEVICE);
    CHECK_EQ(gw_sensor_update(NULL, MAC_A, &d, 0, &slot), GW_SENSOR_UNKNOWN_DEVICE);
}

static void test_update_stores_values_and_reports_slot(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(1, 2500, 5055);
    int slot = -1;
    gw_sensor_table_init(&t, 1000);
    gw_sensor_add(&t, MAC_A);
    gw_sensor_add(&t, MAC_B);
    CHECK_EQ(gw_sensor_update(&t, MAC_B, &d, 500, &slot), GW_SENSOR_UPDATED);
    CHECK_EQ(slot, 1);
    CHECK(t.slots[1].last.has_temperature);
    CHECK_EQ(t.slots[1].last.temperature_c100, 2500);
    CHECK_EQ(t.slots[1].last.humidity_pct100, 5055);
    CHECK_EQ(t.slots[1].last_seen_ms, 500);
    CHECK(!t.slots[0].seen);                          /* the other sensor is untouched */
    CHECK_EQ(gw_sensor_update(&t, MAC_B, &d, 600, NULL), GW_SENSOR_DUPLICATE); /* NULL slot_out is allowed */
}

static void test_partial_packets_are_merged(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t first = pkt_th(1, 2500, 5000);
    gw_bthome_data_t second;
    gw_sensor_table_init(&t, 100000);
    gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &first, 0, NULL), GW_SENSOR_UPDATED);

    memset(&second, 0, sizeof second);                /* battery-only packet */
    second.has_packet_id = true; second.packet_id = 2;
    second.has_battery = true;   second.battery_pct = 80;
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &second, 10, NULL), GW_SENSOR_UPDATED);

    CHECK(t.slots[0].last.has_temperature);           /* kept from the first packet */
    CHECK_EQ(t.slots[0].last.temperature_c100, 2500);
    CHECK(t.slots[0].last.has_humidity);
    CHECK(t.slots[0].last.has_battery);
    CHECK_EQ(t.slots[0].last.battery_pct, 80);

    second.has_battery = false;                       /* newer value of a quantity replaces the old one */
    second.packet_id = 3;
    second.has_temperature = true; second.temperature_c100 = 2600;
    second.has_moisture = true; second.moisture_wet = true;
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &second, 20, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(t.slots[0].last.temperature_c100, 2600);
    CHECK_EQ(t.slots[0].last.battery_pct, 80);
    CHECK(t.slots[0].last.has_moisture && t.slots[0].last.moisture_wet);
}

static void test_repeated_packet_id_is_a_duplicate(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(7, 2500, 5000);
    gw_bthome_data_t changed = pkt_th(7, 9999, 5000);   /* same id, different data: still the repeat */
    gw_sensor_table_init(&t, 100000);
    gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 0, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 10, NULL), GW_SENSOR_DUPLICATE);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &changed, 20, NULL), GW_SENSOR_DUPLICATE);
    CHECK_EQ(t.slots[0].last.temperature_c100, 2500);   /* duplicates never overwrite */
    d.packet_id = 8;
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 30, NULL), GW_SENSOR_UPDATED);
    d.packet_id = 7;                                     /* going back to an older id is a new packet */
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 40, NULL), GW_SENSOR_UPDATED);
}

static void test_packet_ids_are_per_sensor(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(5, 2500, 5000);
    gw_sensor_table_init(&t, 100000);
    gw_sensor_add(&t, MAC_A);
    gw_sensor_add(&t, MAC_B);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 0, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_B, &d, 1, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 2, NULL), GW_SENSOR_DUPLICATE);
}

static void test_packets_without_id_are_never_duplicates(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(0, 2500, 5000);
    d.has_packet_id = false;
    gw_sensor_table_init(&t, 100000);
    gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 0, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 1, NULL), GW_SENSOR_UPDATED);
}

static void test_repeated_id_is_accepted_after_the_sensor_was_silent(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(0, 2500, 5000);       /* a rebooted sensor restarts at packet id 0 */
    gw_sensor_table_init(&t, 1000);
    gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 0, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 999, NULL), GW_SENSOR_DUPLICATE);
    d.temperature_c100 = 1800;
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 999 + 1000, NULL), GW_SENSOR_UPDATED);  /* silent >= stale: accept */
    CHECK_EQ(t.slots[0].last.temperature_c100, 1800);
}

static void test_duplicates_keep_the_sensor_alive(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(3, 2500, 5000);
    int slot;
    gw_sensor_table_init(&t, 1000);
    slot = gw_sensor_add(&t, MAC_A);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 0, NULL), GW_SENSOR_UPDATED);
    CHECK_EQ(gw_sensor_update(&t, MAC_A, &d, 900, NULL), GW_SENSOR_DUPLICATE);
    CHECK(!gw_sensor_is_stale(&t, slot, 1800));       /* 900 ms after the repeat, not 1800 after the data */
    CHECK(gw_sensor_is_stale(&t, slot, 1900));
}

static void test_staleness_boundaries(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(1, 2500, 5000);
    int slot;
    gw_sensor_table_init(&t, 1000);
    slot = gw_sensor_add(&t, MAC_A);
    CHECK(gw_sensor_is_stale(&t, slot, 0));           /* registered but never heard */
    gw_sensor_update(&t, MAC_A, &d, 5000, NULL);
    CHECK(!gw_sensor_is_stale(&t, slot, 5000));
    CHECK(!gw_sensor_is_stale(&t, slot, 5999));
    CHECK(gw_sensor_is_stale(&t, slot, 6000));        /* exactly the timeout */
    CHECK(gw_sensor_is_stale(&t, slot, 60000));
}

static void test_staleness_survives_counter_wrap(void)
{
    gw_sensor_table_t t;
    gw_bthome_data_t d = pkt_th(1, 2500, 5000);
    int slot;
    gw_sensor_table_init(&t, 1000);
    slot = gw_sensor_add(&t, MAC_A);
    gw_sensor_update(&t, MAC_A, &d, UINT32_MAX - 499, NULL);
    CHECK(!gw_sensor_is_stale(&t, slot, 498));        /* 999 ms later across the wrap */
    CHECK(gw_sensor_is_stale(&t, slot, 500));         /* 1000 ms later */
}

static void test_staleness_of_invalid_slots(void)
{
    gw_sensor_table_t t;
    gw_sensor_table_init(&t, 1000);
    CHECK(gw_sensor_is_stale(&t, 0, 0));              /* unused slot */
    CHECK(gw_sensor_is_stale(&t, -1, 0));
    CHECK(gw_sensor_is_stale(&t, GW_SENSOR_MAX, 0));
    CHECK(gw_sensor_is_stale(NULL, 0, 0));
}

int main(void)
{
    RUN(test_add_find_count);
    RUN(test_table_full_and_bad_arguments);
    RUN(test_mac_must_match_all_six_bytes);
    RUN(test_unknown_device_is_dropped);
    RUN(test_update_stores_values_and_reports_slot);
    RUN(test_partial_packets_are_merged);
    RUN(test_repeated_packet_id_is_a_duplicate);
    RUN(test_packet_ids_are_per_sensor);
    RUN(test_packets_without_id_are_never_duplicates);
    RUN(test_repeated_id_is_accepted_after_the_sensor_was_silent);
    RUN(test_duplicates_keep_the_sensor_alive);
    RUN(test_staleness_boundaries);
    RUN(test_staleness_survives_counter_wrap);
    RUN(test_staleness_of_invalid_slots);
    return MT_SUMMARY();
}
