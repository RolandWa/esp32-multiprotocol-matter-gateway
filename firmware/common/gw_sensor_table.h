/**
 * gw_sensor_table.h - registry of BLE (BTHome) sensors known to the gateway (pure C99).
 *
 * Only sensors that were registered (add) are accepted; advertisements from any other device
 * are reported as UNKNOWN_DEVICE and dropped - a neighbour's sensor must never become a Matter
 * endpoint. (Policy "allow-list by MAC" is a proposal; auto-pairing would be a new decision.)
 *
 * Per sensor the table keeps the last value of every quantity (a packet may carry only a
 * subset), the last BTHome packet id (BTHome receivers must drop a repeated id, because senders
 * repeat the same advertisement to improve delivery) and the time of the last accepted packet
 * (for "unavailable" detection). A repeated packet id is accepted again when the sensor had been
 * silent for longer than the stale timeout - a rebooted sensor restarts its counter.
 *
 * `mac` is an opaque 6-byte device address as delivered by the BLE stack (NimBLE: ble_addr_t.val).
 * Time is the free-running uint32 millisecond counter used everywhere (differences mod 2^32).
 */
#ifndef GW_SENSOR_TABLE_H
#define GW_SENSOR_TABLE_H

#include <stdbool.h>
#include <stdint.h>

#include "gw_bthome.h"

#define GW_SENSOR_MAX 16
#define GW_SENSOR_DEFAULT_STALE_MS (15u * 60u * 1000u)  /* PROPOSAL: pvvx default adv. interval is minutes-scale */

typedef struct {
    bool used;
    uint8_t mac[6];
    bool seen;                  /* at least one packet accepted */
    uint32_t last_seen_ms;
    bool has_packet_id;
    uint8_t last_packet_id;
    gw_bthome_data_t last;      /* merged: each has_* flag stays set once a value was received */
} gw_sensor_slot_t;

typedef struct {
    gw_sensor_slot_t slots[GW_SENSOR_MAX];
    uint32_t stale_after_ms;
} gw_sensor_table_t;

typedef enum {
    GW_SENSOR_UNKNOWN_DEVICE = 0,
    GW_SENSOR_DUPLICATE,        /* same packet id as the previous accepted packet */
    GW_SENSOR_UPDATED
} gw_sensor_result_t;

void gw_sensor_table_init(gw_sensor_table_t *t, uint32_t stale_after_ms);

/** Register a sensor. Returns its slot index; the existing index when already registered; -1 when full or on bad args. */
int gw_sensor_add(gw_sensor_table_t *t, const uint8_t mac[6]);

/** Slot index of a registered sensor, or -1. */
int gw_sensor_find(const gw_sensor_table_t *t, const uint8_t mac[6]);

/** Number of registered sensors. */
int gw_sensor_count(const gw_sensor_table_t *t);

/** Feed one parsed packet. On UPDATED, `*slot_out` (if not NULL) receives the slot index. */
gw_sensor_result_t gw_sensor_update(gw_sensor_table_t *t, const uint8_t mac[6], const gw_bthome_data_t *data,
                                    uint32_t now_ms, int *slot_out);

/** True when the slot is unused, never received a packet, or has been silent for >= stale_after_ms. */
bool gw_sensor_is_stale(const gw_sensor_table_t *t, int slot, uint32_t now_ms);

#endif /* GW_SENSOR_TABLE_H */
