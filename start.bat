@echo off
title WhatsApp Template Atlas Startup Script
color 0A
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================
echo [1/4] Iniciando o Docker Desktop...
echo ==============================================

:: Verifica se o Docker Desktop ja esta rodando
tasklist /fi "imagename eq Docker Desktop.exe" | find /i "Docker Desktop.exe" >nul
if errorlevel 1 (
    echo Docker Desktop nao esta rodando. Tentando abrir...
    if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" (
        start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
    ) else if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo AVISO: Nao foi possivel encontrar o Docker Desktop.
        echo Se o Docker ja estiver configurado no WSL ou como servico, aguardaremos...
    )
) else (
    echo Docker Desktop ja esta aberto.
)

echo.
echo Aguardando o motor do Docker inicializar...
:LOOP_DOCKER
ping 127.0.0.1 -n 4 > nul
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ...ainda aguardando o Docker iniciar - se demorar abra manualmente...
    goto LOOP_DOCKER
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado no sistema!
    echo Certifique-se de que o Python esta instalado e no PATH.
    pause
    exit /b
)

echo.
echo ==============================================
echo [2/4] Docker ativo! Verificando portas e subindo os containers...
echo ==============================================
:: Escolhe portas livres e um nome de projeto proprio desta pasta (grava no .env)
python setup_env.py
if %errorlevel% equ 2 (
    echo.
    echo Nada a fazer: este bot ja esta aberto em outra janela.
    pause
    exit /b
)
if %errorlevel% neq 0 (
    echo ERRO ao preparar o ambiente. Veja a mensagem acima.
    pause
    exit /b
)

:: Tenta rodar docker compose (nova sintaxe)
docker compose up -d
if %errorlevel% neq 0 (
    echo Comando docker compose falhou, tentando docker-compose...
    docker-compose up -d
) else (
    echo Containers iniciados ou atualizados com sucesso!
)

echo.
echo ==============================================
echo [3/4] Aguardando banco de dados e Evolution API...
echo ==============================================
ping 127.0.0.1 -n 10 > nul

echo.
echo ==============================================
echo [4/4] Iniciando o Gateway do WhatsApp...
echo ==============================================
echo Verificando dependencias basicas...
python -m pip install -q --disable-pip-version-check -r requirements.txt
if %errorlevel% neq 0 (
    echo AVISO: falha ao instalar dependencias. Veja o erro acima.
)

echo Tudo pronto! Iniciando o servidor...
echo ==============================================
python main.py

echo.
echo O bot parou.
pause
