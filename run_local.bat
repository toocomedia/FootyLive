@echo off
setlocal

set PYTHON_EXE=

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PYTHON_EXE=py
)

if "%PYTHON_EXE%"=="" (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    set PYTHON_EXE=python
  )
)

if "%PYTHON_EXE%"=="" (
  echo Could not find py or python on PATH.
  exit /b 1
)

if not exist .venv (
  %PYTHON_EXE% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if "%API_KEY%"=="" (
  set API_KEY=change-me-local-key
)

if "%CACHE_TTL_SECONDS%"=="" (
  set CACHE_TTL_SECONDS=20
)

if "%REQUEST_TIMEOUT_SECONDS%"=="" (
  set REQUEST_TIMEOUT_SECONDS=10
)

if "%LOG_LEVEL%"=="" (
  set LOG_LEVEL=INFO
)

echo Starting Footy API on http://127.0.0.1:8000
echo API key for local use: %API_KEY%
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
