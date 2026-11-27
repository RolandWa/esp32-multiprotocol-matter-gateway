/* bthome_cli - test helper, NOT part of the firmware.
 *
 * Reads one hex-encoded BTHome service-data payload per line from stdin (starting with the UUID bytes,
 * as gw_bthome_parse expects) and prints one result line per input:
 *
 *   ST=<status> [T=<c100|-> H=<pct100|-> P=<pa|-> B=<pct|-> V=<mv|-> ID=<id|-> M=<-|0|1> TRIG=<0|1> UNK=<0|1>]
 *
 * tests/unit/test_bthome_contract.py feeds it the same packets as the independent Python reference
 * decoder (bthome_ref.py) and compares the lines. An empty line is the empty payload; "NULL" is a NULL pointer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gw_bthome.h"

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(void)
{
    char line[4096];
    while (fgets(line, sizeof line, stdin) != NULL) {
        uint8_t buf[2048];
        size_t n = 0;
        size_t len = strcspn(line, "\r\n");
        gw_bthome_data_t d;
        gw_bthome_status_t st;
        line[len] = '\0';

        if (strcmp(line, "NULL") == 0) {
            st = gw_bthome_parse(NULL, 4, &d);
        } else {
            for (size_t i = 0; i + 1 < len && n < sizeof buf; i += 2) {
                int hi = hexval(line[i]), lo = hexval(line[i + 1]);
                if (hi < 0 || lo < 0) {
                    fprintf(stderr, "bad hex: %s\n", line);
                    return 2;
                }
                buf[n++] = (uint8_t)(hi * 16 + lo);
            }
            st = gw_bthome_parse(buf, n, &d);
        }

        printf("ST=%d", (int)st);
        if (st == GW_BTHOME_OK) {
            if (d.has_temperature) printf(" T=%d", d.temperature_c100); else printf(" T=-");
            if (d.has_humidity)    printf(" H=%u", (unsigned)d.humidity_pct100); else printf(" H=-");
            if (d.has_pressure)    printf(" P=%lu", (unsigned long)d.pressure_pa); else printf(" P=-");
            if (d.has_battery)     printf(" B=%u", (unsigned)d.battery_pct); else printf(" B=-");
            if (d.has_voltage)     printf(" V=%u", (unsigned)d.voltage_mv); else printf(" V=-");
            if (d.has_packet_id)   printf(" ID=%u", (unsigned)d.packet_id); else printf(" ID=-");
            if (d.has_moisture)    printf(" M=%d", d.moisture_wet ? 1 : 0); else printf(" M=-");
            printf(" TRIG=%d UNK=%d", d.trigger_based ? 1 : 0, d.stopped_at_unknown ? 1 : 0);
        }
        printf("\n");
    }
    return 0;
}
