/**
 * gw_rcp_supervisor.h - supervision of the 802.15.4 radio co-processor (C6) by the host (S3).
 *
 * Pure state machine with injected time. The Spinel/HDLC link itself is Espressif's code; this
 * only decides WHEN to reset the RCP and when to give up (docs/CODING_GUIDELINES.md section 4):
 *
 *   INIT --step--> RESETTING (action ASSERT_RESET: drive C6 EN low)
 *   RESETTING --reset_hold_ms--> BOOTING (action RELEASE_RESET: EN high, BOOT high = run mode)
 *   BOOTING --ALIVE--> RUNNING            BOOTING --boot_timeout_ms--> BACKOFF
 *   RUNNING --no ALIVE for alive_timeout_ms--> BACKOFF
 *   BACKOFF --backoff (doubles per consecutive failure, capped)--> RESETTING (ASSERT_RESET)
 *   any --VERSION_MISMATCH--> FAILED     (no retry: another reset cannot fix a wrong image;
 *                                         the host should report it and offer an RCP update)
 *   BACKOFF with max_failures consecutive failures --> FAILED
 *   RUNNING for stable_ms resets the consecutive-failure counter.
 *
 * "ALIVE" is whatever the host layer treats as proof of life: a valid Spinel frame, the answer
 * to a version query. The EN/BOOT GPIO numbers are hardware (per-target pin header, still open);
 * this module never touches a pin - the caller executes the returned action.
 *
 * The defaults below are PROPOSALS, not measurements; reset_hold_ms matches esp-serial-flasher's
 * default reset hold (100 ms), the rest awaits a bring-up on real boards (tests/hw).
 */
#ifndef GW_RCP_SUPERVISOR_H
#define GW_RCP_SUPERVISOR_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    GW_RCP_INIT = 0,
    GW_RCP_RESETTING,
    GW_RCP_BOOTING,
    GW_RCP_RUNNING,
    GW_RCP_BACKOFF,
    GW_RCP_FAILED
} gw_rcp_state_t;

typedef enum {
    GW_RCP_EV_NONE = 0,
    GW_RCP_EV_ALIVE,
    GW_RCP_EV_VERSION_MISMATCH
} gw_rcp_event_t;

typedef enum {
    GW_RCP_ACT_NONE = 0,
    GW_RCP_ACT_ASSERT_RESET,   /* drive the C6 EN pin low */
    GW_RCP_ACT_RELEASE_RESET   /* release EN (BOOT stays high: normal boot) */
} gw_rcp_action_t;

typedef struct {
    uint32_t reset_hold_ms;     /* EN low for this long */
    uint32_t boot_timeout_ms;   /* after release: max wait for the first ALIVE */
    uint32_t alive_timeout_ms;  /* in RUNNING: max silence before the RCP is declared dead */
    uint32_t backoff_base_ms;   /* wait before retry #1; doubles each consecutive failure */
    uint32_t backoff_max_ms;
    uint32_t stable_ms;         /* RUNNING this long clears the consecutive-failure counter */
    uint8_t max_failures;       /* consecutive failures before FAILED (0 = never give up) */
} gw_rcp_cfg_t;

typedef struct {
    gw_rcp_cfg_t cfg;
    gw_rcp_state_t state;
    uint32_t state_since_ms;
    uint32_t last_alive_ms;
    uint32_t running_since_ms;
    uint8_t consecutive_failures;
    uint32_t total_resets;      /* number of ASSERT_RESET actions issued (for diagnostics) */
} gw_rcp_sup_t;

void gw_rcp_default_cfg(gw_rcp_cfg_t *cfg);

/** Returns false for NULL or an unusable config (a zero timeout, backoff_max < backoff_base). */
bool gw_rcp_sup_init(gw_rcp_sup_t *s, const gw_rcp_cfg_t *cfg);

/**
 * Advance the machine to `now_ms`, applying `ev`. Returns the single action the caller must
 * execute now (usually GW_RCP_ACT_NONE). Call it periodically (e.g. every 100 ms) and on events.
 * In FAILED and for NULL `s` it always returns NONE.
 */
gw_rcp_action_t gw_rcp_sup_step(gw_rcp_sup_t *s, uint32_t now_ms, gw_rcp_event_t ev);

const char *gw_rcp_state_str(gw_rcp_state_t state);

#endif /* GW_RCP_SUPERVISOR_H */
