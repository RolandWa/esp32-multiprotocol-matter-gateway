/**
 * gw_ventilation.h - "time to ventilate" flag with hysteresis (pure C99).
 *
 * Requirement (project_specification_and_requirements.md, "Logika oceny potrzeby wietrzenia"):
 * the flag turns ON when IAQ > 150 and turns OFF again only when IAQ < 110, so it does not
 * flap around one threshold. Between 110 and 150 the previous state is kept.
 *
 * Added here (NOT in the requirements, a safe default the owner can change): while the BSEC
 * accuracy is below `min_accuracy` (default 1; accuracy 0 = "stabilising", the IAQ value is
 * not meaningful) the flag is HELD - it is neither raised nor cleared by an unreliable value.
 * IAQ values above 500 are invalid and ignored the same way.
 */
#ifndef GW_VENTILATION_H
#define GW_VENTILATION_H

#include <stdbool.h>
#include <stdint.h>

#define GW_VENT_DEFAULT_ON_ABOVE 150u
#define GW_VENT_DEFAULT_OFF_BELOW 110u
#define GW_VENT_DEFAULT_MIN_ACCURACY 1u

typedef struct {
    uint16_t on_above;    /* flag raised when iaq >  on_above  */
    uint16_t off_below;   /* flag cleared when iaq < off_below (must be <= on_above) */
    uint8_t min_accuracy; /* BSEC accuracy needed before a value may change the flag */
} gw_vent_cfg_t;

typedef struct {
    gw_vent_cfg_t cfg;
    bool active;
} gw_vent_t;

/** Fill `cfg` with the defaults above. */
void gw_vent_default_cfg(gw_vent_cfg_t *cfg);

/** Returns false (and leaves `v` untouched) for a NULL pointer or off_below > on_above. */
bool gw_vent_init(gw_vent_t *v, const gw_vent_cfg_t *cfg);

/** Feed one IAQ sample; returns the (possibly updated) flag. */
bool gw_vent_update(gw_vent_t *v, uint16_t iaq, uint8_t accuracy);

#endif /* GW_VENTILATION_H */
