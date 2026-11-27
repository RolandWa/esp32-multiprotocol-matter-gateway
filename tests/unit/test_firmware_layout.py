"""Regression tests for the structure of firmware/ (no ESP-IDF, no hardware needed).

What they protect:
  * firmware/common stays pure C (no ESP-IDF include), is fully listed in its IDF CMakeLists, and every module has a unit test;
  * files copied from Espressif's examples stay byte-identical (hash manifests) - the gateway's own changes are an explicit,
    reviewed list, so an accidental edit of vendor code or a new unclassified file fails here;
  * the gateway-specific RCP setting is still there;
  * the partition tables are sane (no overlap, alignment, fit in flash, OTA pair);
  * a built image, when one exists in dist/, still fits its slot with a safety margin.
"""
import glob
import hashlib
import os
import re

import pytest

from conftest import REPO

FW = os.path.join(REPO, "firmware")
COMMON = os.path.join(FW, "common")
UNIT = os.path.join(REPO, "tests", "unit")

# Files in each project that are NOT vendor code and not in the manifest (the "gateway's own" list).
GATEWAY_OWN = {
    "host-esp32s3": {"CMakeLists.txt", "main/app_main.cpp", "main/gw_boot.c", "main/gw_boot.h",
                     "sdkconfig.defaults.gateway", "README.md", "VENDOR_BASELINE.sha256", "dependencies.lock"},
    "rcp-esp32c6": {"sdkconfig.defaults.esp32c6", "README.md", "VENDOR_BASELINE.sha256", "dependencies.lock"},
}
PROJECTS = sorted(GATEWAY_OWN)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _project_files(project):
    root = os.path.join(FW, project)
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("dist", "build", "managed_components", "__pycache__")]
        for name in filenames:
            if name in ("sdkconfig", "sdkconfig.old"):
                continue
            found.add(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    return found


def _manifest(project):
    entries = {}
    with open(os.path.join(FW, project, "VENDOR_BASELINE.sha256"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digest, name = line.split(None, 1)
            entries[name.strip()] = digest
    return entries


def _sha256_lf(path):
    return hashlib.sha256(_read(path).replace(b"\r\n", b"\n")).hexdigest()


# ---------------------------------------------------------------- firmware/common

def test_common_has_no_esp_idf_includes():
    bad = re.compile(r'#\s*include\s*[<"](esp_|freertos|driver/|soc/|hal/|nvs|sdkconfig|lwip|bt/|esp-)')
    offenders = []
    for path in glob.glob(os.path.join(COMMON, "*.[ch]")):
        for n, line in enumerate(_read(path).decode("utf-8").splitlines(), 1):
            if bad.search(line):
                offenders.append("%s:%d: %s" % (os.path.basename(path), n, line.strip()))
    assert not offenders, "ESP-IDF include in the pure-C directory:\n" + "\n".join(offenders)


def test_common_cmakelists_lists_every_source_file():
    text = _read(os.path.join(COMMON, "CMakeLists.txt")).decode("utf-8")
    listed = set(re.findall(r'"([\w.-]+\.c)"', text))
    on_disk = {os.path.basename(p) for p in glob.glob(os.path.join(COMMON, "*.c"))}
    assert on_disk, "no .c files in firmware/common"
    assert listed == on_disk, "CMakeLists SRCS differs from the files on disk: %s" % sorted(listed ^ on_disk)


def test_every_common_module_has_a_unit_test_and_vice_versa():
    # a module is a gw_*.h header; header-only modules (gw_pins.h) have no .c file
    modules = {os.path.basename(p)[:-2] for p in glob.glob(os.path.join(COMMON, "*.h"))}
    tests = {os.path.basename(p)[len("test_"):-2] for p in glob.glob(os.path.join(UNIT, "test_*.c"))}
    assert modules - tests == set(), "modules without a unit test: %s" % sorted(modules - tests)
    assert tests - modules == set(), "unit tests without a module: %s" % sorted(tests - modules)


def test_every_common_module_has_a_header_with_the_gw_prefix():
    for path in glob.glob(os.path.join(COMMON, "*.[ch]")):
        base = os.path.basename(path)[:-2]
        assert base.startswith("gw_"), "public modules of common/ carry the gw_ prefix: %s" % base
        assert os.path.exists(os.path.join(COMMON, base + ".h")), base


# ---------------------------------------------------------------- vendor baselines

@pytest.mark.parametrize("project", PROJECTS)
def test_vendor_files_are_byte_identical_to_the_baseline(project):
    entries = _manifest(project)
    assert entries, "empty manifest"
    changed = []
    for name, digest in entries.items():
        path = os.path.join(FW, project, name)
        assert os.path.exists(path), "vendor file missing: %s/%s" % (project, name)
        if _sha256_lf(path) != digest:
            changed.append(name)
    assert not changed, ("vendor file(s) of %s were edited: %s. If intended, move the file to the gateway's own list "
                         "(GATEWAY_OWN here, README.md of the project) and drop it from VENDOR_BASELINE.sha256." % (project, changed))


@pytest.mark.parametrize("project", PROJECTS)
def test_every_project_file_is_classified_as_vendor_or_gateway_own(project):
    classified = set(_manifest(project)) | GATEWAY_OWN[project]
    unknown = _project_files(project) - classified
    assert not unknown, "unclassified file(s) in %s: %s (add to GATEWAY_OWN or the manifest)" % (project, sorted(unknown))
    missing = GATEWAY_OWN[project] - _project_files(project)
    assert not missing, "listed gateway files that do not exist in %s: %s" % (project, sorted(missing))


@pytest.mark.parametrize("project", PROJECTS)
def test_project_readme_documents_its_provenance(project):
    text = _read(os.path.join(FW, project, "README.md")).decode("utf-8")
    assert "## References" in text
    assert "VENDOR_BASELINE.sha256" in text
    assert re.search(r"v6\.0\.2|release/v1\.6\.1", text)


# ---------------------------------------------------------------- gateway-specific configuration

def test_rcp_keeps_the_ncp_vendor_hook_and_stays_an_rcp():
    gw = _read(os.path.join(FW, "rcp-esp32c6", "sdkconfig.defaults.esp32c6")).decode("utf-8")
    vendor = _read(os.path.join(FW, "rcp-esp32c6", "sdkconfig.defaults")).decode("utf-8")
    assert re.search(r"^CONFIG_OPENTHREAD_NCP_VENDOR_HOOK=y$", gw, re.M)
    assert re.search(r"^CONFIG_OPENTHREAD_RADIO=y$", vendor, re.M)
    assert not re.search(r"^CONFIG_OPENTHREAD_FTD=y", vendor, re.M)


def test_host_cmake_wires_in_common_and_keeps_the_project_name():
    text = _read(os.path.join(FW, "host-esp32s3", "CMakeLists.txt")).decode("utf-8")
    assert re.search(r'"\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./common"', text)
    assert re.search(r"^project\(gateway_host\)", text, re.M)


def test_host_cmake_loads_the_gateway_overrides_after_the_vendor_defaults():
    text = _read(os.path.join(FW, "host-esp32s3", "CMakeLists.txt")).decode("utf-8")
    assert len(re.findall(r"SDKCONFIG_DEFAULTS", text)) == 1, "SDKCONFIG_DEFAULTS must be set exactly once"
    m = re.search(r'^set\(SDKCONFIG_DEFAULTS "([^"]+)"\)', text, re.M)
    assert m, "SDKCONFIG_DEFAULTS is not set in the host CMakeLists.txt"
    files = m.group(1).split(";")
    assert files == ["sdkconfig.defaults", "sdkconfig.defaults.gateway"], files
    # it must be set before project.cmake is included, otherwise IDF has already read the default value
    assert text.index("SDKCONFIG_DEFAULTS") < text.index("include($ENV{IDF_PATH}/tools/cmake/project.cmake)")


def test_host_main_still_calls_the_boot_banner():
    text = _read(os.path.join(FW, "host-esp32s3", "main", "app_main.cpp")).decode("utf-8")
    assert '#include "gw_boot.h"' in text
    assert len(re.findall(r"^\s*gw_boot_banner\(\);", text, re.M)) == 1


# ---------------------------------------------------------------- partition tables

def parse_size(text):
    text = text.strip()
    mult = {"K": 1024, "M": 1024 * 1024}.get(text[-1:].upper(), 1)
    return int(text[:-1] if mult != 1 else text, 0) * mult


def align_up(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def parse_partitions(csv_text, table_offset=0x8000):
    """Lay out an ESP-IDF partition CSV with the IDF rules: data 4 KB aligned, app 64 KB aligned, blank offsets follow."""
    parts = []
    cursor = table_offset + 0x1000
    for raw in csv_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, ptype, subtype, offset, size = [f.strip() for f in line.split(",")[:5]]
        is_app = ptype.lower() in ("app", "0", "0x0", "0x00")
        align = 0x10000 if is_app else 0x1000
        off = parse_size(offset) if offset else align_up(cursor, align)
        length = parse_size(size)
        parts.append({"name": name, "type": ptype, "subtype": subtype, "app": is_app, "offset": off, "size": length,
                      "explicit": bool(offset)})
        cursor = off + length
    return parts


def check_partitions(parts, flash_size, table_offset=0x8000):
    """Return a list of problems (empty = fine)."""
    problems = []
    ordered = sorted(parts, key=lambda p: p["offset"])
    for p in ordered:
        align = 0x10000 if p["app"] else 0x1000
        if p["offset"] % align:
            problems.append("%s offset 0x%X not aligned to 0x%X" % (p["name"], p["offset"], align))
        if p["offset"] < table_offset + 0x1000:
            problems.append("%s starts inside the bootloader/partition table area" % p["name"])
        if p["size"] <= 0:
            problems.append("%s has no size" % p["name"])
    for a, b in zip(ordered, ordered[1:]):
        if a["offset"] + a["size"] > b["offset"]:
            problems.append("%s overlaps %s" % (a["name"], b["name"]))
    if ordered and ordered[-1]["offset"] + ordered[-1]["size"] > flash_size:
        problems.append("table ends at 0x%X, beyond the %d-byte flash" % (ordered[-1]["offset"] + ordered[-1]["size"], flash_size))
    ota = [p for p in parts if p["subtype"].startswith("ota_") and p["app"]]
    if ota:
        if len({p["size"] for p in ota}) != 1:
            problems.append("OTA slots differ in size")
        if len(ota) < 2:
            problems.append("fewer than two OTA slots")
        if not [p for p in parts if p["subtype"] == "ota" and not p["app"]]:
            problems.append("OTA slots without an otadata partition")
    return problems


def flash_size_of(project):
    size = 2  # IDF default
    for path in glob.glob(os.path.join(FW, project, "sdkconfig.defaults*")):
        m = re.search(r"^CONFIG_ESPTOOLPY_FLASHSIZE_(\d+)MB=y", _read(path).decode("utf-8"), re.M)
        if m:
            size = int(m.group(1))
    return size * 1024 * 1024


@pytest.mark.parametrize("project", PROJECTS)
def test_partition_table_is_sane(project):
    text = _read(os.path.join(FW, project, "partitions.csv")).decode("utf-8")
    parts = parse_partitions(text)
    assert parts
    assert check_partitions(parts, flash_size_of(project)) == []


def test_host_partition_layout_matches_what_the_build_reported():
    # flasher_args of the 2026-11-27 build: otadata 0x1f000, ota_0 0x30000 (verifies the layout rules used above)
    parts = {p["name"]: p for p in parse_partitions(_read(os.path.join(FW, "host-esp32s3", "partitions.csv")).decode("utf-8"))}
    assert parts["otadata"]["offset"] == 0x1F000
    assert parts["ota_0"]["offset"] == 0x30000
    assert parts["ota_0"]["size"] == 0x1D0000
    assert parts["ota_1"]["offset"] == 0x200000


def test_partition_checker_detects_the_faults_it_claims_to():
    flash = 4 * 1024 * 1024
    ok = "nvs,data,nvs,0x9000,0x6000\notadata,data,ota,,0x2000\nota_0,app,ota_0,,1M\nota_1,app,ota_1,,1M\n"
    assert check_partitions(parse_partitions(ok), flash) == []

    overlap = "nvs,data,nvs,0x9000,0x6000\nphy,data,phy,0xA000,0x1000\n"
    assert any("overlaps" in p for p in check_partitions(parse_partitions(overlap), flash))

    unaligned_app = "nvs,data,nvs,0x9000,0x6000\nfactory,app,factory,0x11000,1M\n"
    assert any("not aligned" in p for p in check_partitions(parse_partitions(unaligned_app), flash))

    too_big = "nvs,data,nvs,0x9000,0x6000\nfactory,app,factory,0x10000,4M\n"
    assert any("beyond" in p for p in check_partitions(parse_partitions(too_big), flash))

    unequal = ok.replace("ota_1,app,ota_1,,1M", "ota_1,app,ota_1,,512K")
    assert any("differ" in p for p in check_partitions(parse_partitions(unequal), flash))

    no_otadata = "nvs,data,nvs,0x9000,0x6000\nota_0,app,ota_0,,1M\nota_1,app,ota_1,,1M\n"
    assert any("otadata" in p for p in check_partitions(parse_partitions(no_otadata), flash))

    in_table = "nvs,data,nvs,0x8000,0x6000\n"
    assert any("bootloader" in p for p in check_partitions(parse_partitions(in_table), flash))


# ---------------------------------------------------------------- built images (only when a build exists)

MIN_FREE_PERCENT = 2.0   # the host app had 3.0 % free on 2026-11-27; below 2 % the next feature will not fit


@pytest.mark.parametrize("project", PROJECTS)
def test_built_app_image_fits_its_slot_with_a_margin(project):
    images = glob.glob(os.path.join(FW, project, "dist", "*", "*_app.bin"))
    if not images:
        pytest.skip("no dist/ build of %s (run scripts/build.bat --merge)" % project)
    parts = parse_partitions(_read(os.path.join(FW, project, "partitions.csv")).decode("utf-8"))
    slots = [p["size"] for p in parts if p["app"]]
    slot = min(slots)
    for image in images:
        size = os.path.getsize(image)
        free = (slot - size) * 100.0 / slot
        assert size <= slot, "%s (%d B) does not fit the %d B slot" % (image, size, slot)
        assert free >= MIN_FREE_PERCENT, "only %.1f %% of the slot is free for %s" % (free, os.path.basename(image))
