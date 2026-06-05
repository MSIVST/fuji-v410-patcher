@echo off
setlocal
cd /d "%~dp0"
py -3 fuji_v410_patcher_gui.pyw
if errorlevel 1 (
  echo.
  echo Failed to launch with the Python launcher. Trying python.exe...
  python fuji_v410_patcher_gui.pyw
)
