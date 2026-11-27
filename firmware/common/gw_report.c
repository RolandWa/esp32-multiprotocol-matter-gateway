#include "gw_report.h"

#include <stddef.h>

void gw_report_gate_init(gw_report_gate_t *g, int32_t min_delta, uint32_t max_interval_ms)
{
    if (g == NULL) {
        return;
    }
    g->min_delta = min_delta < 0 ? 0 : min_delta;
    g->max_interval_ms = max_interval_ms;
    g->has_last = false;
    g->last_value = 0;
    g->last_time_ms = 0;
}

void gw_report_gate_reset(gw_report_gate_t *g)
{
    if (g != NULL) {
        g->has_last = false;
    }
}

bool gw_report_should_send(gw_report_gate_t *g, int32_t value, uint32_t now_ms)
{
    if (g == NULL) {
        return false;
    }
    bool send = !g->has_last;
    if (!send) {
        int64_t d = (int64_t)value - (int64_t)g->last_value;
        if (d < 0) {
            d = -d;
        }
        if (d > 0 && d >= (int64_t)g->min_delta) {
            send = true;
        } else if (g->max_interval_ms != 0u && (uint32_t)(now_ms - g->last_time_ms) >= g->max_interval_ms) {
            send = true;
        }
    }
    if (send) {
        g->has_last = true;
        g->last_value = value;
        g->last_time_ms = now_ms;
    }
    return send;
}
