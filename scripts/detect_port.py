#!/usr/bin/env python3
"""List serial ports of Espressif USB devices (native USB-Serial/JTAG has VID 0x303A).

Both XIAO modules of this project (ESP32-S3 and ESP32-C6) enumerate with the same
VID/PID, so with two boards plugged in the port cannot be guessed from the VID:
identify each board by its USB serial number (the module's MAC) or by asking
esptool (`--chip-id`).  Record the serial numbers in docs/BUILD_AND_FLASH.md.

Usage:
    python scripts/detect_port.py                 # table of all matching ports
    python scripts/detect_port.py --last          # print only the highest COM port (old behaviour)
    python scripts/detect_port.py --serial 40:4C:CA:xx:xx:xx   # port of the board with this serial number
    python scripts/detect_port.py --chip-id       # ask esptool which chip sits on each port (slow, needs esptool)

Exit code 1 when nothing matches. Requires pyserial.
"""
import argparse
import subprocess
import sys

import serial.tools.list_ports

ESPRESSIF_VID = 0x303A


def find_ports(vid=ESPRESSIF_VID):
    ports = [p for p in serial.tools.list_ports.comports() if vid is None or p.vid == vid]
    return sorted(ports, key=lambda p: p.device)


def chip_of(port):
    """Return esptool's 'Chip is ...' line for a port, or '?'."""
    try:
        out = subprocess.run([sys.executable, "-m", "esptool", "-p", port, "chip-id"],
                             capture_output=True, text=True, timeout=30).stdout
        for line in out.splitlines():
            if line.startswith("Chip type:") or line.startswith("Chip is"):
                return line.split(":", 1)[-1].strip() if ":" in line else line
    except Exception:
        pass
    return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vid", type=lambda s: int(s, 0), default=ESPRESSIF_VID,
                    help="USB vendor id (default 0x303A; 0 = list every port)")
    ap.add_argument("--last", action="store_true", help="print only the last (highest) port")
    ap.add_argument("--serial", help="print the port whose USB serial number contains this text")
    ap.add_argument("--chip-id", action="store_true", help="query esptool for the chip type of every port")
    args = ap.parse_args()

    ports = find_ports(args.vid or None)
    if args.serial:
        ports = [p for p in ports if p.serial_number and args.serial.lower() in p.serial_number.lower()]
    if not ports:
        return 1
    if args.last:
        print(ports[-1].device)
        return 0
    if args.serial:
        print(ports[0].device)
        return 0

    for p in ports:
        row = [p.device, f"{p.vid:04X}:{p.pid:04X}" if p.vid else "-", p.serial_number or "-", p.description]
        if args.chip_id:
            row.append(chip_of(p.device))
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
