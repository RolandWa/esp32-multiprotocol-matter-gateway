#include "gw_sensor_table.h"

#include <string.h>

void gw_sensor_table_init(gw_sensor_table_t *t, uint32_t stale_after_ms)
{
    if (t == NULL) {
        return;
    }
    memset(t, 0, sizeof *t);
    t->stale_after_ms = stale_after_ms;
}

int gw_sensor_find(const gw_sensor_table_t *t, const uint8_t mac[6])
{
    if (t == NULL || mac == NULL) {
        return -1;
    }
    for (int i = 0; i < GW_SENSOR_MAX; i++) {
        if (t->slots[i].used && memcmp(t->slots[i].mac, mac, 6) == 0) {
            return i;
        }
    }
    return -1;
}

int gw_sensor_add(gw_sensor_table_t *t, const uint8_t mac[6])
{
    if (t == NULL || mac == NULL) {
        return -1;
    }
    const int existing = gw_sensor_find(t, mac);
    if (existing >= 0) {
        return existing;
    }
    for (int i = 0; i < GW_SENSOR_MAX; i++) {
        if (!t->slots[i].used) {
            memset(&t->slots[i], 0, sizeof t->slots[i]);
            t->slots[i].used = true;
            memcpy(t->slots[i].mac, mac, 6);
            return i;
        }
    }
    return -1;
}

int gw_sensor_count(const gw_sensor_table_t *t)
{
    int n = 0;
    if (t != NULL) {
        for (int i = 0; i < GW_SENSOR_MAX; i++) {
            n += t->slots[i].used ? 1 : 0;
        }
    }
    return n;
}

bool gw_sensor_is_stale(const gw_sensor_table_t *t, int slot, uint32_t now_ms)
{
    if (t == NULL || slot < 0 || slot >= GW_SENSOR_MAX || !t->slots[slot].used || !t->slots[slot].seen) {
        return true;
    }
    return (uint32_t)(now_ms - t->slots[slot].last_seen_ms) >= t->stale_after_ms;
}

gw_sensor_result_t gw_sensor_update(gw_sensor_table_t *t, const uint8_t mac[6], const gw_bthome_data_t *data,
                                    uint32_t now_ms, int *slot_out)
{
    const int idx = gw_sensor_find(t, mac);
    if (idx < 0 || data == NULL) {
        return GW_SENSOR_UNKNOWN_DEVICE;
    }
    gw_sensor_slot_t *s = &t->slots[idx];

    if (data->has_packet_id && s->has_packet_id && data->packet_id == s->last_packet_id &&
        !gw_sensor_is_stale(t, idx, now_ms)) {
        s->last_seen_ms = now_ms; /* data is dropped, but a repeating sensor is alive */
        return GW_SENSOR_DUPLICATE;
    }

    gw_bthome_data_t *m = &s->last;
    if (data->has_temperature) { m->has_temperature = true; m->temperature_c100 = data->temperature_c100; }
    if (data->has_humidity)    { m->has_humidity = true;    m->humidity_pct100 = data->humidity_pct100; }
    if (data->has_pressure)    { m->has_pressure = true;    m->pressure_pa = data->pressure_pa; }
    if (data->has_battery)     { m->has_battery = true;     m->battery_pct = data->battery_pct; }
    if (data->has_voltage)     { m->has_voltage = true;     m->voltage_mv = data->voltage_mv; }
    if (data->has_moisture)    { m->has_moisture = true;    m->moisture_wet = data->moisture_wet; }
    m->trigger_based = data->trigger_based;

    if (data->has_packet_id) {
        s->has_packet_id = true;
        s->last_packet_id = data->packet_id;
    }
    s->seen = true;
    s->last_seen_ms = now_ms;
    if (slot_out != NULL) {
        *slot_out = idx;
    }
    return GW_SENSOR_UPDATED;
}
