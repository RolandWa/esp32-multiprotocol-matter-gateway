/* Unit tests for gw_rcp_supervisor.c with injected time; the "RCP" is simulated by the events fed in. */
#include <stdint.h>

#include "gw_rcp_supervisor.h"
#include "minitest.h"

static gw_rcp_cfg_t cfg(void)
{
    gw_rcp_cfg_t c;
    gw_rcp_default_cfg(&c);   /* hold 100, boot 3000, alive 10000, backoff 1000..30000, stable 60000, max 5 */
    return c;
}

/* Start the machine at `t0` and run it through the reset sequence up to BOOTING. Returns the time of release. */
static uint32_t start_to_booting(gw_rcp_sup_t *s, uint32_t t0)
{
    CHECK_EQ(gw_rcp_sup_step(s, t0, GW_RCP_EV_NONE), GW_RCP_ACT_ASSERT_RESET);
    CHECK_EQ(s->state, GW_RCP_RESETTING);
    CHECK_EQ(gw_rcp_sup_step(s, t0 + s->cfg.reset_hold_ms, GW_RCP_EV_NONE), GW_RCP_ACT_RELEASE_RESET);
    CHECK_EQ(s->state, GW_RCP_BOOTING);
    return t0 + s->cfg.reset_hold_ms;
}

/* Every wait in this file is bounded: a broken module must fail a test, never hang the suite. */

/* Step 1 ms at a time with no events until the machine is in `want`. False if `limit_ms` pass first. */
static bool advance_to_state(gw_rcp_sup_t *s, uint32_t *now, gw_rcp_state_t want, uint32_t limit_ms)
{
    for (uint32_t i = 0; s->state != want; i++) {
        if (i >= limit_ms) {
            return false;
        }
        (*now)++;
        gw_rcp_sup_step(s, *now, GW_RCP_EV_NONE);
    }
    return true;
}

/* Same, until `consecutive_failures` reaches `n`. */
static bool advance_to_failures(gw_rcp_sup_t *s, uint32_t *now, uint8_t n, uint32_t limit_ms)
{
    for (uint32_t i = 0; s->consecutive_failures < n; i++) {
        if (i >= limit_ms) {
            return false;
        }
        (*now)++;
        gw_rcp_sup_step(s, *now, GW_RCP_EV_NONE);
    }
    return true;
}

/* Step 1 ms at a time with no events until `want` happens or `limit_ms` pass. Returns elapsed ms, or -1. */
static long run_until_action(gw_rcp_sup_t *s, uint32_t *now, gw_rcp_action_t want, uint32_t limit_ms)
{
    for (uint32_t i = 0; i < limit_ms; i++) {
        (*now)++;
        if (gw_rcp_sup_step(s, *now, GW_RCP_EV_NONE) == want) {
            return (long)(i + 1);
        }
    }
    return -1;
}

static void test_config_validation(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));
    CHECK_EQ(s.state, GW_RCP_INIT);

    c = cfg(); c.reset_hold_ms = 0;    CHECK(!gw_rcp_sup_init(&s, &c));
    c = cfg(); c.boot_timeout_ms = 0;  CHECK(!gw_rcp_sup_init(&s, &c));
    c = cfg(); c.alive_timeout_ms = 0; CHECK(!gw_rcp_sup_init(&s, &c));
    c = cfg(); c.backoff_base_ms = 0;  CHECK(!gw_rcp_sup_init(&s, &c));
    c = cfg(); c.backoff_max_ms = c.backoff_base_ms - 1; CHECK(!gw_rcp_sup_init(&s, &c));
    c = cfg(); c.backoff_max_ms = c.backoff_base_ms;     CHECK(gw_rcp_sup_init(&s, &c));  /* equal is fine */
    c = cfg(); c.stable_ms = 0; c.max_failures = 0;      CHECK(gw_rcp_sup_init(&s, &c));  /* optional features off */
    CHECK(!gw_rcp_sup_init(NULL, &c));
    CHECK(!gw_rcp_sup_init(&s, NULL));
    gw_rcp_default_cfg(NULL);
}

