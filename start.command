#!/bin/bash
# ==============================================
# WhatsAjax - Script de inicialização para macOS
# (equivalente ao start.bat do Windows)
#
# Torne executável uma vez com:  chmod +x start.command
# Depois é só dar duplo clique no Finder.
# ==============================================

# Vai para a pasta onde este script está
cd "$(dirname "$0")" || exit 1

echo "=============================================="
echo "[1/4] Verificando o Docker Desktop..."
echo "=============================================="

# Verifica se o Docker está rodando; se não, tenta abrir
if ! docker info >/dev/null 2>&1; then
    echo "Docker nao esta rodando. Tentando abrir o Docker Desktop..."
    open -a Docker 2>/dev/null || echo "AVISO: Docker Desktop nao encontrado. Instale em https://www.docker.com/products/docker-desktop/"

    echo "Aguardando o motor do Docker inicializar..."
    until docker info >/dev/null 2>&1; do
        echo "...ainda aguardando o Docker iniciar..."
        sleep 3
    done
else
    echo "Docker ja esta ativo."
fi

echo ""
echo "=============================================="
echo "[2/4] Verificando portas e subindo os containers..."
echo "=============================================="

# Escolhe portas livres e um nome de projeto proprio desta pasta (grava no .env)
PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python
$PYTHON setup_env.py
case $? in
    0) ;;
    2) echo "Nada a fazer: este bot ja esta aberto em outra janela."; read -r -p "Pressione ENTER para sair..."; exit 0 ;;
    *) echo "ERRO ao preparar o ambiente. Veja a mensagem acima."; read -r -p "Pressione ENTER para sair..."; exit 1 ;;
esac

# Tenta a sintaxe nova; se falhar, tenta a antiga
if ! docker compose up -d; then
    echo "Comando 'docker compose' falhou, tentando 'docker-compose'..."
    docker-compose up -d
fi

echo ""
echo "=============================================="
echo "[3/4] Aguardando banco de dados e Evolution API..."
echo "=============================================="
sleep 8

echo ""
echo "=============================================="
echo "[4/4] Iniciando o Gateway WhatsAjax..."
echo "=============================================="

# Escolhe o interpretador Python disponível
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "ERRO: Python nao encontrado! Instale em https://www.python.org/downloads/"
    read -r -p "Pressione ENTER para sair..."
    exit 1
fi

echo "Verificando dependencias basicas..."
$PYTHON -m pip install -q --disable-pip-version-check -r requirements.txt || echo "AVISO: falha ao instalar dependencias. Veja o erro acima."

echo "Tudo pronto! Iniciando o servidor..."
echo "=============================================="
$PYTHON main.py

echo ""
echo "O bot parou."
read -r -p "Pressione ENTER para fechar..."
