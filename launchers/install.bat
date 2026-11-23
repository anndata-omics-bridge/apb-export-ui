@echo off
rem Install the APB Export web app with uv from PyPI, then start it; run it again to start the app.
rem Arguments go to `apb-export-web start`, such as --port 8771 or --no-browser.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul || powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" || goto failed
uv tool install --python 3.13 --with-executables-from apb2,apb-export,apb-fasta apb-export-ui==0.2.0 || goto failed
for /f "delims=" %%d in ('uv tool dir --bin') do set "UV_TOOL_BIN=%%d"
"%UV_TOOL_BIN%\apb-export-web.exe" start %* || goto failed
exit /b 0
:failed
echo Installing or starting APB Export failed; see the messages above.
pause
exit /b 1
