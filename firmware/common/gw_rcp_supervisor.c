#include "gw_rcp_supervisor.h"

#include <stddef.h>

void gw_rcp_default_cfg(gw_rcp_cfg_t *cfg)
{
    if (cfg == NULL) {
        return;
    }
    cfg->reset_hold_ms = 100;
    cfg->boot_timeout_ms = 3000;
    cfg->alive_timeout_ms = 10000;
    cfg->backoff_base_ms = 1000;
    cfg->backoff_max_ms = 30000;
    cfg->stable_ms = 60000;
    cfg->max_failures = 5;
}

bool gw_rcp_sup_init(gw_rcp_sup_t *s, const gw_rcp_cfg_t *cfg)
{
    if (s == NULL || cfg == NULL || cfg->reset_hold_ms == 0 || cfg->boot_timeout_ms == 0 ||
        cfg->alive_timeout_ms == 0 || cfg->backoff_base_ms == 0 || cfg->backoff_max_ms < cfg->backoff_base_ms) {
        return false;
    }
    s->cfg = *cfg;
    s->state = GW_RCP_INIT;
    s->state_since_ms = 0;
    s->last_alive_ms = 0;
    s->running_since_ms = 0;
    s->consecutive_failures = 0;
    s->total_resets = 0;
    return true;
}

static void enter(gw_rcp_sup_t *s, gw_rcp_state_t st, uint32_t now_ms)
{
    s->state = st;
    s->state_since_ms = now_ms;
}

static uint32_t backoff_ms(const gw_rcp_sup_t *s)
{
    /* failures >= 1 here; base * 2^(failures-1), capped (shift bounded to avoid overflow) */
    uint32_t wait = s->cfg.backoff_base_ms;
    for (uint8_t i = 1; i < s->consecutive_failures; i++) {
        if (wait >= s->cfg.backoff_max_ms / 2u + 1u) {
            return s->cfg.backoff_max_ms;
        }
        wait *= 2u;
    }
    return wait > s->cfg.backoff_max_ms ? s->cfg.backoff_max_ms : wait;
}

/* Count a failure; go to FAILED when the budget is spent, else wait before the next reset. */
static void fail(gw_rcp_sup_t *s, uint32_t now_ms)
{
    if (s->consecutive_failures < UINT8_MAX) {
        s->consecutive_failures++;
    }
    if (s->cfg.max_failures != 0 && s->consecutive_failures >= s->cfg.max_failures) {
        enter(s, GW_RCP_FAILED, now_ms);
    } else {
        enter(s, GW_RCP_BACKOFF, now_ms);
    }
}

gw_rcp_action_t gw_rcp_sup_step(gw_rcp_sup_t *s, uint32_t now_ms, gw_rcp_event_t ev)
{
    if (s == NULL || s->state == GW_RCP_FAILED) {
        return GW_RCP_ACT_NONE;
    }
    if (ev == GW_RCP_EV_VERSION_MISMATCH) {
        enter(s, GW_RCP_FAILED, now_ms);
        return GW_RCP_ACT_NONE;
    }

    const uint32_t in_state = (uint32_t)(now_ms - s->state_since_ms);

    switch (s->state) {
    case GW_RCP_INIT:
        s->total_resets++;
        enter(s, GW_RCP_RESETTING, now_ms);
        return GW_RCP_ACT_ASSERT_RESET;

    case GW_RCP_RESETTING:
        if (in_state >= s->cfg.reset_hold_ms) {
            enter(s, GW_RCP_BOOTING, now_ms);
            return GW_RCP_ACT_RELEASE_RESET;
        }
        return GW_RCP_ACT_NONE;

    case GW_RCP_BOOTING:
        if (ev == GW_RCP_EV_ALIVE) {
            s->last_alive_ms = now_ms;
            s->running_since_ms = now_ms;
            enter(s, GW_RCP_RUNNING, now_ms);
        } else if (in_state >= s->cfg.boot_timeout_ms) {
            fail(s, now_ms);
        }
        return GW_RCP_ACT_NONE;

    case GW_RCP_RUNNING:
        if (ev == GW_RCP_EV_ALIVE) {
            s->last_alive_ms = now_ms;
        }
        if ((uint32_t)(now_ms - s->last_alive_ms) >= s->cfg.alive_timeout_ms) {
            fail(s, now_ms);
        } else if (s->consecutive_failures != 0 && s->cfg.stable_ms != 0 &&
                   (uint32_t)(now_ms - s->running_since_ms) >= s->cfg.stable_ms) {
            s->consecutive_failures = 0;
        }
        return GW_RCP_ACT_NONE;

    case GW_RCP_BACKOFF:
        if (in_state >= backoff_ms(s)) {
            s->total_resets++;
            enter(s, GW_RCP_RESETTING, now_ms);
            return GW_RCP_ACT_ASSERT_RESET;
        }
        return GW_RCP_ACT_NONE;

    case GW_RCP_FAILED:
        break;
    }
    return GW_RCP_ACT_NONE;
}

const char *gw_rcp_state_str(gw_rcp_state_t state)
{
    switch (state) {
    case GW_RCP_INIT:      return "init";
    case GW_RCP_RESETTING: return "resetting";
    case GW_RCP_BOOTING:   return "booting";
    case GW_RCP_RUNNING:   return "running";
    case GW_RCP_BACKOFF:   return "backoff";
    case GW_RCP_FAILED:    return "failed";
    }
    return "unknown";
}
