# Development environment

What the owner uses successfully, as of **2026-11-25**. "Verified" = read from the machine during that session
(`--version`, directory listings, header files). Re-verify before relying on an exact number — this machine moves
(IDF v6.1-dev, Python 3.14 and Ubuntu 26.04 are all recent).

## 1. Layout of the setup

```text
Windows 11 (10.0.26200)                                WSL2 (Ubuntu 26.04 LTS, kernel 6.18.33.2-microsoft-standard-WSL2)
 ├─ repo (OneDrive folder, path has spaces/commas)       ├─ ~/esp/esp-idf-v4.4.2   old project (tag v4.4.2)  [do not touch]
 ├─ VS Code + Claude Code                                ├─ ~/esp/esp-idf          untagged v6.1-dev checkout
 ├─ Python 3.12  pytest, pyserial, esptool 5.3.1         ├─ ~/.espressif/          tools + python envs
 ├─ KiCad 10.0 (+ 9.0) and PCM plugins                   ├─ ~/esptool              esptool v4.6.2 (matches the old CI)
 ├─ Git 2.56 (core.autocrlf=true), gh 2.96               ├─ ~/work/src, ~/work/build   rsync copies + build dirs (scripts/wsl_idf.sh)
 └─ flashing, serial monitor, KiCad, Bambu Studio        └─ compilers, cmake, ninja, gcc for host unit tests
```

Rule of thumb: **Windows owns USB, KiCad and the sources; WSL owns every compiler.** Sources are *copied* (rsync) to a
Linux path for each build because ESP-IDF cannot build in a path with spaces/commas, and because OneDrive syncing build trees
is slow and wasteful. WSL's `/mnt/c` (9p) is also much slower than the Linux file system.

## 2. Versions (verified)

### Windows

