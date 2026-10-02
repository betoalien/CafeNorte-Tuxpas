@echo off
setlocal
cd /d "%~dp0\..\.."
uv run cafenorte validate %*
if "%*"=="" if not defined CI pause
exit /b %ERRORLEVEL%
