@echo off
setlocal
set "EP_ROOT=%~dp0"
if not exist "%EP_ROOT%.venv\Scripts\python.exe" goto install
"%EP_ROOT%.venv\Scripts\python.exe" -c "import errorpilot" >nul 2>nul
if errorlevel 1 goto install
goto run
:install
echo [ErrorPilot] Setting up on first use...
call "%EP_ROOT%setup.cmd"
if errorlevel 1 exit /b 1
:run
if "%~1"=="" (
  "%EP_ROOT%.venv\Scripts\python.exe" -m errorpilot auto "%CD%"
) else (
  "%EP_ROOT%.venv\Scripts\python.exe" -m errorpilot %*
)
exit /b %errorlevel%
