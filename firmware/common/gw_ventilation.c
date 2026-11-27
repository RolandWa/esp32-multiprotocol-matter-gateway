#include "gw_ventilation.h"

#include <stddef.h>

#include "gw_units.h" /* GW_IAQ_MAX */

void gw_vent_default_cfg(gw_vent_cfg_t *cfg)
{
    if (cfg == NULL) {
        return;
    }
    cfg->on_above = GW_VENT_DEFAULT_ON_ABOVE;
    cfg->off_below = GW_VENT_DEFAULT_OFF_BELOW;
    cfg->min_accuracy = GW_VENT_DEFAULT_MIN_ACCURACY;
}

bool gw_vent_init(gw_vent_t *v, const gw_vent_cfg_t *cfg)
{
    if (v == NULL || cfg == NULL || cfg->off_below > cfg->on_above) {
        return false;
    }
    v->cfg = *cfg;
    v->active = false;
    return true;
}

bool gw_vent_update(gw_vent_t *v, uint16_t iaq, uint8_t accuracy)
{
    if (v == NULL) {
        return false;
    }
    if (accuracy < v->cfg.min_accuracy || iaq > GW_IAQ_MAX) {
        return v->active; /* unreliable sample: hold */
    }
    if (iaq > v->cfg.on_above) {
        v->active = true;
    } else if (iaq < v->cfg.off_below) {
        v->active = false;
    }
    return v->active;
}