| Tool | Version | Notes |
|---|---|---|
| OS | Windows 11 Enterprise 10.0.26200 | |
| WSL | 2.7.10.0, kernel 6.18.33.2 | `wsl.conf`: `systemd=true`. Every `wsl` call prints "Failed to start the systemd user session" — harmless |
| Python (scripts, tests) | **3.12.10** (`py -3.12`) | has pytest 9.1.1, pyserial, **esptool 5.3.1**. 3.13 also installed; the old project's `.venv` is *not* the default |
| Git | 2.56.0.windows.4 | `core.autocrlf=true` → LF/CRLF warnings; see `.gitattributes` |
| GitHub CLI | 2.96.0 | |
| KiCad | **10.0** and 9.0 in `C:\Program Files\KiCad\` | `bin\kicad-cli.exe`, `bin\python.exe` (has `pcbnew`, wx) |
| KiCad plugins (PCM) | JLCPCB Tools (bouni), InteractiveHtmlBom, Fabrication Toolkit (bennymeg), KiKit, … | in the user's **Documents** folder `KiCad\10.0\3rdparty\plugins\` — Documents is OneDrive-redirected, so `~/Documents` is the wrong place; `scripts/kicad_fab_export.py` asks Windows for the real folder |
| Printer slicer | Bambu Studio (printer: Bambu Lab H2D) | see `ENCLOSURE_3D.md` |

### WSL (Ubuntu 26.04 LTS)

| Tool | Version | Notes |
|---|---|---|
| gcc / make | 15.2.0 / 4.4.1 | host unit tests (`tests/unit`) |
| cmake | 4.2.3 (system) | **too new for IDF v4.4.2's mbedtls** — IDF's own venv holds cmake 3.28.4 and wins on `PATH` after `export.sh` |
| ninja / rsync / git / ccache | 1.13.2 / 3.4.1 / 2.53.0 / 4.12.3 | |
| python3 | 3.14.4 | default. Fine for the IDF v6.x venv (`idf6.2_py3.14_env`); **not** usable for IDF v4.x |
| python3.10 | 3.10.20 | used for IDF v4.4.2 (`idf4.4_py3.10_env`) through a `python3 → python3.10` shim |

### ESP-IDF in WSL

| Path | Version | State |
|---|---|---|
| `~/esp/esp-idf-v4.4.2` | v4.4.2 | old project. SoCs in `components/soc`: esp32, esp32c3, esp32h2, esp32s2, esp32s3 — **no ESP32-C6** |
| `~/esp/esp-idf` | v6.1-dev-6354-gd0b65797c30 (untagged) | has esp32c6, esp32c5, esp32c61, esp32h2, esp32h21, esp32h4, esp32p4, esp32s3, esp32s31 … Pin a **release tag** for the product |
| `~/esp/esp-idf-v6.0.2` | v6.0.2 (tag) | **added 2026-11-27** for this project; `IDF_TOOLS_PATH=~/.espressif-gateway` (own tools + `python_env/idf6.0_py3.14_env`, esptool 5.7.0 inside). `install.sh esp32s3,esp32c6` ran; `ot_rcp` for esp32c6 built with it. Source copies in `~/work/src`, builds in `~/work/build/<name>/v6.0.2-<target>` |
| `~/esp/esp-matter` | `release/v1.6.1` (tip `4645784`, connectedhomeip `0998b87db7`) | **added 2026-11-27**, shallow, ≈ 6.7 GB. Used with `install.sh --no-bootstrap --no-host-tool` (pigweed Python env not built, see `OPEN_QUESTIONS.md` §1); no `chip-tool`. Build: IDF `export.sh` first (with `IDF_TOOLS_PATH=~/.espressif-gateway`), then `. ~/esp/esp-matter/export.sh`, source copy in `~/work/src`, `-B ~/work/build/<name>/v6.0.2-<target>` |
| `~/esptool` | v4.6.2 | used by the old CI-style merge step |

Installed tools in `~/.espressif/tools/`: `riscv32-esp-elf` (esp-16.1.0_20260609 for IDF 6; esp-2021r2-patch3-8.4.0 for IDF 4.4.2),
`xtensa-esp32-elf` and `xtensa-esp32s3-elf` (**esp-2021r2-patch3-8.4.0 only — the IDF 4.4.2 generation**), `openocd-esp32`
(v0.11.0-esp32-20220411, v0.12.0-esp32-20260703), `esp-clangd`, `esp-rom-elfs`, `esp32ulp-elf`, `esp32s2ulp-elf`,
`riscv32-esp-elf-gdb`.
**Missing for IDF 6:** `xtensa-esp-elf` (esp-16.1.0…), which the ESP32-S3 needs. `install.sh esp32s3,esp32c6` in that IDF fetches it.

## 3. Choosing the ESP-IDF version for *this* project

This is an **open decision** (`OPEN_QUESTIONS.md`), but the constraints are known:

* **ESP32-C6 needs a newer IDF than v4.4.2** (verified: no `esp32c6` in its `components/soc`).
* **esp-matter pins its own ESP-IDF release.** Sources disagree on which: the component-registry page of esp-matter v1.4.1 recommends
  IDF v5.2.3, and the GitHub main README names v6.0.2 (a web search on 2026-11-25 could not tie either to a specific esp-matter branch). Take the version from the README of the
  exact esp-matter branch/tag you check out, then install that IDF side by side (§4). Do not use the untagged `~/esp/esp-idf`.
* The Zigbee/RCP side (`esp-zigbee-sdk`, `ot_rcp`) has its own IDF requirements — one IDF version for both images keeps life simple.
* The old project's rule "never migrate APIs to a newer IDF" applies **only to the old project**.

## 4. Installing an ESP-IDF version side by side (WSL)

**Owner's requirement (2026-11-26):** the old project `wireless-esp8266-dap` must keep building. Use a **separate `IDF_TOOLS_PATH`** (e.g. `~/.espressif-gateway`) for the new IDF so its `install.sh` never touches `~/.espressif`; do not change global `PATH`/`python3`/cmake; record a baseline first and rebuild the old project afterwards. Rules and acceptance test: `../project_specification_and_requirements.md` §4A. The commands below must be run with `export IDF_TOOLS_PATH=~/.espressif-gateway` in the same shell (and that variable must not be put into `~/.bashrc`).

```bash
# Example for a release tag; replace <tag> (e.g. vX.Y.Z) and the targets
mkdir -p ~/esp && cd ~/esp
git clone -b <tag> --recursive https://github.com/espressif/esp-idf.git esp-idf-<tag>
cd esp-idf-<tag>
# IDF v4.x needs Python <= 3.10 and v5.x supports a limited Python range: put the right python3 first on PATH
# (scripts/wsl_idf.sh does this with --python; do the same for install.sh:)
mkdir -p ~/.idf_python_shim_python3_10 && ln -sf "$(command -v python3.10)" ~/.idf_python_shim_python3_10/python3
PATH=~/.idf_python_shim_python3_10:$PATH ./install.sh esp32s3,esp32c6      # downloads toolchains; needs internet
```

Then build with `scripts/build.bat … --idf ~/esp/esp-idf-<tag>`. Notes:

* Python venvs live in `~/.espressif/python_env/idf<major.minor>_py<ver>_env`; a Python upgrade of the OS can orphan them — re-run `install.sh`.
* Each IDF generation needs **its own** toolchain versions (see the table above); `install.sh` for the new IDF installs them next to the old ones.
* **esp-matter** (needed for the host image) is a separate checkout with its own `install.sh`/`export.sh` and several GB of submodules.
  Clone it on the **Linux file system** (`~/esp/esp-matter`), follow its docs for the chosen release, and give its `export.sh` to
  the build with `--extra-export ~/esp/esp-matter/export.sh` (or `EXTRA_EXPORT`).
* Pin everything: IDF tag, esp-matter tag, `dependencies.lock` (commit it), and record the exact versions in this file.

## 5. Windows-side setup checklist

```powershell
py -3.12 -m pip install pytest pyserial esptool          # tests, port detection, flashing
git config --global core.autocrlf                         # true on this machine -> .gitattributes matters
wsl --status                                              # WSL2, default distro Ubuntu
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" version
```

Optional lab equipment used by the previous project (not required here): NI VirtualBench (`pyvirtualbench`), a DMM for calibration,
OpenOCD with the elaphureLink build, a USBIP client. They were only needed for the debugger hardware.

## 6. Sanity checks (run after any change to the machine)

```powershell
python -m pytest tests/unit -q                      # 30 tests: C (gcc in WSL, incl. ASan/UBSan) + KiCad tools + scripts
wsl -- gcc --version ; wsl -- ls ~/esp ~/.espressif/tools
```

## References

- ESP-IDF installation (Linux/WSL): <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/linux-macos-setup.html>
- ESP-IDF version/support policy: <https://github.com/espressif/esp-idf/blob/master/SUPPORT_POLICY.md>
- esp-matter documentation (setup, supported IDF per release — choose the release first): <https://docs.espressif.com/projects/esp-matter/>
- WSL documentation (file system performance, `wsl.conf`): <https://learn.microsoft.com/windows/wsl/>
- Previous project's environment script: `../wireless-esp8266-dap/build_WSL.py`
