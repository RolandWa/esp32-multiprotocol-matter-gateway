/* Unit tests for gw_report.c: send on change >= delta or every max_interval, wrap-safe time. */
#include <stdint.h>

#include "gw_report.h"
#include "minitest.h"

static void test_defaults_match_the_requirement(void)
{
    CHECK_EQ(GW_REPORT_TEMP_DELTA_C100, 20);      /* 0.2 degC */
    CHECK_EQ(GW_REPORT_IAQ_DELTA, 10);
    CHECK_EQ(GW_REPORT_MAX_INTERVAL_MS, 60000);
}

static void test_first_value_is_always_sent(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 20, 60000);
    CHECK(gw_report_should_send(&g, 2150, 1000));
    CHECK(!gw_report_should_send(&g, 2150, 1001));
}

static void test_delta_threshold_is_inclusive(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, GW_REPORT_TEMP_DELTA_C100, GW_REPORT_MAX_INTERVAL_MS);
    CHECK(gw_report_should_send(&g, 2000, 0));
    CHECK(!gw_report_should_send(&g, 2019, 10));   /* +0.19 degC */
    CHECK(gw_report_should_send(&g, 2020, 20));    /* +0.20 degC exactly */
}

static void test_negative_change_counts_too(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 20, 60000);
    CHECK(gw_report_should_send(&g, 2000, 0));
    CHECK(!gw_report_should_send(&g, 1981, 10));
    CHECK(gw_report_should_send(&g, 1980, 20));
}

static void test_delta_is_measured_against_last_sent_not_last_seen(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 10, 0);
    CHECK(gw_report_should_send(&g, 100, 0));
    CHECK(!gw_report_should_send(&g, 105, 1));
    CHECK(!gw_report_should_send(&g, 109, 2));     /* slow drift must not be lost ... */
    CHECK(gw_report_should_send(&g, 110, 3));      /* ... it accumulates against 100 */
    CHECK(!gw_report_should_send(&g, 105, 4));     /* and the new baseline is 110 */
}

static void test_interval_is_inclusive(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 20, 60000);
    CHECK(gw_report_should_send(&g, 500, 1000));
    CHECK(!gw_report_should_send(&g, 500, 1000 + 59999));
    CHECK(gw_report_should_send(&g, 500, 1000 + 60000));
    CHECK(!gw_report_should_send(&g, 500, 1000 + 60001));   /* the timer restarted at the send */
    CHECK(gw_report_should_send(&g, 500, 1000 + 120000));
}

static void test_interval_survives_counter_wrap(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 0, 200);
    CHECK(gw_report_should_send(&g, 7, UINT32_MAX - 99));   /* 100 ms before the wrap */
    CHECK(!gw_report_should_send(&g, 7, 99));               /* 199 ms later, across the wrap */
    CHECK(gw_report_should_send(&g, 7, 100));               /* 200 ms later */
}

static void test_zero_delta_sends_every_change_only(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 0, 0);
    CHECK(gw_report_should_send(&g, 5, 0));
    CHECK(!gw_report_should_send(&g, 5, 1));
    CHECK(gw_report_should_send(&g, 6, 2));
    CHECK(!gw_report_should_send(&g, 6, 4000000000u));      /* interval 0 = never by time */
}

static void test_negative_delta_is_clamped(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, -5, 0);
    CHECK_EQ(g.min_delta, 0);
    CHECK(gw_report_should_send(&g, 1, 0));
    CHECK(!gw_report_should_send(&g, 1, 1));                /* an unchanged value never fires on delta */
}

static void test_reset_forces_the_next_send(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 20, 60000);
    CHECK(gw_report_should_send(&g, 10, 0));
    CHECK(!gw_report_should_send(&g, 10, 1));
    gw_report_gate_reset(&g);
    CHECK(gw_report_should_send(&g, 10, 2));
}

static void test_extreme_values_do_not_overflow(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 1000, 0);
    CHECK(gw_report_should_send(&g, INT32_MIN, 0));
    CHECK(gw_report_should_send(&g, INT32_MAX, 1));         /* |delta| = 2^32 - 1 needs 64-bit maths */
    CHECK(gw_report_should_send(&g, INT32_MIN, 2));
}

static void test_not_sent_means_state_unchanged(void)
{
    gw_report_gate_t g;
    gw_report_gate_init(&g, 20, 60000);
    CHECK(gw_report_should_send(&g, 100, 1000));
    CHECK(!gw_report_should_send(&g, 110, 2000));
    CHECK_EQ(g.last_value, 100);
    CHECK_EQ(g.last_time_ms, 1000);
}

static void test_null_gate(void)
{
    gw_report_gate_init(NULL, 1, 1);
    gw_report_gate_reset(NULL);
    CHECK(!gw_report_should_send(NULL, 1, 1));
}

int main(void)
{
    RUN(test_defaults_match_the_requirement);
    RUN(test_first_value_is_always_sent);
    RUN(test_delta_threshold_is_inclusive);
    RUN(test_negative_change_counts_too);
    RUN(test_delta_is_measured_against_last_sent_not_last_seen);
    RUN(test_interval_is_inclusive);
    RUN(test_interval_survives_counter_wrap);
    RUN(test_zero_delta_sends_every_change_only);
    RUN(test_negative_delta_is_clamped);
    RUN(test_reset_forces_the_next_send);
    RUN(test_extreme_values_do_not_overflow);
    RUN(test_not_sent_means_state_unchanged);
    RUN(test_null_gate);
    return MT_SUMMARY();
}
