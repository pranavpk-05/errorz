@echo off
setlocal
pushd "%~dp0"
echo [ErrorPilot] Preparing a local installation...
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python Launcher 'py' not found. Install Python 3.11+ first.
  goto fail
)
py -3.11 --version >nul 2>nul
if not errorlevel 1 (
  py -3.11 -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 (
  echo [ERROR] Could not create virtual environment. Python 3.11+ required.
  goto fail
)
:install
".venv\Scripts\python.exe" -m pip install -e "."
if errorlevel 1 (
  echo [ERROR] Installation failed. Check internet access and pip output.
  goto fail
)
echo.
echo [ErrorPilot] Ready. Examples:
echo   ep.cmd doctor
echo   ep.cmd auto examples
popd
exit /b 0
:fail
popd
exit /b 1
