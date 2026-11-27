@echo off
:: Build an ESP-IDF project in WSL from Windows (wrapper around scripts/wsl_idf.sh).
::
::   scripts\build.bat --project firmware\host-esp32s3 --target esp32s3 --idf ~/esp/esp-idf-v5.x --merge
::   scripts\build.bat --project firmware\rcp-esp32c6  --target esp32c6 --idf ~/esp/esp-idf-v5.x -- build size
::
:: All arguments are passed on to wsl_idf.sh unchanged (see its header for the options).
:: --project is relative to the repository root unless it is an absolute WSL path.
:: Set IDF_DIR (inside WSL) to avoid repeating --idf.
::
:: Tip: run it from PowerShell as  `& .\scripts\build.bat ...`  (not `cmd /c "scripts\build.bat ..."`:
:: the extra quotes make cmd look for a file literally named like the whole command line).
setlocal
set "HERE=%~dp0"
for /f "usebackq delims=" %%I in (`wsl wslpath -a "%HERE%wsl_idf.sh"`) do set "WSL_SCRIPT=%%I"
if not defined WSL_SCRIPT (
    echo ERROR: WSL is not available or wslpath failed.
    exit /b 1
)
wsl bash "%WSL_SCRIPT%" %*
exit /b %ERRORLEVEL%
