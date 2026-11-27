# Host unit tests for the pure-C parts of the firmware (no ESP-IDF needed).
#
#   make -C tests/unit test        # build + run every test_*.c   (gcc; on Windows run it in WSL)
#   make -C tests/unit san         # same with AddressSanitizer + UndefinedBehaviorSanitizer
#   make -C tests/unit clean
#
# Convention: tests/unit/test_<name>.c is linked with ALL .c files found in PURE_DIRS.
# Put only IDF-free logic in those directories (see docs/CODING_GUIDELINES.md); anything that
# includes an ESP-IDF header cannot be compiled here.

CC       ?= gcc
CFLAGS   ?= -std=c99 -O1 -g -Wall -Wextra -Werror -pedantic
PURE_DIRS ?= ../../firmware/common
INCLUDES := -I. $(addprefix -I,$(PURE_DIRS))
PURE_SRC := $(foreach d,$(PURE_DIRS),$(wildcard $(d)/*.c))
TESTS    := $(basename $(wildcard test_*.c))
HEADERS  := $(wildcard *.h) $(foreach d,$(PURE_DIRS),$(wildcard $(d)/*.h))

all: $(TESTS)

$(TESTS): %: %.c $(PURE_SRC) $(HEADERS)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $< $(PURE_SRC) -lm

# Test helper used by test_bthome_contract.py: the C BTHome parser behind a stdin/stdout interface (not a unit test).
bthome_cli: tools/bthome_cli.c $(PURE_SRC) $(HEADERS)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $< $(PURE_SRC) -lm

.PHONY: test san clean bthome_cli
test: all
	@fail=0; for t in $(TESTS); do echo "== $$t"; ./$$t || fail=1; done; exit $$fail

san: CFLAGS += -fsanitize=address,undefined -fno-sanitize-recover=all
san: clean test

clean:
	rm -f $(TESTS) $(addsuffix .exe,$(TESTS)) bthome_cli bthome_cli.exe
