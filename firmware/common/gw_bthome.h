/**
 * gw_bthome.h - BTHome v2 service-data parser (pure C99, no ESP-IDF).
 *
 * Input is the payload of the BLE AD element "Service Data - 16-bit UUID" (AD type 0x16)
 * WITHOUT the AD length/type bytes, i.e. it starts with the UUID in over-the-air byte order:
 *
 *     D2 FC | 40 | 02 C4 09 | 03 BF 13          (bthome.io example: 25.00 C, 50.55 %)
 *     UUID    info  temp       humidity
 *
 * This is what NimBLE's ble_hs_adv_fields.svc_data_uuid16 points at (UUID bytes included).
 *
 * Scope (decision of the owner, docs/OPEN_QUESTIONS.md 3a): sensors run pvvx/ATC_MiThermometer
 * with BTHome v2. ENCRYPTED packets (device-info bit 0) are rejected with
 * GW_BTHOME_ERR_ENCRYPTED - AES-CCM decryption is not implemented until the owner decides
 * whether to use a bindkey.
 *
 * Objects are decoded per https://bthome.io/format/ . Only objects whose length is known are
 * stepped over; the first object id this parser does not know ends the parse (the spec
 * requires senders to emit ids in ascending order for exactly that reason) and sets
 * `stopped_at_unknown`. Measurements decoded before that point are valid.
 *
 * Values are kept in the units of the wire format, NOT converted (see gw_units.h):
 *   temperature  0.01 degC  (object 0x02, or 0x45 which is 0.1 degC and is scaled x10)
 *   humidity     0.01 %     (object 0x03, or 0x2E which is 1 % and is scaled x100)
 *   pressure     Pa         (object 0x04 is uint24 x 0.01 hPa == 1 Pa per count)
 *   battery      %          (object 0x01)
 *   voltage      mV         (object 0x0C, uint16 x 0.001 V == 1 mV per count)
 * If an object occurs twice, the later one wins.
 */
#ifndef GW_BTHOME_H
#define GW_BTHOME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define GW_BTHOME_UUID16 0xFCD2u

typedef enum {
    GW_BTHOME_OK = 0,
    GW_BTHOME_ERR_ARG,        /* NULL pointer */
    GW_BTHOME_ERR_TOO_SHORT,  /* fewer than 3 bytes (UUID + device info) */
    GW_BTHOME_ERR_UUID,       /* not the BTHome UUID 0xFCD2 */
    GW_BTHOME_ERR_VERSION,    /* BTHome version in device info is not 2 */
    GW_BTHOME_ERR_ENCRYPTED,  /* encryption flag set; decryption not implemented */
    GW_BTHOME_ERR_MALFORMED   /* an object runs past the end of the data */
} gw_bthome_status_t;

typedef struct {
    bool trigger_based;       /* device-info bit 2: irregular sender (button), do not mark "unavailable" */

    bool has_packet_id;       /* object 0x00 */
    uint8_t packet_id;

    bool has_temperature;     /* 0x02 / 0x45 */
    int16_t temperature_c100; /* 0.01 degC */

    bool has_humidity;        /* 0x03 / 0x2E */
    uint16_t humidity_pct100; /* 0.01 % (may exceed 10000 if the sender is faulty; gw_units validates) */

    bool has_pressure;        /* 0x04 */
    uint32_t pressure_pa;

    bool has_battery;         /* 0x01 */
    uint8_t battery_pct;      /* may exceed 100 if the sender is faulty; gw_units validates */

    bool has_voltage;         /* 0x0C */
    uint16_t voltage_mv;

    bool has_moisture;        /* binary sensor 0x20 (water leak sensors) */
    bool moisture_wet;

    bool stopped_at_unknown;  /* parse ended at an object id this parser does not know */
} gw_bthome_data_t;

/**
 * Parse BTHome v2 service data. `out` is zeroed first; on any error it is left zeroed
 * (no half-filled result). Returns GW_BTHOME_OK on success, also when no object was decoded.
 */
gw_bthome_status_t gw_bthome_parse(const uint8_t *data, size_t len, gw_bthome_data_t *out);

/** Human-readable status for logs. Never returns NULL. */
const char *gw_bthome_status_str(gw_bthome_status_t status);

#endif /* GW_BTHOME_H */
