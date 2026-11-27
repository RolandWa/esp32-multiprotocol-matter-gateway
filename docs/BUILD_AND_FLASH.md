# Build, flash, monitor

Everything here was exercised on the previous project (an ESP32-C3 firmware built in WSL, flashed from Windows). The scripts
were additionally re-tested on 2026-11-25: `build.bat` + `wsl_idf.sh` reproduced the old project's merged image (same size,
106 of 786 384 bytes differ — embedded build paths/timestamps). **Flashing was not re-tested** (no board connected): `flash.bat`
has only a dry-run test. Hardware steps below marked *(experience)* come from the old project's flash scripts.

## 1. Two images, two chips

| Image | Chip | Toolchain | Bootloader offset of the merged image |
|---|---|---|---|
| `firmware/host-esp32s3` | ESP32-S3 (Xtensa) | `xtensa-esp-elf` | `0x0` |
| `firmware/rcp-esp32c6` | ESP32-C6 (RISC-V) | `riscv32-esp-elf` | `0x0` |

(Classic ESP32 and ESP32-S2 use `0x1000`; `flash.bat` knows this.) Both images must be built with the **same pinned IDF** unless a
documented reason says otherwise. Targets are independent: a build dir is created per `(IDF tag, target)` pair.

## 2. Building (Windows → WSL)

```powershell
# IDF v6.0.2 installed side by side (docs/ENVIRONMENT.md section 4); host also needs esp-matter's export.sh
& .\scripts\build.bat --project firmware/host-esp32s3 --target esp32s3 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --extra-export '~/esp/esp-matter/export.sh' --merge
& .\scripts\build.bat --project firmware/rcp-esp32c6  --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --merge
& .\scripts\build.bat --project firmware/rcp-esp32c6  --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' -- size-components   # any idf.py command
& .\scripts\build.bat --project firmware/rcp-esp32c6  --target esp32c6 --idf '~/esp/esp-idf-v6.0.2' --tools-path '~/.espressif-gateway' --clean               # fresh build dir
```

Two PowerShell traps (both cost a failed build on 2026-11-27): **use forward slashes in `--project`** (`firmware/rcp-esp32c6`; the
backslash is eaten on the way into WSL's bash, giving `firmwarercp-esp32c6`) and **quote `~`** (`'~/esp/...'`; PowerShell expands an
unquoted `~` to `C:\Users\<name>` before the script sees it). `--tools-path` keeps the old project's `~/.espressif` untouched. The
shared `firmware/common` directory is mirrored to `~/work/src/common` on every build, so `../common` in the project's `CMakeLists.txt` resolves.

What `scripts/wsl_idf.sh` does, and why:

1. **rsync** the project to `~/work/src/<name>` (excludes `.git`, `build/`, `dist/`, `managed_components/`, `sdkconfig`;
   excluded paths are also protected from `--delete`, so downloaded components and the generated `sdkconfig` survive between runs).
   Needed because ESP-IDF breaks on paths with spaces/commas.
