"""Independent reference decoder for BTHome v2 service data (https://bthome.io/format/, read 2026-11-27).

Written from the specification, NOT from firmware/common/gw_bthome.c, so that
test_bthome_contract.py compares two separate implementations. The semantic choices that the spec leaves open
are the project's decisions and are mirrored here on purpose (and documented in gw_bthome.h):
  * encrypted packets are rejected (no AES-CCM yet),
  * parsing stops at the first object id that is not in the table,
  * a repeated object: the later one wins,
  * object 0x45 (0.1 degC) is scaled to 0.01 degC and saturated to int16; 0x2E (1 %) is scaled to 0.01 %.
"""

OK, ARG, TOO_SHORT, UUID, VERSION, ENCRYPTED, MALFORMED = range(7)

# object id -> data length in bytes (only fixed-length objects that the spec table lists)
LENGTHS = {
    0x00: 1, 0x01: 1, 0x02: 2, 0x03: 2, 0x04: 3, 0x05: 3, 0x06: 2, 0x08: 2, 0x09: 1, 0x0A: 3, 0x0B: 3,
    0x0C: 2, 0x0D: 2, 0x0E: 2, 0x12: 2, 0x13: 2, 0x14: 2, 0x20: 1, 0x2E: 1, 0x3D: 2, 0x3E: 4, 0x40: 2,
    0x42: 3, 0x43: 2, 0x45: 2, 0x46: 1, 0x48: 2, 0x49: 2, 0x4A: 2, 0x4B: 3, 0x4E: 4, 0x4F: 4, 0x51: 2,
    0x52: 2, 0x56: 2, 0x57: 1, 0x58: 1, 0x59: 1, 0x5A: 2, 0x5B: 4, 0x5F: 2, 0x60: 1, 0x62: 4, 0x63: 4,
    0x64: 1, 0x65: 1, 0x67: 1,
}


def _le(b, signed=False):
    return int.from_bytes(bytes(b), "little", signed=signed)


def decode(data):
    """Return the result line that bthome_cli prints for `data` (bytes)."""
    if len(data) < 3:
        return "ST=%d" % TOO_SHORT
    if _le(data[0:2]) != 0xFCD2:
        return "ST=%d" % UUID
    info = data[2]
    if (info >> 5) != 2:
        return "ST=%d" % VERSION
    if info & 1:
        return "ST=%d" % ENCRYPTED

    r = {"T": "-", "H": "-", "P": "-", "B": "-", "V": "-", "ID": "-", "M": "-"}
    unk = 0
    pos = 3
    while pos < len(data):
        oid = data[pos]
        n = LENGTHS.get(oid)
        if n is None:
            unk = 1
            break
        if pos + 1 + n > len(data):
            return "ST=%d" % MALFORMED
        v = data[pos + 1:pos + 1 + n]
        if oid == 0x00:
            r["ID"] = v[0]
        elif oid == 0x01:
            r["B"] = v[0]
        elif oid == 0x02:
            r["T"] = _le(v, signed=True)
        elif oid == 0x45:
            r["T"] = max(-32768, min(32767, _le(v, signed=True) * 10))
        elif oid == 0x03:
            r["H"] = _le(v)
        elif oid == 0x2E:
            r["H"] = v[0] * 100
        elif oid == 0x04:
            r["P"] = _le(v)
        elif oid == 0x0C:
            r["V"] = _le(v)
        elif oid == 0x20:
            r["M"] = 1 if v[0] else 0
        pos += 1 + n

    return "ST=%d T=%s H=%s P=%s B=%s V=%s ID=%s M=%s TRIG=%d UNK=%d" % (
        OK, r["T"], r["H"], r["P"], r["B"], r["V"], r["ID"], r["M"], 1 if info & 4 else 0, unk)
