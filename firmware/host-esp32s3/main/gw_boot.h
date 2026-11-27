/* gw_boot.h - start-up banner and pure-logic self-test of the host image (gateway code, not vendor code). */
#ifndef GW_BOOT_H
#define GW_BOOT_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Run the fixed-vector smoke test of the logic in firmware/common on the target itself
 * (BTHome vector -> Matter units -> ventilation flag). Returns true when every step gives the
 * expected value. The real tests are the host unit tests (tests/unit); this only proves that the
 * code is linked into the image and behaves the same on the Xtensa target.
 */
bool gw_selftest(void);

/** Log IDF and application versions and the self-test result. Never aborts. */
void gw_boot_banner(void);

#ifdef __cplusplus
}
#endif

#endif /* GW_BOOT_H */
