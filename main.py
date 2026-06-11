"""
WhatsApp Template Atlas - Servidor Principal
=============================================
Servidor FastAPI que recebe webhooks da Evolution API,
roteia comandos para o WhatsBot e mensagens para o Assistente IA.

Compatível com Windows e macOS.
"""
import asyncio
import os
import sys
import json
import time
import base64
import uuid
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

import secrets
from dotenv import load_dotenv

# Auto-geração do .env antes das importações locais
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
if not env_path.exists():
    new_key = secrets.token_hex(16).upper()
    default_env = f"""# ==========================================
# GERAÇÃO AUTOMÁTICA DE AMBIENTE (Template)
# ==========================================

# Evolution API
SERVER_PORT=8000
EVOLUTION_API_URL=http://localhost:8080
INSTANCE_NAME=Atlas
AUTHENTICATION_API_KEY={new_key}
GLOBAL_API_KEY={new_key}

# WhatsApp Admins
ADMIN_NUMBERS=
ADMIN_MASTER_NUMBERS=

# LLM APIs
GROQ_API_KEY=
GOOGLE_API_KEY=
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(default_env)
    print("\n" + "="*50)
    print("✅ ARQUIVO .env GERADO AUTOMATICAMENTE!")
    print(f"🔑 Evolution API Key: {new_key}")
    
    print("🔄 Reiniciando container da Evolution API para aplicar a chave...")
    import subprocess
    try:
        subprocess.run(["docker-compose", "down"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker-compose", "up", "-d"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Docker reiniciado com sucesso com a nova chave!")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível reiniciar o Docker automaticamente: {e}")
        print("   Por favor, abra outro terminal e rode manualmente:")
        print("   docker-compose down")
        print("   docker-compose up -d")
    print("="*50 + "\n")

load_dotenv()

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import aiofiles

from evolution_api_client import (
    send_text_message, download_media_message,
    EVOLUTION_API_URL, INSTANCE_NAME, GLOBAL_API_KEY
)
from assistant import process_assistant_request, get_groq_client
from whatsbot import process_whatsbot_command
from dashboard_api import router as dashboard_router


# ================= CONFIGURAÇÕES =================
BASE_DIR = Path(__file__).resolve().parent
BASE_TEMP_DIR = BASE_DIR / "temp_media"
BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_NUMBERS_ENV = os.getenv("ADMIN_NUMBERS", "")
ADMIN_NUMBERS = [n.strip() for n in ADMIN_NUMBERS_ENV.split(",") if n.strip()]

ADMIN_MASTER_NUMBERS_ENV = os.getenv("ADMIN_MASTER_NUMBERS", "")
ADMIN_MASTER_NUMBERS = [n.strip() for n in ADMIN_MASTER_NUMBERS_ENV.split(",") if n.strip()]

# Junta todos os admins em uma lista única para verificação
ALL_ADMINS = list(set(ADMIN_NUMBERS + ADMIN_MASTER_NUMBERS))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# QR Code Cache
latest_qr_base64 = None

# Deduplicador de mensagens O(1) com set + deque limitado
_processed_ids_set = set()
_processed_ids_queue = deque(maxlen=500)

# Vision states (para perguntas ambíguas tela/câmera)
vision_states = {}


# ================= LIFESPAN =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("🚀 WhatsApp Template Atlas - Iniciando...")
    print(f"📡 Evolution API: {EVOLUTION_API_URL}")
    print(f"📋 Instância: {INSTANCE_NAME}")
    print(f"👑 Master Admins: {ADMIN_MASTER_NUMBERS}")
    print(f"👤 Admins: {ADMIN_NUMBERS}")
    print("=" * 50)

    # Envia mensagem de boas-vindas para admins masters
    async def send_startup():
        await asyncio.sleep(3)  # Espera a Evolution API estar pronta
        for admin in ADMIN_MASTER_NUMBERS:
            try:
                await send_text_message(admin, "✅ *Atlas Template* está online e operacional!")
            except Exception as e:
                print(f"[Startup] Erro ao enviar mensagem para {admin}: {e}")

    asyncio.create_task(send_startup())
    yield
    print("🛑 WhatsApp Template Atlas - Encerrando...")


# ================= APP =================
app = FastAPI(title="WhatsApp Template Atlas", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montagem de arquivos estáticos
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/media", StaticFiles(directory=str(BASE_TEMP_DIR)), name="media")
app.mount("/logs_media", StaticFiles(directory=str(LOGS_DIR)), name="logs_media")

app.include_router(dashboard_router)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ================= ROTAS WEB =================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return HTMLResponse(content=open(static_dir / "index.html", encoding="utf-8").read())

from fastapi import Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/qrcode", response_class=HTMLResponse)
async def qrcode_page(request: Request):
    return templates.TemplateResponse(request=request, name="qrcode.html", context={"request": request})

@app.get("/api/qr")
async def get_qr():
    global latest_qr_base64
    if latest_qr_base64:
        return {"base64": latest_qr_base64}

    import httpx
    url = f"{EVOLUTION_API_URL}/instance/connect/{INSTANCE_NAME}"
    headers = {"apikey": GLOBAL_API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            data = response.json()
            if data.get("base64"):
                latest_qr_base64 = data.get("base64")
                return {"base64": latest_qr_base64}
            elif data.get("qrcode", {}).get("base64"):
                latest_qr_base64 = data.get("qrcode").get("base64")
                return {"base64": latest_qr_base64}
            return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/status")
async def get_status():
    import httpx
    url = f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}"
    headers = {"apikey": GLOBAL_API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/logout")
async def logout_instance():
    import httpx
    url = f"{EVOLUTION_API_URL}/instance/logout/{INSTANCE_NAME}"
    headers = {"apikey": GLOBAL_API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            global latest_qr_base64
            latest_qr_base64 = None
            return response.json()
    except Exception as e:
        return {"error": str(e)}


# ================= STEALTH LOGGER =================
async def process_stealth_message(message_data, remote_jid, text, img_path):
    """Salva logs de todas as mensagens recebidas em formato JSONL."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = LOGS_DIR / today
    media_dir = log_dir / "midias_recebidas"
    log_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    sender_clean = re.sub(r'[^a-zA-Z0-9]', '_', remote_jid.split('@')[0])

    # Salva log JSONL
    log_file = log_dir / f"stealth_log_{sender_clean}.log"
    async with aiofiles.open(log_file, mode="a", encoding="utf-8") as f:
        await f.write(json.dumps(message_data, ensure_ascii=False) + "\n")

    # Salva mídia inline (base64)
    if img_path and "temp_media" in str(img_path):
        import shutil
        timestamp = int(time.time())
        dest_path = media_dir / f"{sender_clean}_{timestamp}_thumb.jpg"
        shutil.copy(img_path, dest_path)

    # Download sob demanda de mídias via Evolution API
    try:
        msg_obj = message_data.get("message", {})
        message_id = message_data.get("key", {}).get("id")
        has_media = any(k in msg_obj for k in ["imageMessage", "videoMessage", "audioMessage", "documentMessage", "stickerMessage"])

        if has_media and message_id:
            b64_data = await download_media_message(message_id)
            if b64_data:
                ext = "bin"
                if "imageMessage" in msg_obj: ext = "jpg"
                elif "videoMessage" in msg_obj: ext = "mp4"
                elif "audioMessage" in msg_obj: ext = "ogg"
                elif "stickerMessage" in msg_obj: ext = "webp"
                elif "documentMessage" in msg_obj:
                    filename = msg_obj["documentMessage"].get("fileName", "")
                    mimetype = msg_obj["documentMessage"].get("mimetype", "")
                    if "audio" in mimetype:
                        ext = "ogg"
                    else:
                        ext = filename.split(".")[-1] if "." in filename else "bin"

                timestamp = int(time.time())
                file_path = media_dir / f"{sender_clean}_{timestamp}_{message_id[:6]}.{ext}"
                media_bytes = base64.b64decode(b64_data)
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(media_bytes)
    except Exception as e:
        print(f"Erro ao salvar mídia: {e}")


