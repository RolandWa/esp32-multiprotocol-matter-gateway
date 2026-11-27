"""Smoke tests for the helper scripts that do not need hardware."""
import os
import shutil
import subprocess
import sys

import pytest

from conftest import REPO, SCRIPTS_DIR

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="batch files need Windows")


def test_detect_port_exits_1_when_nothing_matches():
    pytest.importorskip("serial", reason="pyserial not installed")
    r = subprocess.run([sys.executable, f"{SCRIPTS_DIR}/detect_port.py", "--vid", "0x0001"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and r.stdout == ""


@windows_only
@pytest.mark.parametrize("chip, offset", [
    ("esp32s3", "0x0"), ("esp32c6", "0x0"), ("esp32c3", "0x0"), ("esp32h2", "0x0"),
    ("esp32", "0x1000"), ("esp32s2", "0x1000"),
])
def test_flash_bat_uses_the_right_offset_per_chip(tmp_path, chip, offset):
    image = tmp_path / "fw.bin"
    image.write_bytes(b"\x00" * 16)
    env = dict(os.environ, DRY_RUN="1", PYTHON="python")
    r = subprocess.run(["cmd", "/c", os.path.join(REPO, "scripts", "flash.bat"), chip, "COM99", str(image)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"--chip {chip}" in r.stdout and "-p COM99" in r.stdout
    assert f"write-flash {offset} " in r.stdout


@windows_only
def test_flash_bat_requires_chip_port_and_image(tmp_path):
    env = dict(os.environ, DRY_RUN="1")
    bat = os.path.join(REPO, "scripts", "flash.bat")
    assert subprocess.run(["cmd", "/c", bat], capture_output=True, env=env).returncode == 2
    assert subprocess.run(["cmd", "/c", bat, "esp32s3"], capture_output=True, env=env).returncode == 2
    assert subprocess.run(["cmd", "/c", bat, "esp32s3", "COM9"], capture_output=True, env=env).returncode == 2
    missing = subprocess.run(["cmd", "/c", bat, "esp32s3", "COM9", str(tmp_path / "nope.bin")],
                             capture_output=True, text=True, env=env)
    assert missing.returncode == 1 and "image not found" in missing.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_wsl_idf_shell_syntax_is_valid():
    # `bash` on a Windows PATH is usually WSL's bash, which does not understand C:\ paths:
    # run it with the scripts dir as cwd and a relative file name (works for WSL and Git Bash).
    r = subprocess.run(["bash", "-n", "wsl_idf.sh"], cwd=SCRIPTS_DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert b"\r\n" not in open(os.path.join(SCRIPTS_DIR, "wsl_idf.sh"), "rb").read(), \
        "wsl_idf.sh must keep LF line endings (a CRLF checkout breaks bash)"
