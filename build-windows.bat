@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv-windows
if errorlevel 1 goto failed
.venv-windows\Scripts\python.exe -m pip install -r requirements-windows-build.txt
if errorlevel 1 goto failed
.venv-windows\Scripts\python.exe build_windows.py
if errorlevel 1 goto failed
echo.
echo Windows ZIP created in dist. You may close this window.
pause
exit /b 0
:failed
echo.
echo Build failed. Install 64-bit Python 3.12 from python.org, including Tcl/Tk and the Python launcher.
pause
exit /b 1