2. Put a **Python shim** first on `PATH` (`python3.10` for IDF v4.x, system `python3` otherwise; override with `--python`).
3. Source the IDF `export.sh` **without `set -u`** (it dies silently under it) and optionally `--extra-export` (e.g. esp-matter's `export.sh`).
4. Run `idf.py set-target <target>` **once per build dir**, then your `idf.py` command (default `build`).
5. `--merge`: `esptool.py merge_bin` from the build's `flash_args` → `<project>/dist/<target>/<name>_full.bin` (+ `_app.bin`).
   `dist/` is git-ignored. **Back up a known-good image before rebuilding**, the file is overwritten.

`sdkconfig.defaults` and `sdkconfig.defaults.<target>` are the only configuration files to commit; `sdkconfig` is generated.
`dependencies.lock` (IDF component manager) **is** committed: the script syncs it in, and after a build that created or changed it
prints the `cp` command that copies the new lock back from the WSL copy into the project.
Keep secrets out of them (see `CODING_GUIDELINES.md`).

### Calling WSL by hand

```powershell
wsl bash scripts/wsl_idf.sh --help
wsl bash -c "cd ~/work/build/host-esp32s3/<tag>-esp32s3 && ls"          # look at a build tree
```

Put anything longer than one line in a script file and run `wsl bash <file>`: variables from the outer shell are not expanded by
`wsl.exe`, and Git Bash rewrites `/mnt/...` arguments (see `LESSONS_LEARNED.md`).

## 3. Flashing (Windows)

Flash from **Windows** with esptool (USB devices are not visible inside WSL unless usbipd is set up, which this project does not use).

```powershell
python scripts\detect_port.py                 # COM port, USB VID:PID, USB serial number, description
python scripts\detect_port.py --chip-id       # additionally asks esptool which chip answers (slow)
python scripts\detect_port.py --serial 40:4C  # port of the board whose USB serial number contains that text

& .\scripts\flash.bat esp32s3 COM12 dist\esp32s3\host-esp32s3_full.bin
& .\scripts\flash.bat esp32c6 COM14 dist\esp32c6\rcp-esp32c6_full.bin [baud]      # default 460800
$env:DRY_RUN=1; & .\scripts\flash.bat esp32c6 COM14 dist\esp32c6\rcp-esp32c6_full.bin   # prints the command only
```

Rules learned (some the hard way):

* **Native USB-Serial/JTAG of all XIAO ESP32-S3/C6/C3 boards enumerates as VID `0x303A`.** With both modules plugged in, the VID cannot tell
  them apart, so `flash.bat` makes the port a **required** argument. Write the USB serial numbers of the two boards into the table below once.
* esptool on Windows is **5.x** (`write-flash`); the WSL copy used for merging is the IDF-bundled one. Both accept the merged image.
* Download mode: if the board does not enter it by itself, hold **BOOT** while plugging in USB (or tap RESET while holding BOOT), flash,
  then press RESET. *(experience)*
* The first flash of a new board needs the **merged** image (bootloader + partition table + app). Afterwards `idf.py app-flash` equivalents
  (`_app.bin` at the app offset from `flash_args`) are enough.
* **Batch flashing** *(experience)*: the old project had `flash_batch.bat` — loop "plug in, press Enter, flash, count pass/fail". Copy that idea
  when several units are built; keep a log of unit → USB serial number → firmware version.
* Two-chip product: always flash/verify **both** images and record the pair of versions. The host must refuse an RCP image of an
  incompatible protocol version (design this in; see `CODING_GUIDELINES.md`).

| Board | Role | USB serial number | COM port (this PC) |
|---|---|---|---|
| XIAO ESP32-S3 Plus | host | *(fill in)* | *(fill in)* |
| XIAO ESP32-C6 | RCP | *(fill in)* | *(fill in)* |

## 4. Serial monitor

```powershell
python -m serial.tools.miniterm COM12 115200            # pyserial's terminal, Ctrl+] to quit
```

`idf.py monitor` needs the port inside WSL, so use miniterm (or the VS Code serial monitor) on Windows. Typical console speed is 115 200 baud;
on the XIAO S3/C6 the console is the native USB-Serial/JTAG unless it was moved to UART0 (D6/D7). The old project's firmware had a small
line-based command console on the UART (`v`, `s`, `h`, `reboot`) — a cheap, very useful habit for bring-up.

## 5. esp-matter builds (host image) — differences

* esp-matter pulls many gigabytes of submodules; keep it on the Linux file system and build there only (never under `/mnt/c`).
* Source its `export.sh` after IDF's (`--extra-export`). Build time for the first build is long; later builds are incremental because the
  build dir is kept per `(IDF, target)`.
* Partition table and flash size: the XIAO S3 Plus has 16 MB flash (unverified, from the PDF/Seeed) — plan two OTA slots (Matter stack + app is large).
* The C6 RCP image is small; the XIAO C6 has 4 MB flash and no PSRAM (unverified numbers from the PDF).

## 6. Checklist before declaring "firmware works"

- [ ] both images build from a clean build dir (`--clean`) with the pinned IDF
- [ ] merged images flashed to **both** boards (ports confirmed by serial number), console shows the expected versions
- [ ] the inter-chip UART link comes up (host reports RCP version)
- [ ] items from `TESTING.md` §6 (hardware tests) executed and recorded with date and firmware version

## References

- esptool documentation (merge-bin, write-flash, chip IDs): <https://docs.espressif.com/projects/esptool/>
- ESP-IDF build system: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/build-system.html>
- Seeed XIAO ESP32-S3 / ESP32-C6 getting started (boot mode, USB): <https://wiki.seeedstudio.com/>
- pyserial `miniterm`: <https://pyserial.readthedocs.io/en/latest/tools.html#module-serial.tools.miniterm>
- Previous project's flashing scripts: `../wireless-esp8266-dap/flash_eps.bat`, `flash_batch.bat`, `detect_port.py`
