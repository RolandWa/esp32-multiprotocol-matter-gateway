"""The pin map follows the KiCad schematic (docs/CODING_GUIDELINES.md section 3, AGENTS.md section 2 item 6).

hardware/kicad/gw.kicad_sch is the source of truth. This test exports its netlist with kicad-cli and checks, net by net, that
  * firmware/common/gw_pins.h carries the GPIO numbers of the schematic,
  * the ESP-IDF settings of both images (sdkconfig.defaults.gateway / sdkconfig.defaults.esp32c6) carry the same numbers,
  * the baud rate of the vendor code on both sides is still the one in gw_pins.h.
The rules that hold for any map (no duplicates, no USB/strapping pin, exposed pads) are in test_gw_pins.c.
"""
import glob
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import pytest

from conftest import REPO

SCH = os.path.join(REPO, "hardware", "kicad", "gw.kicad_sch")
HEADER = os.path.join(REPO, "firmware", "common", "gw_pins.h")
HOST_GW = os.path.join(REPO, "firmware", "host-esp32s3", "sdkconfig.defaults.gateway")
RCP_GW = os.path.join(REPO, "firmware", "rcp-esp32c6", "sdkconfig.defaults.esp32c6")


def _text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def header_values(path=HEADER):
    """GW_* macro name -> integer, for the plain '#define NAME number' lines."""
    values = {}
    for m in re.finditer(r"^#define\s+(GW_\w+)\s+(\d+)\b", _text(path), re.M):
        values[m.group(1)] = int(m.group(2))
    return values


def _kicad_cli():
    # the owner's GUI is KiCad 9: prefer its CLI, then whatever is on PATH, then KiCad 10
    candidates = [r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe", shutil.which("kicad-cli"),
                  r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


@pytest.fixture(scope="module")
def nets():
    """{net name without the leading '/': [(ref, pin number, pin function), ...]} from the real schematic."""
    cli = _kicad_cli()
    if cli is None:
        pytest.skip("kicad-cli not found")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "gw_netlist.xml")
        proc = subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                              capture_output=True, timeout=300)
        assert proc.returncode == 0, proc.stdout.decode(errors="replace") + proc.stderr.decode(errors="replace")
        root = ET.parse(out).getroot()
    result = {}
    for net in root.iter("net"):
        name = net.get("name").lstrip("/")
        result[name] = [(n.get("ref"), n.get("pin"), n.get("pinfunction") or "") for n in net.iter("node")]
    return result


def _gpio_on(nets, net, ref):
    """GPIO number of the pin of `ref` on `net` (from the pin function name, e.g. GPIO43_A6_D6_TX -> 43)."""
    nodes = [n for n in nets[net] if n[0] == ref]
    assert len(nodes) == 1, "%s: expected exactly one pin of %s, got %s" % (net, ref, nodes)
    m = re.match(r"GPIO(\d+)", nodes[0][2])
    assert m, "%s on %s is not a GPIO pin: %r" % (ref, net, nodes[0][2])
    return int(m.group(1))


# header macro -> (net, reference designator). U1 = XIAO ESP32-S3 (host), U2 = XIAO ESP32-C6 (RCP).
PIN_NETS = {
    "GW_S3_PIN_RCP_UART_TX": ("S3_TX_C6_RX", "U1"),
    "GW_S3_PIN_RCP_UART_RX": ("C6_TX_S3_RX", "U1"),
    "GW_S3_PIN_RCP_UART_RTS": ("S3_RTS_C6_CTS", "U1"),
    "GW_S3_PIN_RCP_UART_CTS": ("C6_RTS_S3_CTS", "U1"),
    "GW_S3_PIN_I2C_SDA": ("I2C_SDA", "U1"),
    "GW_S3_PIN_I2C_SCL": ("I2C_SCL", "U1"),
    "GW_S3_PIN_C6_EN_DRIVE": ("C6_EN_DRV", "U1"),
    "GW_S3_PIN_C6_BOOT_DRIVE": ("C6_BOOT_DRV", "U1"),
    "GW_C6_PIN_RCP_UART_TX": ("C6_TX_S3_RX", "U2"),
    "GW_C6_PIN_RCP_UART_RX": ("S3_TX_C6_RX", "U2"),
    "GW_C6_PIN_RCP_UART_RTS": ("C6_RTS_S3_CTS", "U2"),
    "GW_C6_PIN_RCP_UART_CTS": ("S3_RTS_C6_CTS", "U2"),
}


@pytest.mark.parametrize("macro", sorted(PIN_NETS))
def test_header_matches_the_schematic_net_by_net(nets, macro):
    net, ref = PIN_NETS[macro]
    assert header_values()[macro] == _gpio_on(nets, net, ref), "%s differs from net %s on %s in the schematic" % (macro, net, ref)


