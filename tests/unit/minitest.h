/**
 * minitest.h - 40-line unit-test harness for host-side C tests (no dependencies).
 *
 * Usage in tests/unit/test_<module>.c:
 *
 *     #include "minitest.h"
 *     #include "my_module.h"
 *
 *     static void test_something(void) { CHECK_EQ(my_add(2, 2), 4); CHECK(my_flag()); }
 *
 *     int main(void) {
 *         RUN(test_something);
 *         return MT_SUMMARY();
 *     }
 *
 * The runner prints "ok   <name>" / "FAIL <name>" per test and a final
 * "<N> checks, <M> failures" line; tests/unit/test_c_unit_tests.py relies on that format.
 * Every RUN(...) line must stay on its own line (the pytest runner counts them).
 */
#ifndef MINITEST_H
#define MINITEST_H

#include <stdio.h>

static int mt_checks = 0;
static int mt_failures = 0;
static const char *mt_current = "";

#define CHECK(cond)                                                                    \
    do {                                                                               \
        mt_checks++;                                                                   \
        if (!(cond)) {                                                                 \
            mt_failures++;                                                             \
            printf("  FAIL [%s] %s:%d: %s\n", mt_current, __FILE__, __LINE__, #cond);  \
        }                                                                              \
    } while (0)

/* Compares as long long and prints both values on failure. */
#define CHECK_EQ(actual, expected)                                                     \
    do {                                                                               \
        long long a_ = (long long)(actual), e_ = (long long)(expected);                \
        mt_checks++;                                                                   \
        if (a_ != e_) {                                                                \
            mt_failures++;                                                             \
            printf("  FAIL [%s] %s:%d: %s == %lld, expected %lld\n", mt_current,       \
                   __FILE__, __LINE__, #actual, a_, e_);                               \
        }                                                                              \
    } while (0)

#define RUN(fn)                                                                        \
    do {                                                                               \
        int before_ = mt_failures;                                                     \
        mt_current = #fn;                                                              \
        fn();                                                                          \
        printf("%s %s\n", (mt_failures == before_) ? "ok  " : "FAIL", #fn);            \
    } while (0)

#define MT_SUMMARY()                                                                   \
    (printf("\n%d checks, %d failures\n", mt_checks, mt_failures), mt_failures ? 1 : 0)

#endif /* MINITEST_H */
