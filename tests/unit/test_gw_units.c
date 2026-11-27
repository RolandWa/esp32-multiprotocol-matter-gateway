/* Unit tests for gw_units.c. Range limits come from the Matter cluster definitions (see gw_units.h). */
#include <stdint.h>

#include "gw_units.h"
#include "minitest.h"

static void test_temperature_range_edges(void)
{
    int16_t v = 1234;
    CHECK(gw_to_matter_temperature(2500, &v));
    CHECK_EQ(v, 2500);
    CHECK(gw_to_matter_temperature(-27315, &v));    /* absolute zero is the lowest legal value */
    CHECK_EQ(v, -27315);
    CHECK(gw_to_matter_temperature(0x7FFE, &v));
    CHECK_EQ(v, 0x7FFE);

    v = 1234;
    CHECK(!gw_to_matter_temperature(-27316, &v));
    CHECK(!gw_to_matter_temperature(0x7FFF, &v));   /* 0x7FFF is the "invalid" marker of the cluster */
    CHECK(!gw_to_matter_temperature(INT32_MIN, &v));
    CHECK(!gw_to_matter_temperature(INT32_MAX, &v));
    CHECK_EQ(v, 1234);                              /* untouched on failure */
    CHECK(!gw_to_matter_temperature(2500, NULL));
}

static void test_humidity_range_edges(void)
{
    uint16_t v = 4321;
    CHECK(gw_to_matter_humidity(0, &v));
    CHECK_EQ(v, 0);
    CHECK(gw_to_matter_humidity(5055, &v));
    CHECK_EQ(v, 5055);
    CHECK(gw_to_matter_humidity(10000, &v));
    CHECK_EQ(v, 10000);

    v = 4321;
    CHECK(!gw_to_matter_humidity(10001, &v));
    CHECK(!gw_to_matter_humidity(UINT32_MAX, &v));
    CHECK_EQ(v, 4321);
    CHECK(!gw_to_matter_humidity(100, NULL));
}

static void test_pressure_rounds_to_hectopascal_counts(void)
{
    int16_t v = -1;
    CHECK(gw_to_matter_pressure(100883, &v));   /* 1008.83 hPa -> 1009 */
    CHECK_EQ(v, 1009);
    CHECK(gw_to_matter_pressure(100849, &v));   /* 1008.49 hPa -> 1008 */
    CHECK_EQ(v, 1008);
    CHECK(gw_to_matter_pressure(100850, &v));   /* tie rounds up */
    CHECK_EQ(v, 1009);
    CHECK(gw_to_matter_pressure(0, &v));
    CHECK_EQ(v, 0);
    CHECK(gw_to_matter_pressure(49, &v));
    CHECK_EQ(v, 0);
    CHECK(gw_to_matter_pressure(50, &v));
    CHECK_EQ(v, 1);
}

static void test_pressure_upper_limit_and_overflow(void)
{
    int16_t v = -1;
    CHECK(gw_to_matter_pressure(3276649, &v));  /* rounds to 32766 = last legal count */
    CHECK_EQ(v, 32766);
    v = -1;
    CHECK(!gw_to_matter_pressure(3276650, &v)); /* rounds to 32767 */
    CHECK(!gw_to_matter_pressure(UINT32_MAX, &v)); /* +50 must not wrap to a small number */
    CHECK(!gw_to_matter_pressure(UINT32_MAX - 49, &v));
    CHECK_EQ(v, -1);
    CHECK(!gw_to_matter_pressure(100000, NULL));
}

static void test_battery_half_percent(void)
{
    uint8_t v = 99;
    CHECK(gw_to_matter_battery(0, &v));
    CHECK_EQ(v, 0);
    CHECK(gw_to_matter_battery(97, &v));
    CHECK_EQ(v, 194);
    CHECK(gw_to_matter_battery(100, &v));
    CHECK_EQ(v, 200);

    v = 99;
    CHECK(!gw_to_matter_battery(101, &v));
    CHECK(!gw_to_matter_battery(255, &v));
    CHECK_EQ(v, 99);
    CHECK(!gw_to_matter_battery(50, NULL));
}

static void test_air_quality_class_boundaries(void)
{
    CHECK_EQ(gw_iaq_to_air_quality(0, 3), GW_AIR_QUALITY_GOOD);
    CHECK_EQ(gw_iaq_to_air_quality(50, 3), GW_AIR_QUALITY_GOOD);
    CHECK_EQ(gw_iaq_to_air_quality(51, 3), GW_AIR_QUALITY_FAIR);
    CHECK_EQ(gw_iaq_to_air_quality(100, 3), GW_AIR_QUALITY_FAIR);
    CHECK_EQ(gw_iaq_to_air_quality(101, 3), GW_AIR_QUALITY_MODERATE);
    CHECK_EQ(gw_iaq_to_air_quality(150, 3), GW_AIR_QUALITY_MODERATE);
    CHECK_EQ(gw_iaq_to_air_quality(151, 3), GW_AIR_QUALITY_POOR);
    CHECK_EQ(gw_iaq_to_air_quality(200, 3), GW_AIR_QUALITY_POOR);
    CHECK_EQ(gw_iaq_to_air_quality(201, 3), GW_AIR_QUALITY_VERY_POOR);
    CHECK_EQ(gw_iaq_to_air_quality(300, 3), GW_AIR_QUALITY_VERY_POOR);
    CHECK_EQ(gw_iaq_to_air_quality(301, 3), GW_AIR_QUALITY_EXTREMELY_POOR);
    CHECK_EQ(gw_iaq_to_air_quality(500, 3), GW_AIR_QUALITY_EXTREMELY_POOR);
}

static void test_air_quality_unknown_when_unreliable(void)
{
    CHECK_EQ(gw_iaq_to_air_quality(25, 0), GW_AIR_QUALITY_UNKNOWN);    /* BSEC still stabilising */
    CHECK_EQ(gw_iaq_to_air_quality(400, 0), GW_AIR_QUALITY_UNKNOWN);
    CHECK_EQ(gw_iaq_to_air_quality(501, 3), GW_AIR_QUALITY_UNKNOWN);   /* out of range */
    CHECK_EQ(gw_iaq_to_air_quality(UINT16_MAX, 3), GW_AIR_QUALITY_UNKNOWN);
    CHECK_EQ(gw_iaq_to_air_quality(25, 1), GW_AIR_QUALITY_GOOD);       /* any accuracy > 0 counts */
    CHECK_EQ(gw_iaq_to_air_quality(25, 2), GW_AIR_QUALITY_GOOD);
}

int main(void)
{
    RUN(test_temperature_range_edges);
    RUN(test_humidity_range_edges);
    RUN(test_pressure_rounds_to_hectopascal_counts);
    RUN(test_pressure_upper_limit_and_overflow);
    RUN(test_battery_half_percent);
    RUN(test_air_quality_class_boundaries);
    RUN(test_air_quality_unknown_when_unreliable);
    return MT_SUMMARY();
}