def test_c6_boot_and_enable_are_driven_by_the_s3_through_the_series_resistors(nets):
    # the C6 BOOT pad is GPIO9 (Seeed pinout); the netlist only names the pad "BOOT"
    boot = [n for n in nets["Net-(U2-BOOT)"] if n[0] == "U2"]
    assert boot and boot[0][2] == "BOOT"
    assert header_values()["GW_C6_PIN_BOOT"] == 9
    assert {n[0] for n in nets["Net-(U2-BOOT)"]} == {"R4", "U2"}
    assert {n[0] for n in nets["C6_BOOT_DRV"]} == {"R4", "U1"}
    assert {n[0] for n in nets["Net-(U2-CHIP_EN)"]} == {"R3", "U2"}
    assert {n[0] for n in nets["C6_EN_DRV"]} == {"R3", "U1"}


def test_the_link_nets_connect_exactly_the_two_modules(nets):
    for net in ("S3_TX_C6_RX", "C6_TX_S3_RX", "S3_RTS_C6_CTS", "C6_RTS_S3_CTS"):
        assert sorted(n[0] for n in nets[net]) == ["U1", "U2"], (net, nets[net])


def test_the_i2c_nets_go_to_the_sensor_connector_and_pullups(nets):
    assert sorted(n[0] for n in nets["I2C_SDA"]) == ["J2", "R1", "U1"]
    assert sorted(n[0] for n in nets["I2C_SCL"]) == ["J2", "R2", "U1"]


# ---------------------------------------------------------------- the images carry the same numbers (no schematic needed)

def _kconfig(path):
    return {m.group(1): m.group(2) for m in re.finditer(r"^CONFIG_(\w+)=(\S+)$", _text(path), re.M)}


def test_host_sdkconfig_pins_equal_the_header_with_the_vendor_naming():
    h, k = header_values(), _kconfig(HOST_GW)
    # vendor Kconfig names are from the RCP's side: PIN_TO_RCP_TX = pad wired to the RCP's TX = the S3's RX
    assert int(k["PIN_TO_RCP_TX"]) == h["GW_S3_PIN_RCP_UART_RX"]
    assert int(k["PIN_TO_RCP_RX"]) == h["GW_S3_PIN_RCP_UART_TX"]


def test_host_console_is_moved_off_uart0_because_the_link_uses_its_pads():
    k = _kconfig(HOST_GW)
    h = header_values()
    assert {h["GW_S3_PIN_RCP_UART_TX"], h["GW_S3_PIN_RCP_UART_RX"]} == {43, 44}   # UART0 default pads of the S3
    assert k.get("ESP_CONSOLE_USB_SERIAL_JTAG") == "y"


def test_rcp_sdkconfig_pins_equal_the_header():
    h, k = header_values(), _kconfig(RCP_GW)
    assert k["OPENTHREAD_UART_PIN_MANUAL"] == "y"
    assert int(k["OPENTHREAD_UART_RX_PIN"]) == h["GW_C6_PIN_RCP_UART_RX"]
    assert int(k["OPENTHREAD_UART_TX_PIN"]) == h["GW_C6_PIN_RCP_UART_TX"]


def test_vendor_code_still_uses_the_baud_rate_and_no_flow_control_assumed_in_the_header():
    baud = header_values()["GW_RCP_UART_BAUD"]
    host = _text(os.path.join(REPO, "firmware", "host-esp32s3", "main", "app_zboss.h"))
    rcp = _text(os.path.join(REPO, "firmware", "rcp-esp32c6", "main", "esp_ot_config.h"))
    for name, text in (("app_zboss.h", host), ("esp_ot_config.h", rcp)):
        assert re.search(r"\.baud_rate\s*=\s*%d\b" % baud, text), "%s no longer uses %d baud" % (name, baud)
        assert "UART_HW_FLOWCTRL_DISABLE" in text, "%s no longer disables hardware flow control" % name
    # the host link uses UART1 (UART0 stays the console peripheral)
    assert re.search(r"\.port\s*=\s*UART_NUM_%d\b" % header_values()["GW_S3_RCP_UART_PORT"], host)


def test_every_gpio_number_of_the_link_lives_only_in_the_header():
    """No second copy of the pin numbers in gateway-owned code (docs/CODING_GUIDELINES.md section 3)."""
    own = [os.path.join(REPO, "firmware", "host-esp32s3", "main", "gw_boot.c")] + \
          [p for p in glob.glob(os.path.join(REPO, "firmware", "common", "gw_*.c"))]
    for path in own:
        text = _text(path)
        assert not re.search(r"\bGPIO\s*\(?\s*\d+|gpio_num_t\s*\)\s*\d+|\.(rx|tx)_pin\s*=\s*\d+", text), path