# ================= PROCESSADOR DE ADMIN =================
async def process_admin_message(remote_jid, text, img_path):
    """Processa mensagem de um admin autorizado."""
    try:
        # 1. Transcreve áudio com Whisper (via Groq) se for .ogg
        if img_path and str(img_path).endswith('.ogg'):
            groq_client = get_groq_client()
            if groq_client:
                await send_text_message(remote_jid, "🎤 Ouvindo áudio com Whisper...")
                with open(img_path, "rb") as f:
                    transcription = await groq_client.audio.transcriptions.create(
                        file=(img_path, f.read()),
                        model="whisper-large-v3",
                        response_format="text"
                    )
                transcribed_text = str(transcription).strip()
                print(f"🎤 [WHISPER] Áudio transcrito: '{transcribed_text}'")

                if not text or text.startswith("[Mídia"):
                    text = transcribed_text
                else:
                    text = f"{text}\n[Áudio transcrito: {transcribed_text}]"
                img_path = None

        lower_text = text.lower() if text else ""

        # 2. Interceptador de Visão (tela/câmera)
        import unicodedata
        def remover_acentos(txt):
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

        v_msg = remover_acentos(lower_text)

        if vision_states.get(remote_jid):
            if "tela" in v_msg:
                vision_states[remote_jid] = False
                async def _screen():
                    await send_text_message(remote_jid, "📸 Capturando tela...")
                    from skills.vision_manager import analyze_computer_screen
                    res = await asyncio.to_thread(analyze_computer_screen, "Descreva detalhadamente a tela.")
                    await send_text_message(remote_jid, res)
                asyncio.create_task(_screen())
                return
            elif any(w in v_msg for w in ["camera", "cam", "webcam"]):
                vision_states[remote_jid] = False
                async def _cam():
                    await send_text_message(remote_jid, "📸 Capturando foto da webcam...")
                    from skills.vision_manager import analyze_computer_webcam
                    res = await asyncio.to_thread(analyze_computer_webcam, "Descreva detalhadamente a foto.")
                    await send_text_message(remote_jid, res)
                asyncio.create_task(_cam())
                return
            vision_states[remote_jid] = False

        # Triggers de visão direta
        triggers_tela = ["analise a minha tela", "analisa minha tela", "veja a tela", "olha a tela",
                         "tire um print", "tira print", "leia minha tela", "manda print"]
        triggers_camera = ["analise a minha camera", "tire uma foto", "tira foto", "webcam",
                           "ligue a camera", "olha a camera", "veja a camera"]
        triggers_ambiguos = ["o q vc ve", "o que vc ve", "o que voce ve", "o que esta vendo",
                             "analisa", "analise", "oque vc ve"]

        if any(f in v_msg for f in triggers_tela):
            async def _screen_direct():
                await send_text_message(remote_jid, "📸 Capturando tela...")
                from skills.vision_manager import analyze_computer_screen
                res = await asyncio.to_thread(analyze_computer_screen, "Descreva detalhadamente a tela.")
                await send_text_message(remote_jid, res)
            asyncio.create_task(_screen_direct())
            return

        if any(f in v_msg for f in triggers_camera):
            async def _cam_direct():
                await send_text_message(remote_jid, "📸 Capturando foto da webcam...")
                from skills.vision_manager import analyze_computer_webcam
                res = await asyncio.to_thread(analyze_computer_webcam, "Descreva detalhadamente a foto.")
                await send_text_message(remote_jid, res)
            asyncio.create_task(_cam_direct())
            return

        if any(v_msg.startswith(f) or v_msg == f for f in triggers_ambiguos):
            vision_states[remote_jid] = True
            await send_text_message(remote_jid, "Você quer que eu analise a sua *tela* ou a sua *câmera*?")
            return

        # 3. Tenta comandos hardcoded do WhatsBot (/code, /print, /foto, etc.)
        if text and text.strip().startswith("/"):
            handled = await process_whatsbot_command(remote_jid, text)
            if handled:
                return

        # 4. Tudo o resto vai para o Assistente IA (Groq + Gemini)
        await process_assistant_request(remote_jid, text=text, media_path=img_path)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            await send_text_message(remote_jid, "⏳ *Limite atingido!* Aguarde 1 minuto.")
        else:
            print(f"Erro no process_admin_message: {e}")
            await send_text_message(remote_jid, f"Erro interno: {e}")


