# Lessons learned (previous project → this one)

Every row below happened in `../wireless-esp8266-dap` (or while setting up this repository). Format: **symptom → cause → what to do**.
Grouped by area; the "did" column says how it was handled, so you can tell a rule from a guess.

## Build environment (Windows + WSL + ESP-IDF)

| Symptom | Cause | Do this |
|---|---|---|
| cmake/kconfiglib fail in a OneDrive path | spaces and commas in the path | never build in place; `scripts/wsl_idf.sh` rsyncs to `~/work/src/<name>` (excluded files are protected from `--delete`) |
| IDF v4.4.2 `install.sh`/pip fails on Python 3.14 (gevent compile) | IDF v4.x needs Python ≤ 3.10 | `python3` → `python3.10` shim first on `PATH` (script `--python`) |
| mbedtls fails to configure with the system cmake | Ubuntu 26.04 ships cmake 4.x, IDF 4.4.2's mbedtls needs ≤ 3.x | IDF's venv holds cmake 3.28.4 (`pip install cmake==3.28.4`); it wins on `PATH` after `export.sh` |
| `export.sh` seems to "do nothing", no error | the calling script had `set -u`; export.sh needs unset variables and its stderr was sent to `/dev/null` | never `set -u` around `export.sh` (cost a failed regression run) |
| S3/ESP32 configure fails: "CMAKE_C_COMPILER xtensa-esp32s3-elf-gcc not found" | toolchain for that target was never installed (only `esp32c3` had been) | `install.sh esp32s3,esp32`; check `~/.espressif/tools`; it is an environment error, not a code error |
| Each IDF generation needs different toolchain builds | IDF 4.4.2 → `esp-2021r2-patch3-8.4.0`; IDF 6 → `esp-16.1.0` | install per IDF; keep them side by side |
| A rebuild overwrote the last flashed `.bin` | build copies the merged image to a fixed name | back up known-good images before building |
| `wsl` prints "Failed to start the systemd user session" on every call | `systemd=true` in `wsl.conf`, no user session | harmless; filter it out when parsing output |
| IDF v6.0.2 `export.sh` would look in `~/.espressif` (the old project's tools) | `IDF_TOOLS_PATH` unset | `wsl_idf.sh --tools-path ~/.espressif-gateway` (exported inside the build subshell only) |
| `EXTRA_COMPONENT_DIRS` entry `../common` "doesn't exist" | `wsl_idf.sh` copied only the project directory to `~/work/src/<name>` | the script now mirrors a sibling `common/` to `~/work/src/common` |
| `fatal error: esp_matter_mem.h: No such file` after adding `PRIV_REQUIRES common` to `main/CMakeLists.txt` | a `main` component **without** `REQUIRES` depends on every component; listing any requirement removes that default | leave vendor `main/CMakeLists.txt` as is; `common` is still visible (it is in the build) |
| esp-matter `install.sh` fails building `pycairo` | Python 3.14 makes connectedhomeip require PyGObject (needs `pkg-config` + cairo headers); `sudo` not available; `PW_BOOTSTRAP_PYTHON=python3.10` was ignored (venv still made from the IDF Python) | firmware builds do not need that env (`export.sh` only adds cipd `gn`/`zap`): `install.sh --no-bootstrap --no-host-tool`; `chip-tool` stays unbuilt |
| A mutated/broken module made a unit test hang (unbounded `while` in the test) | the test waited for a state the broken code never reached | every wait loop in a test has a step limit and a `CHECK`; mutation scripts run each binary under `timeout` |

## Shells and quoting (PowerShell, cmd, Git Bash, WSL)

| Symptom | Cause | Do this |
|---|---|---|
| `'build.bat --build' is not recognized` | `cmd /c "build.bat --build"` treats the quoted string as one file name | call `& .\build.bat --build` from PowerShell |
| PowerShell: "Missing closing ')'" | `( cmd1; cmd2 ) \| ...` is not valid | `& { cmd1; cmd2 } \| ...` |
| `bash` on the Windows `PATH` cannot find `C:\...` files | it is WSL's bash | run with a relative path and `cwd=`, or `wsl bash /mnt/c/...` |
| Git Bash turns `/mnt/c/...` arguments into `C:/Program Files/Git/mnt/...` | MSYS path conversion | put the command in a script file; or `MSYS_NO_PATHCONV=1` |
| Shell variables empty inside `wsl -- bash -c '...$VAR...'` | `wsl.exe`/the outer shell expands (or strips) them | write a `.sh` file and run `wsl bash file.sh` |
| `python -I script.py` cannot import its sibling module | isolated mode does not put the script directory on `sys.path` | plain `python script.py` for repo scripts; `-I` only for untrusted code |
| `grep -c $'\r'` gives nonsense in the agent's bash tool | `$'..'` quoting differs | count CRs with Python on the bytes (`b"\r\n"`) |
| A `~` in `--work ~/x` created a directory literally named `~` | tilde is not expanded in values received as arguments | the scripts expand a leading `~` themselves |
| `--tools-path directory not found: C:Users<name>/.espressif-gateway` | PowerShell expands an **unquoted** `~` to `C:\Users\<name>` before `build.bat` runs | quote it: `'~/.espressif-gateway'` (2026-11-27) |
| `no CMakeLists.txt in .../firmwarercp-esp32c6` | `build.bat` passes arguments through `wsl bash`, which eats the backslash of `firmware\rcp-esp32c6` (`\r` is swallowed) | forward slashes in `--project`: `firmware/rcp-esp32c6` (2026-11-27) |
| `python -` in the agent's Git Bash hangs | `python` there is the Microsoft Store stub waiting on stdin | use `py -3.12` (PowerShell) or WSL's `python3` |

## Line endings and git

| Symptom | Cause | Do this |
|---|---|---|
| "LF will be replaced by CRLF" warnings; bash script fails with `\r` errors after a checkout | `core.autocrlf=true` on this PC | `.gitattributes`: `*.sh`/`Makefile`/`*.c`/`*.py` LF, `*.bat` CRLF |
| KiCad project diff shows every line changed | a tool rewrote a CRLF file with LF | KiCad files are `-text` in `.gitattributes`; edit them only with `scripts/kicad_*.py` (byte-exact) |
| `.gitignore` got mixed line endings after an append | the file was CRLF, the appended text LF | convert the whole file back to one style; check with a byte count |
| A tag pointed at an old commit | tag created before more commits were made | moving a pushed tag needs `--force` — only with the owner's approval, only on the own fork; describe what a tag covers; never mark "working" before hardware tests |
| Commit approval | owner's rule | summarise, propose message, wait; split into logical commits (firmware+tests+docs vs. regenerated production files) |

## Firmware design

| Symptom | Cause | Do this |
|---|---|---|
| ADC read nonsense on the S3, PWM on a pin that is also the ADC input | `ADC1_CHANNEL_2` hard-coded: GPIO2 on C3, **GPIO3 on S3**, GPIO38 on ESP32; PWM pin 3 is the S3's ADC pad and the ESP32's UART0 RX | per-target pin header; derive ADC channel from the pin; host test for pin conflicts (`CODING_GUIDELINES.md` §3) — this was found late, by review, never on hardware |
| ADC2 reads fail while Wi-Fi is on | ADC2 hardware is shared with Wi-Fi | ADC1 only |
| Measurements disagreed between boards | the analog filter's time constant (≈ 145 ms) was longer than the test scripts' wait (0.4 s) | derive settle time from the circuit, expose a "settled" state, wait ≥ 5 τ |
| Calibration table "fit" one board, not the rest | boards differ (tolerances, one part fitted differently); one shared table is a compromise | per-board tables selected at run time, with a generator + tests; measure with the settled protocol |
| Windows USBIP kernel driver returned stale bytes | it does not forward bulk-IN URBs | speak the protocol directly over TCP (the old project's `read_vtarget_tcp.py`) — avoid that driver |
| Client vanished, single connection slot stayed busy for hours | default TCP keepalive ≈ 2 h | `TCP_KEEPIDLE/INTVL/CNT` = 5/2/3 s (~11 s) on the accepted socket |
| Console command rebooted the board after flashing | stray bytes in the UART buffer parsed as a one-letter command | reboot only on the full word `reboot`; flush the UART at start |

## Testing

| Symptom | Cause | Do this |
|---|---|---|
| Tests passed first time, but proved nothing | test too weak | mutation check: break the code in a temp copy, tests must fail (5/5 killed on every new module) |
| Python copies of a firmware table drifted | three mirrors of one table | a pytest parses the C source and compares; generated files get `--check` + a freshness test |
| Protocol encoder (C) and decoder (Python) disagreed in theory | no shared vector | the same byte vector asserted on both sides |
| "It builds" reported as "it works" | easy to conflate | keep a "hardware check pending" list; report what was not run |
| Regression build of other targets showed warnings in old code | unused-function/-variable in non-VTarget branches | compare with a baseline build of the previous commit before blaming the change |
| Test runner skipped silently | missing toolchain | the pytest runner skips with a reason only when gcc/make/WSL are absent; elsewhere failures are loud |

## Hardware / KiCad / sourcing

| Symptom | Cause | Do this |
|---|---|---|
| Documents said R4 = 100 Ω, firmware header 100 Ω, schematic 22 kΩ, fab BOM 39 kΩ | values copied into many places; schematic changed three times | **schematic is the only source**; link, do not copy; `kicad_bom_check.py` |
| Fab package listed old parts after a rework | LCSC/TME fields of five parts still had the old numbers (schematic **and** PCB) | edit both with `kicad_set_fields.py`; run `kicad_bom_check.py` before every export |
| BOM kept the stale part number although the PCB was right | JLCPCB Tools setting `lcsc_priority=false` → `project.db` wins | export script forces the board to win; commit `project.db` |
| LDO output never changed with the control signal | LDO in dropout: 5 V from a XIAO is ≈ 4.3–4.4 V after its Schottky | check headroom at the real input; keep the schematic note |
| Output stuck at maximum on the un-reworked boards (PCB-02…10) | MOSFET gate divider (39k/10k) limited Vgs to 0.67 V — below Vth | compute the drive voltage in the design review; the rework changed R4/R5/C2/R1/R3 |
| A "not stocked" part was assumed for months | nobody looked at LCSC; 10 µF/25 V X5R 0603 exists (C96446) | check LCSC/JLCPCB stock when choosing; 5 % JR values missing → 1 % FR |
| Board-to-board spread blamed on different rework states | all boards had the same nominal values — spread was tolerance, C2 part, short settle time | verify the hypothesis before documenting it as root cause |
| Plugin GUI needed for fab export | no CLI in the plugin | `kicad_fab_export.py` drives it headless with KiCad's own Python (BOM/CPL identical to the GUI's) |
| KiCad overwrote a scripted edit | project was open | close KiCad first, reload after |
| `~/Documents` is not where KiCad's plugins are | Documents is redirected into OneDrive | ask Windows for the known folder (done in the script) |

## Process

| Rule | Why |
|---|---|
| Ask before changing application code; ask before commit/push | owner's explicit rule; repeated feedback |
| First name only in commits and generated files | owner's privacy preference |
| Verify AI-generated research against datasheets | the PDF mixes correct statements with unverified numbers and an outdated claim about the Zigbee bridge example |
| One IDF per project, pinned, recorded | "never migrate APIs to a newer IDF" held for the old project; for this one the IDF must be ≥ the C6/esp-matter minimum — decide once, write it down |
| Keep the repo root clean; docs with `## References` | the owner's policy from the old project |

## References

- Old project history and notes: `../wireless-esp8266-dap` — `git log`, `circuit_ESP32C3_Xiao/documentations/VTARGET_BATCH_ANALYSIS.md`, `tests/TEST_RESULTS.md`
- ESP-IDF ADC (ADC2/Wi-Fi): <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/adc.html>
- gitattributes: <https://git-scm.com/docs/gitattributes>
- AP1117 datasheet (dropout): <https://www.diodes.com/assets/Datasheets/AP1117.pdf>
