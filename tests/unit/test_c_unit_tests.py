"""Build and run the C unit tests (tests/unit/test_*.c) from pytest.

Uses a native gcc + make when available (Linux/CI), otherwise gcc inside WSL (Windows).
Skipped if neither exists. The C output is shown when a test fails.

Two guards beyond "exit code 0":
  * every RUN(test_x) line of every test file must have printed "ok" (catches a test that
    silently stopped running),
  * the sanitizer build (make san) must pass too.
"""
import glob
import os
import re
import shutil
import subprocess

import pytest

from conftest import UNIT_DIR


def _wsl_path(path):
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    return "/mnt/" + drive[0].lower() + rest.replace("\\", "/")


def _make(target):
    if shutil.which("gcc") and shutil.which("make"):
        cmd = ["make", "-C", UNIT_DIR, target]
    elif shutil.which("wsl"):
        cmd = ["wsl", "--", "make", "-C", _wsl_path(UNIT_DIR), target]
    else:
        pytest.skip("no gcc/make (native or WSL) available")
    proc = subprocess.run(cmd, capture_output=True, timeout=600)
    text = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").replace("\x00", "")
    if proc.returncode != 0 and re.search(r"gcc.*(not found|No such file)|make: not found", text):
        pytest.skip("gcc/make not usable in this environment")
    return proc.returncode, text


@pytest.fixture(scope="module")
def plain():
    return _make("test")


@pytest.fixture(scope="module")
def sanitized():
    return _make("san")


def test_c_tests_pass(plain):
    code, out = plain
    assert code == 0, out
    assert re.search(r"\d+ checks, 0 failures", out), out


def test_every_declared_test_ran_and_passed(plain):
    _code, out = plain
    declared = []
    for path in sorted(glob.glob(os.path.join(UNIT_DIR, "test_*.c"))):
        with open(path, encoding="utf-8") as f:
            declared += re.findall(r"^\s*RUN\((test_\w+)\);", f.read(), flags=re.M)
    ran = re.findall(r"^ok\s+(test_\w+)", out, flags=re.M)
    assert declared, "no RUN() entries found"
    assert sorted(ran) == sorted(declared), out


def test_c_tests_pass_under_asan_and_ubsan(sanitized):
    code, out = sanitized
    assert code == 0, out
    assert re.search(r"\d+ checks, 0 failures", out), out
