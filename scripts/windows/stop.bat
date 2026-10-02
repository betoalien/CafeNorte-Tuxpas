@echo off
setlocal
cd /d "%~dp0\..\.."
uv run cafenorte stop %*
if "%*"=="" if not defined CI pause
exit /b %ERRORLEVEL%
