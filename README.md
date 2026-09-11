# 🟢 WhatsAjax

Bot WhatsApp com Evolution API e Dashboard Web (visual estilo WhatsApp, com fundo animado em ondas), controlado 100% por comandos (`/code`). Sem uso de APIs de IA. Compatível com **Windows** e **macOS (incluindo Apple Silicon M1/M2)**.

## 📦 Pré-requisitos (Máquina do Zero)

Antes de rodar o projeto em uma máquina nova (Windows ou Mac), você **precisa baixar e instalar**:
1. **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**: É o motor que vai rodar o banco de dados e a Evolution API. Ele **não** vem instalado no computador, precisa baixar e deixar aberto rodando.
2. **[Python 3.10 ou superior](https://www.python.org/downloads/)**: Para rodar o servidor do bot.

## 🚀 Instalação

1. Clone este repositório ou copie a pasta para a máquina.
2. Abra o arquivo `.env` (se não existir, crie a partir do `.env.example`) e preencha suas chaves.
3. Abra o terminal (CMD no Windows ou Terminal no Mac) na pasta do projeto e suba os containers Docker:
   ```bash
   docker-compose up -d
   ```
4. Instale as dependências Python:
   ```bash
   pip install -r requirements.txt
   ```
5. Rode o servidor:
   ```bash
   python main.py
   ```
6. Acesse o Dashboard em `http://localhost:8000/dashboard`
7. Escaneie o QR Code em `http://localhost:8000/qrcode`

### ⚡ Inicialização rápida (um clique)

- **Windows:** dê duplo clique em `start.bat`.
- **macOS:** torne o script executável uma vez e dê duplo clique em `start.command`:
  ```bash
  chmod +x start.command
  ```
  > No macOS, para o `/print` e `/foto` funcionarem, conceda ao Terminal permissão de
  > **Gravação de Tela** e **Câmera** em Ajustes do Sistema → Privacidade e Segurança.

## 📁 Estrutura

- `main.py` - Servidor principal (FastAPI + Uvicorn)
- `whatsbot.py` - Todos os comandos (/code, /print, /foto, /cmd, /jogos, /rede, etc)
- `evolution_api_client.py` - Client da Evolution API
- `dashboard_api.py` - API do Dashboard Web
- `skills/` - Módulos de habilidades (rede, sistema, arquivos, execução Python)
- `tools/` - Módulo de jogos e chamada desktop
- `static/` - Frontend do Dashboard
- `templates/` - Template do QR Code
- `docker-compose.yml` - Docker para Evolution API

## 💬 Comandos

Envie `/code` no WhatsApp (como admin) para ver o menu completo de comandos:
sistema/arquivos, rede/internet, jogos, execução (CMD e Python), controle da
máquina e gestão de contatos/grupos.

## 🖥️ Compatibilidade

- ✅ Windows
- ✅ macOS

## 🔑 APIs Necessárias

- Evolution API (local via Docker)