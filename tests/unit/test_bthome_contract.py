"""Cross-language contract test (docs/TESTING.md layer 4) for the BTHome v2 parser.

The C parser (firmware/common/gw_bthome.c, wrapped by tests/unit/tools/bthome_cli.c) and the independent Python
reference decoder (bthome_ref.py) must give identical results on
  * the examples printed in the BTHome specification,
  * thousands of generated valid packets (ascending object ids, random values),
  * the same packets damaged in every way the parser claims to handle (truncation, bit flips, junk, bad header).
"""
import os
import random
import re
import shutil
import subprocess

import pytest

import bthome_ref
from conftest import UNIT_DIR

CLI = os.path.join(UNIT_DIR, "bthome_cli")

# [bthome.io] examples; the expected lines are derived from the specification text, not from the C code
SPEC_EXAMPLES = [
    ("D2FC4002C40903BF13", "ST=0 T=2500 H=5055 P=- B=- V=- ID=- M=- TRIG=0 UNK=0"),    # 25.00 C, 50.55 %
    ("D2FC4002CA09", "ST=0 T=2506 H=- P=- B=- V=- ID=- M=- TRIG=0 UNK=0"),             # 25.06 C
    ("D2FC400161", "ST=0 T=- H=- P=- B=97 V=- ID=- M=- TRIG=0 UNK=0"),                 # 97 %
    ("D2FC4004138A01", "ST=0 T=- H=- P=100883 B=- V=- ID=- M=- TRIG=0 UNK=0"),         # 1008.83 hPa
    ("D2FC400C020C", "ST=0 T=- H=- P=- B=- V=3074 ID=- M=- TRIG=0 UNK=0"),             # 3.074 V
    ("D2FC402E23", "ST=0 T=- H=3500 P=- B=- V=- ID=- M=- TRIG=0 UNK=0"),               # 35 %
    ("D2FC40451101", "ST=0 T=2730 H=- P=- B=- V=- ID=- M=- TRIG=0 UNK=0"),             # 27.3 C
    ("D2FC400009", "ST=0 T=- H=- P=- B=- V=- ID=9 M=- TRIG=0 UNK=0"),                  # packet id 9
]


def _build():
    if shutil.which("gcc") and shutil.which("make"):
        cmd = ["make", "-C", UNIT_DIR, "bthome_cli"]
    elif shutil.which("wsl"):
        drive, rest = os.path.splitdrive(os.path.abspath(UNIT_DIR))
        cmd = ["wsl", "--", "make", "-C", "/mnt/" + drive[0].lower() + rest.replace("\\", "/"), "bthome_cli"]
    else:
        pytest.skip("no gcc/make (native or WSL) available")
    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").replace("\x00", "")
    if proc.returncode != 0 and re.search(r"gcc.*(not found|No such file)|make: not found", out):
        pytest.skip("gcc/make not usable in this environment")
    assert proc.returncode == 0, out


def _run_cli(lines):
    """Feed hex lines to the C helper, return its output lines."""
    if shutil.which("gcc") and shutil.which("make"):
        cmd = [CLI]
    else:
        drive, rest = os.path.splitdrive(os.path.abspath(CLI))
        cmd = ["wsl", "--", "/mnt/" + drive[0].lower() + rest.replace("\\", "/")]
    proc = subprocess.run(cmd, input=("\n".join(lines) + "\n").encode(), capture_output=True, timeout=300)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return proc.stdout.decode().split("\n")[:-1]


@pytest.fixture(scope="module")
def cli():
    _build()
    return _run_cli


DECODED_IDS = [0x00, 0x01, 0x02, 0x03, 0x04, 0x0C, 0x20, 0x2E, 0x45]


def _random_object_value(rng, n):
    return bytes(rng.randrange(256) for _ in range(n))


def _generate(rng):
    """One valid packet: header + objects with ascending ids, as the specification requires of senders."""
    info = 0x40 | (0x04 if rng.random() < 0.3 else 0)
    # the objects the gateway decodes appear often; other known objects are mixed in so that skipping by length is exercised
    wanted = {oid for oid in DECODED_IDS if rng.random() < 0.4}
    others = set(rng.sample(sorted(bthome_ref.LENGTHS), rng.randrange(0, 4)))
    ids = sorted(wanted | others)
    body = bytearray()
    for oid in ids:
        body.append(oid)
        body += _random_object_value(rng, bthome_ref.LENGTHS[oid])
    if rng.random() < 0.15:                       # an object id this parser does not know ends the parse
        body += bytes([rng.choice([0x07, 0x10, 0x53, 0x54, 0xF0, 0xFF])]) + _random_object_value(rng, 4)
    return bytes([0xD2, 0xFC, info]) + bytes(body)


def _damage(rng, pkt):
    kind = rng.randrange(6)
    p = bytearray(pkt)
    if kind == 0 and len(p) > 1:
        return bytes(p[:rng.randrange(len(p))])                   # truncate anywhere
    if kind == 1 and p:
        p[rng.randrange(len(p))] ^= 1 << rng.randrange(8)         # flip one bit
        return bytes(p)
    if kind == 2:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 12)))  # junk
    if kind == 3 and len(p) > 2:
        p[2] = rng.randrange(256)                                 # random device-info byte
        return bytes(p)
    if kind == 4 and len(p) > 1:
        p[rng.randrange(2)] = rng.randrange(256)                  # corrupt the UUID
        return bytes(p)
    return bytes(p) + _random_object_value(rng, rng.randrange(1, 4))  # trailing garbage


def test_spec_examples_python_reference(cli):
    for hexs, expected in SPEC_EXAMPLES:
        assert bthome_ref.decode(bytes.fromhex(hexs)) == expected, hexs


def test_spec_examples_c_parser(cli):
    got = cli([h for h, _ in SPEC_EXAMPLES])
    assert got == [e for _, e in SPEC_EXAMPLES]


def test_c_and_python_agree_on_generated_and_damaged_packets(cli):
    rng = random.Random(20261127)
    packets = []
    for _ in range(2500):
        valid = _generate(rng)
        packets.append(valid)
        packets.append(_damage(rng, valid))
    packets += [b"", b"\xd2", b"\xd2\xfc", b"\xd2\xfc\x40", b"\xd2\xfc\x41", b"\xd2\xfc\x20\x01\x61"]
    got = cli([p.hex() for p in packets])
    assert len(got) == len(packets)
    for pkt, line in zip(packets, got):
        assert line == bthome_ref.decode(pkt), pkt.hex()


def test_generated_packets_are_mostly_valid_so_the_comparison_means_something(cli):
    """Guard against a generator that only produces rejected packets (which would make agreement trivial)."""
    rng = random.Random(7)
    packets = [_generate(rng) for _ in range(500)]
    results = [bthome_ref.decode(p) for p in packets]
    ok = sum(1 for r in results if r.startswith("ST=0"))
    assert ok == len(packets)
    for field in ("T", "H", "P", "B", "V", "ID", "M"):
        seen = sum(1 for r in results if re.search(r" %s=-?\d" % field, r))
        assert seen >= 100, "field %s decoded in only %d of %d generated packets" % (field, seen, len(packets))
    assert sum(1 for r in results if "UNK=1" in r) >= 30
    assert sum(1 for r in results if "TRIG=1" in r) >= 100


def test_null_pointer_is_rejected_by_the_c_parser(cli):
    assert cli(["NULL"]) == ["ST=%d" % bthome_ref.ARG]
