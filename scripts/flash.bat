@echo off
:: Flash a merged firmware image (<name>_full.bin from `build.bat --merge`) with esptool on Windows.
::
::   scripts\flash.bat <chip> <COMx> <image.bin> [baud]
::   scripts\flash.bat esp32s3 COM12 dist\esp32s3\host-esp32s3_full.bin
::   scripts\flash.bat esp32c6 COM14 dist\esp32c6\rcp-esp32c6_full.bin 460800
::
:: <chip> sets the flash offset of the merged image: 0x0 for esp32s3/esp32c6/esp32c3/esp32h2,
:: 0x1000 for esp32/esp32s2.  The port is mandatory on purpose: both XIAO modules show up
:: with the same USB VID, so guessing the port could flash the wrong board
:: (see scripts\detect_port.py --serial ... and docs\BUILD_AND_FLASH.md).
::
:: Environment:
::   PYTHON   python launcher with esptool installed (default: py -3.12)
::   DRY_RUN  set to 1 to only print the esptool command
::
:: Boot mode: if the board does not enter download mode by itself, hold BOOT while
:: plugging in USB (or tap RESET while holding BOOT), flash, then press RESET.
setlocal
set "CHIP=%~1"
set "PORT=%~2"
set "IMAGE=%~3"
set "BAUD=%~4"
if "%BAUD%"=="" set "BAUD=460800"
if "%PYTHON%"=="" set "PYTHON=py -3.12"

if "%CHIP%"=="" goto usage
if "%PORT%"=="" goto usage
if "%IMAGE%"=="" goto usage

set "OFFSET=0x0"
if /i "%CHIP%"=="esp32"   set "OFFSET=0x1000"
if /i "%CHIP%"=="esp32s2" set "OFFSET=0x1000"

if not exist "%IMAGE%" (
    echo ERROR: image not found: %IMAGE%
    exit /b 1
)

set CMD=%PYTHON% -m esptool --chip %CHIP% -p %PORT% -b %BAUD% write-flash %OFFSET% "%IMAGE%"
echo %CMD%
if "%DRY_RUN%"=="1" exit /b 0
%CMD%
exit /b %ERRORLEVEL%

:usage
echo Usage: flash.bat ^<chip^> ^<COMx^> ^<image.bin^> [baud]
exit /b 2
