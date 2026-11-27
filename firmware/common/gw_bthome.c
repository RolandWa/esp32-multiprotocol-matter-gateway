#include "gw_bthome.h"

#include <string.h>

/* Data length (bytes after the object id) of the fixed-size BTHome v2 objects that were read
 * from https://bthome.io/format/ (2026-11-27). Anything not listed ends the parse. */
typedef struct {
    uint8_t id;
    uint8_t len;
} obj_len_t;

static const obj_len_t k_lengths[] = {
    {0x00, 1}, {0x01, 1}, {0x02, 2}, {0x03, 2}, {0x04, 3}, {0x05, 3}, {0x06, 2}, {0x08, 2},
    {0x09, 1}, {0x0A, 3}, {0x0B, 3}, {0x0C, 2}, {0x0D, 2}, {0x0E, 2}, {0x12, 2}, {0x13, 2},
    {0x14, 2}, {0x20, 1}, {0x2E, 1}, {0x3D, 2}, {0x3E, 4}, {0x40, 2}, {0x42, 3}, {0x43, 2},
    {0x45, 2}, {0x46, 1}, {0x48, 2}, {0x49, 2}, {0x4A, 2}, {0x4B, 3}, {0x4E, 4}, {0x4F, 4},
    {0x51, 2}, {0x52, 2}, {0x56, 2}, {0x57, 1}, {0x58, 1}, {0x59, 1}, {0x5A, 2}, {0x5B, 4},
    {0x5F, 2}, {0x60, 1}, {0x62, 4}, {0x63, 4}, {0x64, 1}, {0x65, 1}, {0x67, 1},
};

static int object_len(uint8_t id)
{
    for (size_t i = 0; i < sizeof k_lengths / sizeof k_lengths[0]; i++) {
        if (k_lengths[i].id == id) {
            return k_lengths[i].len;
        }
    }
    return -1;
}

static uint16_t rd_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

static uint32_t rd_u24(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16);
}

gw_bthome_status_t gw_bthome_parse(const uint8_t *data, size_t len, gw_bthome_data_t *out)
{
    if (data == NULL || out == NULL) {
        return GW_BTHOME_ERR_ARG;
    }
    memset(out, 0, sizeof *out);
    if (len < 3) {
        return GW_BTHOME_ERR_TOO_SHORT;
    }
    if (rd_u16(data) != GW_BTHOME_UUID16) {
        return GW_BTHOME_ERR_UUID;
    }

    const uint8_t info = data[2];
    if ((info >> 5) != 2) {
        return GW_BTHOME_ERR_VERSION;
    }
    if (info & 0x01) {
        return GW_BTHOME_ERR_ENCRYPTED;
    }

    gw_bthome_data_t r;
    memset(&r, 0, sizeof r);
    r.trigger_based = (info & 0x04) != 0;

    size_t pos = 3;
    while (pos < len) {
        const uint8_t id = data[pos];
        const int n = object_len(id);
        if (n < 0) {
            r.stopped_at_unknown = true;
            break;
        }
        if (len - pos - 1 < (size_t)n) {
            return GW_BTHOME_ERR_MALFORMED;
        }
        const uint8_t *v = &data[pos + 1];
        switch (id) {
        case 0x00:
            r.has_packet_id = true;
            r.packet_id = v[0];
            break;
        case 0x01:
            r.has_battery = true;
            r.battery_pct = v[0];
            break;
        case 0x02:
            r.has_temperature = true;
            r.temperature_c100 = (int16_t)rd_u16(v);
            break;
        case 0x45: { /* 0.1 degC, signed 16 bit -> 0.01 degC; saturate instead of wrapping */
            int32_t t = (int32_t)(int16_t)rd_u16(v) * 10;
            r.has_temperature = true;
            r.temperature_c100 = (int16_t)(t > INT16_MAX ? INT16_MAX : (t < INT16_MIN ? INT16_MIN : t));
            break;
        }
        case 0x03:
            r.has_humidity = true;
            r.humidity_pct100 = rd_u16(v);
            break;
        case 0x2E: /* 1 %, unsigned 8 bit -> 0.01 % */
            r.has_humidity = true;
            r.humidity_pct100 = (uint16_t)(v[0] * 100u);
            break;
        case 0x04:
            r.has_pressure = true;
            r.pressure_pa = rd_u24(v);
            break;
        case 0x0C:
            r.has_voltage = true;
            r.voltage_mv = rd_u16(v);
            break;
        case 0x20:
            r.has_moisture = true;
            r.moisture_wet = v[0] != 0;
            break;
        default:
            break; /* known length, value not needed by the gateway */
        }
        pos += 1 + (size_t)n;
    }

    *out = r;
    return GW_BTHOME_OK;
}

const char *gw_bthome_status_str(gw_bthome_status_t status)
{
    switch (status) {
    case GW_BTHOME_OK:            return "ok";
    case GW_BTHOME_ERR_ARG:       return "null argument";
    case GW_BTHOME_ERR_TOO_SHORT: return "too short";
    case GW_BTHOME_ERR_UUID:      return "not a BTHome UUID";
    case GW_BTHOME_ERR_VERSION:   return "not BTHome v2";
    case GW_BTHOME_ERR_ENCRYPTED: return "encrypted (not supported)";
    case GW_BTHOME_ERR_MALFORMED: return "malformed object";
    }
    return "unknown status";
}
