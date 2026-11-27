/**
 * gw_report.h - "should this value be sent to Matter now?" gate (pure C99, injected time).
 *
 * Requirement (project_specification_and_requirements.md, BME680 section): report a change
 * when it exceeds a hysteresis (e.g. 0.2 degC, IAQ 10) OR cyclically every 60 s. One gate per
 * reported quantity. The first value is always sent.
 *
 * Time is a free-running uint32 millisecond counter (esp_timer_get_time()/1000 truncated);
 * differences are computed modulo 2^32, so the 49.7-day wrap-around is harmless as long as
 * the gate is polled more often than every 2^31 ms.
 */
#ifndef GW_REPORT_H
#define GW_REPORT_H

#include <stdbool.h>
#include <stdint.h>

#define GW_REPORT_TEMP_DELTA_C100 20     /* 0.20 degC in 0.01 degC units */
#define GW_REPORT_IAQ_DELTA 10
#define GW_REPORT_MAX_INTERVAL_MS 60000u

typedef struct {
    int32_t min_delta;        /* send when |value - last_sent| >= min_delta (0 = send every change) */
    uint32_t max_interval_ms; /* send when this long has passed since the last send (0 = never by time) */
    bool has_last;
    int32_t last_value;
    uint32_t last_time_ms;
} gw_report_gate_t;

void gw_report_gate_init(gw_report_gate_t *g, int32_t min_delta, uint32_t max_interval_ms);

/** True when `value` should be sent now; the gate then remembers it as the last sent value. */
bool gw_report_should_send(gw_report_gate_t *g, int32_t value, uint32_t now_ms);

/** Forget the last value (e.g. after a Matter subscription was re-established): next call sends. */
void gw_report_gate_reset(gw_report_gate_t *g);

#endif /* GW_REPORT_H */