# ================= WEBHOOK PRINCIPAL =================
@app.post("/webhook/evolution/{path:path}")
@app.post("/webhook/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks, path: str = ""):
    global latest_qr_base64
    try:
        payload = await request.json()

        # Log assíncrono de debug
        async def _log_debug(p):
            try:
                async with aiofiles.open("webhook_debug.log", "a", encoding="utf-8") as f:
                    await f.write(json.dumps(p, ensure_ascii=False) + "\n\n")
            except Exception:
                pass
        asyncio.create_task(_log_debug(payload))

        event_type = payload.get("event")

        # QR Code atualizado
        if event_type == "qrcode.updated":
            base64_qr = payload.get("data", {}).get("qrcode", {}).get("base64")
            if base64_qr:
                latest_qr_base64 = base64_qr
                print("✅ QR Code atualizado via Webhook!")
            return {"status": "ok"}

        # Conexão atualizada
        if event_type == "connection.update":
            state = payload.get("data", {}).get("state")
            if state == "open":
                latest_qr_base64 = None
            return {"status": "ok"}

        # Ignora tudo que não for message upsert
        if event_type != "messages.upsert":
            return {"status": "ignored", "reason": "not messages.upsert"}

        data = payload.get("data", {})
        message_info = data.get("message", {})

        # Extrai texto antecipadamente para checar se é um comando
        conversation = message_info.get("conversation")
        extended_text = message_info.get("extendedTextMessage", {}).get("text")
        image_caption = message_info.get("imageMessage", {}).get("caption")
        temp_text = conversation or extended_text or image_caption or ""

        # Ignora mensagens enviadas por nós mesmos, a menos que seja um comando explícito
        if data.get("key", {}).get("fromMe"):
            if not temp_text.strip().startswith("/"):
                return {"status": "ignored", "reason": "from_me_not_command"}

        message_id = data.get("key", {}).get("id")

        # Deduplicação O(1)
        if message_id:
            if message_id in _processed_ids_set:
                return {"status": "ignored", "reason": "duplicate_message"}
            if len(_processed_ids_queue) >= _processed_ids_queue.maxlen:
                oldest = _processed_ids_queue[0]
                _processed_ids_set.discard(oldest)
            _processed_ids_queue.append(message_id)
            _processed_ids_set.add(message_id)

        remote_jid = data.get("key", {}).get("remoteJid", "")
        sender_pn = data.get("key", {}).get("senderPn")

        # Resolve @lid para número real
        if sender_pn and "@lid" in remote_jid:
            remote_jid = sender_pn

        if "@s.whatsapp.net" in remote_jid:
            remote_jid = remote_jid.replace("@s.whatsapp.net", "")

        if not remote_jid or "status@broadcast" in remote_jid:
            return {"status": "ignored", "reason": "invalid_jid"}

        # Extrai texto da mensagem
        conversation = message_info.get("conversation")
        extended_text = message_info.get("extendedTextMessage", {}).get("text")
        image_caption = message_info.get("imageMessage", {}).get("caption")
        msg_text = conversation or extended_text or image_caption or ""

        # Extrai mídia inline (base64)
        img_path = None
        contact_clean = re.sub(r'[^a-zA-Z0-9]', '_', remote_jid.split('@')[0])
        base64_data = data.get("message", {}).get("base64")
        if base64_data:
            img_bytes = base64.b64decode(base64_data)
            today_str = datetime.now().strftime("%Y-%m-%d")
            f_path = LOGS_DIR / today_str / "midias_recebidas"
            f_path.mkdir(parents=True, exist_ok=True)
            img_file = f_path / f"{contact_clean}_{int(time.time())}_{uuid.uuid4().hex[:4]}_thumb.jpg"
            with open(img_file, "wb") as f:
                f.write(img_bytes)
            img_path = str(img_file)
            if not msg_text:
                msg_text = "[Mídia Base64 Inline]"

        # Verifica se não tem texto nem mídia
        if not msg_text and not img_path:
            keys = data.get("message", {}).keys()
            if "reactionMessage" in keys or "protocolMessage" in keys:
                return {"status": "ignored", "reason": "system_or_reaction_message"}
            if any("Message" in k for k in keys):
                msg_text = f"[Mídia: {list(keys)}]"
            else:
                return {"status": "ignored", "reason": "empty_text_and_media"}

        is_group = "@g.us" in remote_jid
        clean_number = ''.join(filter(str.isdigit, remote_jid))

        # Sempre salva no stealth log
        background_tasks.add_task(process_stealth_message, data, remote_jid, msg_text, img_path)

        # Timeout: ignora mensagens com mais de 1 hora
        msg_timestamp = data.get("messageTimestamp")
        if msg_timestamp:
            diff = int(time.time()) - int(msg_timestamp)
            if diff > 3600:
                print(f"[TIMEOUT] Mensagem ignorada ({diff}s atrás). Remetente: {clean_number}")
                return {"status": "ignored", "reason": "message_too_old"}

        # Verifica se é admin
        is_admin = any(admin in clean_number for admin in ALL_ADMINS)

        # Se não for admin, envia mensagem padrão (personalize aqui!)
        if not is_admin and not is_group:
            background_tasks.add_task(
                send_text_message, remote_jid,
                "👋 Olá! Este é um assistente privado. Entre em contato pelo número oficial."
            )
            return {"status": "success", "reason": "unauthorized_redirected"}

        # Ignora grupos
        if is_group:
            return {"status": "success"}

        # Processa mensagem de admin em paralelo
        async def background_admin(r_jid, text_content, initial_img, msg_id_val, m_info, c_clean):
            try:
                final_img = initial_img
                has_m = any(k in m_info for k in ["imageMessage", "videoMessage", "audioMessage", "documentMessage", "stickerMessage"])

                # Download de mídia sob demanda
                if has_m and not final_img and msg_id_val:
                    try:
                        b64 = await asyncio.wait_for(download_media_message(msg_id_val), timeout=30)
                    except asyncio.TimeoutError:
                        print(f"[TIMEOUT] Download de mídia expirou: {msg_id_val}")
                        b64 = ""
                    if b64:
                        ext = "bin"
                        if "imageMessage" in m_info: ext = "jpg"
                        elif "videoMessage" in m_info: ext = "mp4"
                        elif "audioMessage" in m_info: ext = "ogg"
                        elif "documentMessage" in m_info:
                            mime = m_info["documentMessage"].get("mimetype", "")
                            if "audio" in mime: ext = "ogg"
                            else:
                                fn = m_info["documentMessage"].get("fileName", "")
                                ext = fn.split(".")[-1] if "." in fn else "bin"

                        today_s = datetime.now().strftime("%Y-%m-%d")
                        f_dir = LOGS_DIR / today_s / "midias_recebidas"
                        f_dir.mkdir(parents=True, exist_ok=True)
                        final_img = str(f_dir / f"{c_clean}_{int(time.time())}_{uuid.uuid4().hex[:4]}.{ext}")
                        media_bytes = base64.b64decode(b64)
                        async with aiofiles.open(final_img, "wb") as fw:
                            await fw.write(media_bytes)

                await process_admin_message(r_jid, text_content, final_img)
            except Exception as e:
                print(f"[ERRO] Background admin: {e}")
                await send_text_message(r_jid, f"⚠️ Erro: {e}")

        asyncio.create_task(
            background_admin(remote_jid, msg_text, img_path, message_id, message_info, contact_clean)
        )

        return {"status": "success"}

    except Exception as e:
        print(f"Erro no webhook: {e}")
        return {"status": "error", "detail": str(e)}


# ================= INICIALIZAÇÃO =================
if __name__ == "__main__":
    print(f"🌐 Servidor rodando em http://0.0.0.0:{SERVER_PORT}")
    print(f"📊 Dashboard: http://localhost:{SERVER_PORT}/dashboard")
    print(f"📱 QR Code:   http://localhost:{SERVER_PORT}/qrcode")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
