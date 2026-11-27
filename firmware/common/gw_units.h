/**
 * gw_units.h - conversions from sensor units to Matter attribute units (pure C99).
 *
 * Every function validates the input against the range of the target attribute and returns
 * false (leaving *out untouched) when the value cannot be represented. The caller then keeps
 * the previous attribute value or reports "null" - it never publishes garbage.
 *
 * Units (checked 2026-11-27 against the cluster definitions shipped with esp-matter
 * release/v1.6.1, connectedhomeip/src/app/zap-templates/zcl/data-model/chip/ (<cluster>-cluster.xml)):
 *   TemperatureMeasurement.MeasuredValue   int16, 0.01 degC, min -27315, max 0x7FFE
 *   RelativeHumidityMeasurement.MeasuredValue uint16, 0.01 %, max 10000
 *   PowerSource.BatPercentRemaining        uint8, 0.5 % steps, max 200 (0xC8)
 *   PressureMeasurement.MeasuredValue      int16, range -32767..32766. The XML does not state the
 *       unit; the Matter/ZCL text defines it as 10 x kPa (0.1 kPa = 1 hPa = 100 Pa per count).
 *       NOT re-verified against the Matter specification PDF.
 *   AirQuality.AirQuality                  enum8, 0 Unknown, 1 Good, 2 Fair, 3 Moderate, 4 Poor,
 *       5 VeryPoor, 6 ExtremelyPoor
 *
 * The IAQ -> AirQuality class boundaries are a PROPOSAL (not from a standard): Bosch's own
 * IAQ classes (0-50 excellent, 51-100 good, 101-150 lightly, 151-200 moderately, 201-250
 * heavily, 251-350 severely polluted, > 350 extremely) have 7 steps, Matter has 6, so the top
 * two Bosch classes are merged. The "ventilate" threshold (IAQ 150, gw_ventilation.h) sits on
 * the Moderate/Poor boundary on purpose.
 */
#ifndef GW_UNITS_H
#define GW_UNITS_H

#include <stdbool.h>
#include <stdint.h>

#define GW_MATTER_TEMP_MIN_C100 (-27315)
#define GW_MATTER_TEMP_MAX_C100 0x7FFE
#define GW_MATTER_HUMIDITY_MAX_PCT100 10000u
#define GW_MATTER_BATTERY_MAX_HALF_PCT 200u
#define GW_MATTER_PRESSURE_MAX 32766

#define GW_IAQ_MAX 500u

typedef enum {
    GW_AIR_QUALITY_UNKNOWN = 0,
    GW_AIR_QUALITY_GOOD = 1,
    GW_AIR_QUALITY_FAIR = 2,
    GW_AIR_QUALITY_MODERATE = 3,
    GW_AIR_QUALITY_POOR = 4,
    GW_AIR_QUALITY_VERY_POOR = 5,
    GW_AIR_QUALITY_EXTREMELY_POOR = 6
} gw_air_quality_t;

/** 0.01 degC -> Matter temperature (identical scale; only the range is checked). */
bool gw_to_matter_temperature(int32_t c100, int16_t *out);

/** 0.01 % -> Matter relative humidity (identical scale; only the range is checked). */
bool gw_to_matter_humidity(uint32_t pct100, uint16_t *out);

/** Pascal -> Matter pressure (100 Pa per count, rounded to nearest, ties up). */
bool gw_to_matter_pressure(uint32_t pascal, int16_t *out);

/** Battery percent 0..100 -> Matter half-percent 0..200. */
bool gw_to_matter_battery(uint8_t percent, uint8_t *out);

/** BSEC IAQ index (0..500) and accuracy (0..3) -> AirQuality enum. Accuracy 0 -> Unknown. */
gw_air_quality_t gw_iaq_to_air_quality(uint16_t iaq, uint8_t accuracy);

#endif /* GW_UNITS_H */
