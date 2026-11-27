#include "gw_units.h"

#include <stddef.h>

bool gw_to_matter_temperature(int32_t c100, int16_t *out)
{
    if (out == NULL || c100 < GW_MATTER_TEMP_MIN_C100 || c100 > GW_MATTER_TEMP_MAX_C100) {
        return false;
    }
    *out = (int16_t)c100;
    return true;
}

bool gw_to_matter_humidity(uint32_t pct100, uint16_t *out)
{
    if (out == NULL || pct100 > GW_MATTER_HUMIDITY_MAX_PCT100) {
        return false;
    }
    *out = (uint16_t)pct100;
    return true;
}

bool gw_to_matter_pressure(uint32_t pascal, int16_t *out)
{
    /* 64-bit: pascal + 50 would wrap for values near UINT32_MAX */
    const uint64_t counts = ((uint64_t)pascal + 50u) / 100u;
    if (out == NULL || counts > (uint64_t)GW_MATTER_PRESSURE_MAX) {
        return false;
    }
    *out = (int16_t)counts;
    return true;
}

bool gw_to_matter_battery(uint8_t percent, uint8_t *out)
{
    if (out == NULL || percent > 100u) {
        return false;
    }
    *out = (uint8_t)(percent * 2u);
    return true;
}

gw_air_quality_t gw_iaq_to_air_quality(uint16_t iaq, uint8_t accuracy)
{
    if (accuracy == 0u || iaq > GW_IAQ_MAX) {
        return GW_AIR_QUALITY_UNKNOWN;
    }
    if (iaq <= 50u)  return GW_AIR_QUALITY_GOOD;
    if (iaq <= 100u) return GW_AIR_QUALITY_FAIR;
    if (iaq <= 150u) return GW_AIR_QUALITY_MODERATE;
    if (iaq <= 200u) return GW_AIR_QUALITY_POOR;
    if (iaq <= 300u) return GW_AIR_QUALITY_VERY_POOR;
    return GW_AIR_QUALITY_EXTREMELY_POOR;
}
