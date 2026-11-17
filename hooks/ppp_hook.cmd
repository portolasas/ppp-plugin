@echo off
rem Starts ppp_hook.py for the hooks of VS Code on Windows (PLUGIN PL-12, PL-27).
rem The Python: PPP_PYTHON; else the first line of python.txt in the folder of ppp (PPP_HOME, else %USERPROFILE%\.ppp),
rem written by "ppp setup"; else python.exe on PATH unless it is the Store stub in WindowsApps; else python.exe of an
rem active conda or mamba environment; else C:\BITrusted, where environments go that may not go into Program Files
rem (python.exe in it, in a folder of it, or in <folder>\envs\<name>; the first one found, PPP_TRUSTED_DIR for tests);
rem else a usual conda, mamba or miniforge folder; else the launcher py.exe on PATH.
rem Never the current folder (the workspace): a python.bat there would run on every tool call.
rem Never blocks: without a Python, or when Python fails, it ends with 0. A PreToolUse hook that fails makes the agent
rem host refuse every tool call; a refusal of ppp comes as JSON on stdout with exit code 0.
setlocal EnableExtensions DisableDelayedExpansion
set "NoDefaultCurrentDirectoryInExePath=1"
set "PPP_PY="
set "PPP_DIR=%USERPROFILE%\.ppp"
if defined PPP_HOME set "PPP_DIR=%PPP_HOME%"
if not defined PPP_TRUSTED_DIR set "PPP_TRUSTED_DIR=C:\BITrusted"
if defined PPP_PYTHON if exist "%PPP_PYTHON%" set "PPP_PY=%PPP_PYTHON%"
if not defined PPP_PY if exist "%PPP_DIR%\python.txt" for /f "usebackq eol=| delims=" %%L in ("%PPP_DIR%\python.txt") do if not defined PPP_PY if exist "%%~L" set "PPP_PY=%%~L"
if not defined PPP_PY for /f "delims=" %%P in ('where $PATH:python.exe 2^>nul ^| findstr /v /i /l /c:"WindowsApps"') do if not defined PPP_PY set "PPP_PY=%%P"
if not defined PPP_PY for %%R in ("%CONDA_PREFIX%" "%MAMBA_ROOT_PREFIX%" "%PPP_TRUSTED_DIR%") do if not defined PPP_PY if not "%%~R"=="" if exist "%%~R\python.exe" set "PPP_PY=%%~R\python.exe"
if not defined PPP_PY if exist "%PPP_TRUSTED_DIR%\" for /d %%A in ("%PPP_TRUSTED_DIR%\*") do if not defined PPP_PY if exist "%%~A\python.exe" set "PPP_PY=%%~A\python.exe"
if not defined PPP_PY if exist "%PPP_TRUSTED_DIR%\" for /d %%A in ("%PPP_TRUSTED_DIR%\*") do for /d %%E in ("%%~A\envs\*") do if not defined PPP_PY if exist "%%~E\python.exe" set "PPP_PY=%%~E\python.exe"
if not defined PPP_PY for %%R in ("%USERPROFILE%\miniforge3" "%USERPROFILE%\mambaforge" "%USERPROFILE%\micromamba" "%USERPROFILE%\miniconda3" "%USERPROFILE%\anaconda3" "%LOCALAPPDATA%\miniforge3" "%LOCALAPPDATA%\mambaforge" "%LOCALAPPDATA%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%ProgramData%\miniforge3" "%ProgramData%\mambaforge" "%ProgramData%\miniconda3" "%ProgramData%\anaconda3") do if not defined PPP_PY if exist "%%~R\python.exe" set "PPP_PY=%%~R\python.exe"
if defined PPP_PY (
  "%PPP_PY%" -I "%~dp0ppp_hook.py" %*
  exit /b 0
)
set "PPP_LAUNCHER="
for /f "delims=" %%P in ('where $PATH:py.exe 2^>nul') do if not defined PPP_LAUNCHER set "PPP_LAUNCHER=%%P"
if defined PPP_LAUNCHER "%PPP_LAUNCHER%" -3 -I "%~dp0ppp_hook.py" %*
exit /b 0
