@echo off
title PeopleFlowMonitor Master Launcher

cd /d "%~dp0"

echo ==========================================
echo       INICIANDO PeopleFlowMonitor
echo ==========================================

:: Detecta venv
set PYTHON_EXE=

if exist .venv\Scripts\python.exe (
    set PYTHON_EXE=.venv\Scripts\python.exe
)

if not defined PYTHON_EXE if exist venv\Scripts\python.exe (
    set PYTHON_EXE=venv\Scripts\python.exe
)

if not defined PYTHON_EXE (
    echo [ERRO] Ambiente virtual nao encontrado!
    pause
    exit /b 1
)

echo [OK] Python do venv encontrado!

:: API
start "API" cmd /k "%PYTHON_EXE% -m uvicorn app.api.main:app"

timeout /t 2 > nul

:: IA
start "IA" cmd /k "%PYTHON_EXE% scripts/run_local.py"

timeout /t 2 > nul

:: Dashboard
start "Dashboard" cmd /k "%PYTHON_EXE% -m streamlit run app/ui/dashboard.py"

echo Sistema iniciado!
