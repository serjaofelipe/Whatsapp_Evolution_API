@echo off
title WhatsApp Template Atlas Startup Script
color 0A
chcp 65001 >nul

echo ==============================================
echo [1/4] Iniciando o Docker Desktop...
echo ==============================================

:: Verifica se o Docker Desktop ja esta rodando
tasklist /fi "imagename eq Docker Desktop.exe" | find /i "Docker Desktop.exe" >nul
if errorlevel 1 (
    echo Docker Desktop nao esta rodando. Tentando abrir...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo AVISO: Nao foi possivel encontrar o atalho padrao do Docker Desktop.
        echo Se o Docker ja estiver configurado no WSL ou como servico, aguardaremos...
    )
) else (
    echo Docker Desktop ja esta aberto.
)

echo.
echo Aguardando o motor do Docker inicializar...
:LOOP_DOCKER
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ...ainda aguardando o Docker iniciar (se demorar, abra-o manualmente)...
    goto LOOP_DOCKER
)

echo.
echo ==============================================
echo [2/4] Docker ativo! Subindo os containers...
echo ==============================================
:: Vai para a pasta raiz onde o script .bat esta localizado
cd /d "%~dp0"

:: Tenta rodar docker-compose (ou docker compose)
docker-compose up -d >nul 2>&1
if %errorlevel% neq 0 (
    echo "docker-compose" falhou, tentando "docker compose"...
    docker compose up -d
) else (
    echo Containers iniciados/verificados com sucesso!
)

echo.
echo ==============================================
echo [3/4] Aguardando banco de dados e Evolution API...
echo ==============================================
:: Espera 10 segundos para dar tempo dos containers subirem e estabilizarem
timeout /t 10 /nobreak

echo.
echo ==============================================
echo [4/4] Iniciando o Gateway do WhatsApp...
echo ==============================================
:: Verifica se o Python esta instalado no sistema
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado no sistema!
    echo Certifique-se de que o Python esta instalado e marcado na opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b
)

:: Verifica dependencias
echo Verificando dependencias basicas...
pip install -r requirements.txt >nul 2>&1

:: Executa o bot principal
echo Tudo pronto! Iniciando o servidor...
echo ==============================================
python main.py

echo.
echo O bot parou.
pause
