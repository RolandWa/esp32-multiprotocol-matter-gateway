#include "gw_boot.h"

#include <stdint.h>

#include "esp_app_desc.h"
#include "esp_log.h"
#include "esp_system.h"

#include "gw_bthome.h"
#include "gw_units.h"
#include "gw_ventilation.h"

static const char *TAG = "gw_boot";

bool gw_selftest(void)
{
    /* bthome.io example: D2FC 40 02C409 03BF13 = 25.00 degC, 50.55 % */
    static const uint8_t vector[] = {0xD2, 0xFC, 0x40, 0x02, 0xC4, 0x09, 0x03, 0xBF, 0x13};
    gw_bthome_data_t d;
    int16_t t = 0;
    uint16_t h = 0;
    gw_vent_t vent;
    gw_vent_cfg_t cfg;

    if (gw_bthome_parse(vector, sizeof vector, &d) != GW_BTHOME_OK || !d.has_temperature || !d.has_humidity) {
        return false;
    }
    if (!gw_to_matter_temperature(d.temperature_c100, &t) || t != 2500) {
        return false;
    }
    if (!gw_to_matter_humidity(d.humidity_pct100, &h) || h != 5055) {
        return false;
    }

    gw_vent_default_cfg(&cfg);
    if (!gw_vent_init(&vent, &cfg)) {
        return false;
    }
    return !gw_vent_update(&vent, 150, 3) && gw_vent_update(&vent, 151, 3);
}

void gw_boot_banner(void)
{
    const esp_app_desc_t *app = esp_app_get_description();
    ESP_LOGI(TAG, "gateway host: app %s, project %s, built %s %s", app->version, app->project_name, app->date, app->time);
    ESP_LOGI(TAG, "ESP-IDF %s", esp_get_idf_version());
    if (gw_selftest()) {
        ESP_LOGI(TAG, "logic self-test: ok");
    } else {
        ESP_LOGE(TAG, "logic self-test FAILED - the pure-logic modules misbehave on this target");
    }
}