static void test_happy_path_reset_sequence_then_running(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));

    CHECK_EQ(gw_rcp_sup_step(&s, 0, GW_RCP_EV_NONE), GW_RCP_ACT_ASSERT_RESET);
    CHECK_EQ(gw_rcp_sup_step(&s, 99, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);     /* EN low for 100 ms */
    CHECK_EQ(s.state, GW_RCP_RESETTING);
    CHECK_EQ(gw_rcp_sup_step(&s, 100, GW_RCP_EV_NONE), GW_RCP_ACT_RELEASE_RESET);
    CHECK_EQ(s.state, GW_RCP_BOOTING);
    CHECK_EQ(gw_rcp_sup_step(&s, 400, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    for (uint32_t t = 1400; t < 40000; t += 1000) {
        CHECK_EQ(gw_rcp_sup_step(&s, t, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);
        CHECK_EQ(s.state, GW_RCP_RUNNING);
    }
    CHECK_EQ(s.total_resets, 1);
    CHECK_EQ(s.consecutive_failures, 0);
}

static void test_alive_during_reset_is_ignored(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));
    gw_rcp_sup_step(&s, 0, GW_RCP_EV_NONE);
    CHECK_EQ(gw_rcp_sup_step(&s, 50, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);  /* stale bytes while EN is low */
    CHECK_EQ(s.state, GW_RCP_RESETTING);
    CHECK_EQ(gw_rcp_sup_step(&s, 100, GW_RCP_EV_ALIVE), GW_RCP_ACT_RELEASE_RESET);
    CHECK_EQ(s.state, GW_RCP_BOOTING);                                     /* not skipped straight to RUNNING */
}

static void test_boot_timeout_leads_to_backoff_and_a_new_reset(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    uint32_t rel;
    CHECK(gw_rcp_sup_init(&s, &c));
    rel = start_to_booting(&s, 0);

    CHECK_EQ(gw_rcp_sup_step(&s, rel + 2999, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_BOOTING);
    CHECK_EQ(gw_rcp_sup_step(&s, rel + 3000, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_BACKOFF);
    CHECK_EQ(s.consecutive_failures, 1);

    CHECK_EQ(gw_rcp_sup_step(&s, rel + 3000 + 999, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(gw_rcp_sup_step(&s, rel + 3000 + 1000, GW_RCP_EV_NONE), GW_RCP_ACT_ASSERT_RESET);
    CHECK_EQ(s.state, GW_RCP_RESETTING);
    CHECK_EQ(s.total_resets, 2);
}

static void test_dead_rcp_in_running_state_is_detected(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));
    start_to_booting(&s, 0);
    gw_rcp_sup_step(&s, 500, GW_RCP_EV_ALIVE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);

    CHECK_EQ(gw_rcp_sup_step(&s, 500 + 9999, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    CHECK_EQ(gw_rcp_sup_step(&s, 500 + 10000, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_BACKOFF);
}

static void test_alive_events_postpone_the_dead_timeout(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));
    start_to_booting(&s, 0);
    gw_rcp_sup_step(&s, 500, GW_RCP_EV_ALIVE);
    gw_rcp_sup_step(&s, 9000, GW_RCP_EV_ALIVE);
    gw_rcp_sup_step(&s, 9000 + 9999, GW_RCP_EV_NONE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    gw_rcp_sup_step(&s, 9000 + 10000, GW_RCP_EV_NONE);
    CHECK_EQ(s.state, GW_RCP_BACKOFF);
}

static void test_alive_event_arriving_with_the_timeout_wins(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    CHECK(gw_rcp_sup_init(&s, &c));
    start_to_booting(&s, 0);
    gw_rcp_sup_step(&s, 500, GW_RCP_EV_ALIVE);
    gw_rcp_sup_step(&s, 500 + 10000, GW_RCP_EV_ALIVE);   /* late, but alive: not declared dead */
    CHECK_EQ(s.state, GW_RCP_RUNNING);
}

static void test_backoff_doubles_and_is_capped(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    const long expected[] = {1000, 2000, 4000, 5000, 5000, 5000};   /* cap 5000 */
    uint32_t now = 0;
    c.backoff_max_ms = 5000;
    c.max_failures = 0;                                            /* never give up */
    CHECK(gw_rcp_sup_init(&s, &c));
    start_to_booting(&s, now);
    now = s.state_since_ms;

    for (size_t i = 0; i < sizeof expected / sizeof expected[0]; i++) {
        long to_backoff, to_reset;
        /* silent RCP: wait for the boot timeout to land in BACKOFF ... */
        to_backoff = 0;
        while (s.state != GW_RCP_BACKOFF && to_backoff < 100000) {
            now++;
            to_backoff++;
            gw_rcp_sup_step(&s, now, GW_RCP_EV_NONE);
        }
        CHECK_EQ(s.state, GW_RCP_BACKOFF);
        /* ... then measure how long BACKOFF lasts */
        to_reset = run_until_action(&s, &now, GW_RCP_ACT_ASSERT_RESET, 100000);
        CHECK_EQ(to_reset, expected[i]);
        /* finish the reset sequence into BOOTING again */
        to_reset = run_until_action(&s, &now, GW_RCP_ACT_RELEASE_RESET, 1000);
        CHECK_EQ(to_reset, 100);
    }
}

static void test_gives_up_after_max_consecutive_failures(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();                 /* max_failures = 5 */
    uint32_t now = 0;
    int resets_seen = 1;
    CHECK(gw_rcp_sup_init(&s, &c));
    CHECK_EQ(gw_rcp_sup_step(&s, now, GW_RCP_EV_NONE), GW_RCP_ACT_ASSERT_RESET);

    for (int i = 0; i < 200000 && s.state != GW_RCP_FAILED; i++) {
        now++;
        if (gw_rcp_sup_step(&s, now, GW_RCP_EV_NONE) == GW_RCP_ACT_ASSERT_RESET) {
            resets_seen++;
        }
    }
    CHECK_EQ(s.state, GW_RCP_FAILED);
    CHECK_EQ(s.consecutive_failures, 5);
    CHECK_EQ(resets_seen, 5);               /* initial reset + 4 retries; the 5th failure ends it */
    CHECK_EQ(s.total_resets, 5);

    for (int i = 0; i < 100; i++) {         /* FAILED is final: nothing wakes it up, not even ALIVE */
        now += 100000;
        CHECK_EQ(gw_rcp_sup_step(&s, now, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);
        CHECK_EQ(s.state, GW_RCP_FAILED);
    }
    CHECK_EQ(s.total_resets, 5);
}

static void test_version_mismatch_is_fatal_from_any_state(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();

    CHECK(gw_rcp_sup_init(&s, &c));                          /* in INIT */
    CHECK_EQ(gw_rcp_sup_step(&s, 0, GW_RCP_EV_VERSION_MISMATCH), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_FAILED);
    CHECK_EQ(s.total_resets, 0);

    CHECK(gw_rcp_sup_init(&s, &c));                          /* while booting */
    start_to_booting(&s, 0);
    CHECK_EQ(gw_rcp_sup_step(&s, 200, GW_RCP_EV_VERSION_MISMATCH), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_FAILED);

    CHECK(gw_rcp_sup_init(&s, &c));                          /* while running: no reset can fix a wrong image */
    start_to_booting(&s, 0);
    gw_rcp_sup_step(&s, 300, GW_RCP_EV_ALIVE);
    CHECK_EQ(gw_rcp_sup_step(&s, 400, GW_RCP_EV_VERSION_MISMATCH), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_FAILED);
    CHECK_EQ(gw_rcp_sup_step(&s, 500000, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.total_resets, 1);
}

static void test_stable_running_clears_the_failure_counter(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    uint32_t now = 0;
    long wait;
    CHECK(gw_rcp_sup_init(&s, &c));
    gw_rcp_sup_step(&s, now, GW_RCP_EV_NONE);

    /* two silent boots: failures = 2 */
    CHECK(advance_to_failures(&s, &now, 2, 100000));
    CHECK_EQ(s.consecutive_failures, 2);
    CHECK(advance_to_state(&s, &now, GW_RCP_BOOTING, 100000)); /* until the third boot attempt starts */
    now++;
    gw_rcp_sup_step(&s, now, GW_RCP_EV_ALIVE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    CHECK_EQ(s.consecutive_failures, 2);                     /* not cleared by merely coming up */

    {
        const uint32_t up = now;
        for (uint32_t t = up + 1000; t < up + 60000; t += 1000) {
            gw_rcp_sup_step(&s, t, GW_RCP_EV_ALIVE);
        }
        CHECK_EQ(s.consecutive_failures, 2);                 /* 59 s: not stable yet */
        gw_rcp_sup_step(&s, up + 60000, GW_RCP_EV_ALIVE);
        CHECK_EQ(s.consecutive_failures, 0);                 /* 60 s: stable */
        now = up + 60000;
    }

    /* the next failure starts from the short backoff again, not from 4 s */
    CHECK(advance_to_state(&s, &now, GW_RCP_BACKOFF, 100000));
    CHECK_EQ(s.consecutive_failures, 1);
    wait = run_until_action(&s, &now, GW_RCP_ACT_ASSERT_RESET, 100000);
    CHECK_EQ(wait, 1000);
}

static void test_flapping_before_stable_keeps_counting(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    uint32_t now = 0;
    CHECK(gw_rcp_sup_init(&s, &c));
    for (int round = 1; round <= 4; round++) {               /* comes up, goes silent (dead after 10 s), repeat */
        CHECK(advance_to_state(&s, &now, GW_RCP_BOOTING, 100000));
        now++;
        gw_rcp_sup_step(&s, now, GW_RCP_EV_ALIVE);
        CHECK_EQ(s.state, GW_RCP_RUNNING);
        {
            const uint32_t up = now;
            while (s.state == GW_RCP_RUNNING && now < up + 100000) {
                now++;
                gw_rcp_sup_step(&s, now, GW_RCP_EV_NONE);
            }
        }
        CHECK_EQ(s.state, GW_RCP_BACKOFF);
        CHECK_EQ(s.consecutive_failures, round);             /* ~10 s of uptime is not "stable" (60 s) */
    }
}

static void test_time_counter_wrap_is_harmless(void)
{
    gw_rcp_sup_t s;
    gw_rcp_cfg_t c = cfg();
    uint32_t t0 = UINT32_MAX - 50;                           /* the counter wraps during the 100 ms reset hold */
    CHECK(gw_rcp_sup_init(&s, &c));
    CHECK_EQ(gw_rcp_sup_step(&s, t0, GW_RCP_EV_NONE), GW_RCP_ACT_ASSERT_RESET);
    CHECK_EQ(gw_rcp_sup_step(&s, t0 + 99, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(gw_rcp_sup_step(&s, t0 + 100, GW_RCP_EV_NONE), GW_RCP_ACT_RELEASE_RESET);
    CHECK_EQ(gw_rcp_sup_step(&s, t0 + 150, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    CHECK_EQ(gw_rcp_sup_step(&s, t0 + 150 + 9999, GW_RCP_EV_NONE), GW_RCP_ACT_NONE);
    CHECK_EQ(s.state, GW_RCP_RUNNING);
    gw_rcp_sup_step(&s, t0 + 150 + 10000, GW_RCP_EV_NONE);
    CHECK_EQ(s.state, GW_RCP_BACKOFF);
}

static void test_null_and_names(void)
{
    CHECK_EQ(gw_rcp_sup_step(NULL, 0, GW_RCP_EV_ALIVE), GW_RCP_ACT_NONE);
    CHECK(gw_rcp_state_str(GW_RCP_INIT) != NULL);
    CHECK(gw_rcp_state_str(GW_RCP_RUNNING) != NULL);
    CHECK(gw_rcp_state_str(GW_RCP_FAILED) != NULL);
    CHECK(gw_rcp_state_str((gw_rcp_state_t)42) != NULL);
}

int main(void)
{
    RUN(test_config_validation);
    RUN(test_happy_path_reset_sequence_then_running);
    RUN(test_alive_during_reset_is_ignored);
    RUN(test_boot_timeout_leads_to_backoff_and_a_new_reset);
    RUN(test_dead_rcp_in_running_state_is_detected);
    RUN(test_alive_events_postpone_the_dead_timeout);
    RUN(test_alive_event_arriving_with_the_timeout_wins);
    RUN(test_backoff_doubles_and_is_capped);
    RUN(test_gives_up_after_max_consecutive_failures);
    RUN(test_version_mismatch_is_fatal_from_any_state);
    RUN(test_stable_running_clears_the_failure_counter);
    RUN(test_flapping_before_stable_keeps_counting);
    RUN(test_time_counter_wrap_is_harmless);
    RUN(test_null_and_names);
    return MT_SUMMARY();
}
