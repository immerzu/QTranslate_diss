@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run_qtranslate_smoke.ps1" %*
exit /b %ERRORLEVEL%
