@echo off
REM ExecBox MCP Server Runner for Windows
REM This batch file ensures the server runs with the correct environment

setlocal

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Run the Python runner script with all arguments passed through
python run_server.py %*

REM Exit with the same code as the Python script
exit /b %ERRORLEVEL%
