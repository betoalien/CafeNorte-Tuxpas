@echo off
setlocal
cd /d "%~dp0\..\.."
uv run cafenorte credentials %*
if "%*"=="" if not defined CI pause
exit /b %ERRORLEVEL%
