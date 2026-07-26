@echo off
REM Publica o Ementario num endereco HTTPS publico, para ligar ao ChatGPT.
REM Deixe esta janela aberta enquanto estiver usando o conector.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado em .venv
    echo Rode primeiro:  python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
if not exist "dados\tcerj.sqlite" (
    echo Acervo nao encontrado em dados\tcerj.sqlite - rode a coleta antes.
    pause
    exit /b 1
)
title Ementario - publicado
".venv\Scripts\python.exe" -m ementario.publicar
echo.
echo Encerrado. O endereco publicado deixou de valer.
pause
