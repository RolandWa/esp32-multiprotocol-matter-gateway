/* Unit tests for gw_ventilation.c. Requirement: ON when IAQ > 150, OFF when IAQ < 110. */
#include <stdint.h>

#include "gw_units.h"
#include "gw_ventilation.h"
#include "minitest.h"

static gw_vent_t make(void)
{
    gw_vent_t v;
    gw_vent_cfg_t cfg;
    gw_vent_default_cfg(&cfg);
    CHECK(gw_vent_init(&v, &cfg));
    return v;
}

static void test_defaults_match_the_requirement(void)
{
    gw_vent_cfg_t cfg;
    gw_vent_default_cfg(&cfg);
    CHECK_EQ(cfg.on_above, 150);
    CHECK_EQ(cfg.off_below, 110);
    CHECK_EQ(cfg.min_accuracy, 1);
}

static void test_starts_off(void)
{
    gw_vent_t v = make();
    CHECK(!v.active);
}

static void test_on_threshold_is_strictly_above(void)
{
    gw_vent_t v = make();
    CHECK(!gw_vent_update(&v, 150, 3));   /* "IAQ > 150": 150 itself does not trigger */
    CHECK(gw_vent_update(&v, 151, 3));
}

static void test_off_threshold_is_strictly_below(void)
{
    gw_vent_t v = make();
    CHECK(gw_vent_update(&v, 200, 3));
    CHECK(gw_vent_update(&v, 110, 3));    /* "IAQ < 110": 110 itself keeps it on */
    CHECK(!gw_vent_update(&v, 109, 3));
}

static void test_hysteresis_band_holds_state_in_both_directions(void)
{
    gw_vent_t v = make();
    CHECK(!gw_vent_update(&v, 130, 3));   /* rising into the band from below: stays off */
    CHECK(gw_vent_update(&v, 160, 3));
    CHECK(gw_vent_update(&v, 130, 3));    /* falling into the band from above: stays on */
    CHECK(gw_vent_update(&v, 111, 3));
    CHECK(gw_vent_update(&v, 150, 3));
}

static void test_noise_around_the_on_threshold_does_not_flap(void)
{
    gw_vent_t v = make();
    int transitions = 0;
    bool prev = false;
    for (int i = 0; i < 100; i++) {
        bool now = gw_vent_update(&v, (uint16_t)((i & 1) ? 151 : 149), 3);
        if (now != prev) {
            transitions++;
            prev = now;
        }
    }
    CHECK_EQ(transitions, 1);             /* went on once and stayed on */
    CHECK(v.active);
}

static void test_unreliable_samples_hold_the_state(void)
{
    gw_vent_t v = make();
    CHECK(!gw_vent_update(&v, 400, 0));   /* accuracy 0: must not raise the flag */
    CHECK(gw_vent_update(&v, 400, 1));
    CHECK(gw_vent_update(&v, 20, 0));     /* nor clear it */
    CHECK(!gw_vent_update(&v, 20, 1));
}

static void test_invalid_iaq_is_ignored(void)
{
    gw_vent_t v = make();
    CHECK(!gw_vent_update(&v, 501, 3));
    CHECK(!gw_vent_update(&v, UINT16_MAX, 3));
    CHECK(gw_vent_update(&v, 500, 3));    /* 500 is the largest valid value */
    CHECK(gw_vent_update(&v, 501, 3));    /* and an invalid one does not clear it */
}

static void test_custom_config(void)
{
    gw_vent_t v;
    gw_vent_cfg_t cfg = {100, 80, 3};
    CHECK(gw_vent_init(&v, &cfg));
    CHECK(!gw_vent_update(&v, 300, 2));   /* below the required accuracy */
    CHECK(gw_vent_update(&v, 101, 3));
    CHECK(gw_vent_update(&v, 80, 3));
    CHECK(!gw_vent_update(&v, 79, 3));
}

static void test_equal_thresholds_are_allowed_and_inverted_rejected(void)
{
    gw_vent_t v;
    gw_vent_cfg_t same = {120, 120, 0};
    gw_vent_cfg_t inverted = {110, 150, 0};
    CHECK(gw_vent_init(&v, &same));
    CHECK(gw_vent_update(&v, 121, 0));
    CHECK(!gw_vent_update(&v, 119, 0));
    CHECK(gw_vent_update(&v, 121, 0));
    CHECK(gw_vent_update(&v, 120, 0));    /* exactly at the threshold: neither > nor < */

    v.active = true;
    CHECK(!gw_vent_init(&v, &inverted));
    CHECK(v.active);                      /* rejected init leaves the object untouched */
    CHECK_EQ(v.cfg.on_above, 120);
}

static void test_null_arguments(void)
{
    gw_vent_cfg_t cfg;
    gw_vent_t v;
    gw_vent_default_cfg(NULL);
    gw_vent_default_cfg(&cfg);
    CHECK(!gw_vent_init(NULL, &cfg));
    CHECK(!gw_vent_init(&v, NULL));
    CHECK(!gw_vent_update(NULL, 300, 3));
}

static void test_threshold_sits_on_the_moderate_poor_boundary(void)
{
    /* the flag and the Matter AirQuality enum must agree: ventilate <=> Poor or worse */
    for (uint16_t iaq = 0; iaq <= 500; iaq++) {
        gw_vent_t fresh = make();
        bool flag = gw_vent_update(&fresh, iaq, 3);
        bool poor_or_worse = gw_iaq_to_air_quality(iaq, 3) >= GW_AIR_QUALITY_POOR;
        CHECK(flag == poor_or_worse);
    }
}

int main(void)
{
    RUN(test_defaults_match_the_requirement);
    RUN(test_starts_off);
    RUN(test_on_threshold_is_strictly_above);
    RUN(test_off_threshold_is_strictly_below);
    RUN(test_hysteresis_band_holds_state_in_both_directions);
    RUN(test_noise_around_the_on_threshold_does_not_flap);
    RUN(test_unreliable_samples_hold_the_state);
    RUN(test_invalid_iaq_is_ignored);
    RUN(test_custom_config);
    RUN(test_equal_thresholds_are_allowed_and_inverted_rejected);
    RUN(test_null_arguments);
    RUN(test_threshold_sits_on_the_moderate_poor_boundary);
    return MT_SUMMARY();
}
