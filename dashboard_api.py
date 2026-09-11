"""
WhatsApp Template Atlas - Dashboard API
=========================================
API REST para o dashboard web: logs, admins, envio de mensagens e edição do .env.
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List

from evolution_api_client import send_text_message, send_media_message

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
ENV_FILE = BASE_DIR / ".env"


class SendMessageRequest(BaseModel):
    number: str
    text: str

class AdminUpdateRequest(BaseModel):
    admins: List[str]
    master_admins: List[str]

class EnvUpdateRequest(BaseModel):
    env_content: str


@router.get("/logs")
async def get_logs():
    """Lê as pastas de log e retorna todas as conversas estruturadas."""
    conversations = {}

    if not LOGS_DIR.exists():
        return {"conversations": []}

    for date_folder in sorted(LOGS_DIR.iterdir(), reverse=True):
        if not date_folder.is_dir():
            continue

        for log_file in date_folder.glob("stealth_log_*.log"):
            sender = log_file.stem.replace("stealth_log_", "")

            if sender not in conversations:
                conversations[sender] = {
                    "id": sender,
                    "name": sender,
                    "messages": [],
                    "last_timestamp": 0
                }

            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            msg_data = json.loads(line)
                            msg_type = msg_data.get("messageType", "")

                            text = ""
                            if msg_type == "conversation":
                                text = msg_data.get("message", {}).get("conversation", "")
                            elif msg_type == "extendedTextMessage":
                                text = msg_data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
                            elif "imageMessage" in msg_type or "videoMessage" in msg_type or "audioMessage" in msg_type:
                                text = f"[{msg_type}]"

                            if text:
                                from_me = msg_data.get("key", {}).get("fromMe", False)
                                timestamp = msg_data.get("messageTimestamp", 0)

                                conversations[sender]["messages"].append({
                                    "text": text,
                                    "fromMe": from_me,
                                    "timestamp": timestamp,
                                    "type": msg_type
                                })

                                if timestamp > conversations[sender]["last_timestamp"]:
                                    conversations[sender]["last_timestamp"] = timestamp
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print(f"Erro ao ler log {log_file}: {e}")

    # Injetar mídias das pastas midias_recebidas
    if LOGS_DIR.exists():
        for date_folder in sorted(LOGS_DIR.iterdir(), reverse=True):
            if not date_folder.is_dir(): continue
            media_dir = date_folder / "midias_recebidas"
            if not media_dir.exists(): continue

            for media_file in media_dir.iterdir():
                if not media_file.is_file(): continue
                parts = media_file.stem.split("_")
                if len(parts) >= 2:
                    sender = parts[0]
                    try:
                        timestamp = int(parts[1])
                    except:
                        timestamp = int(media_file.stat().st_mtime)

                    if sender not in conversations:
                        conversations[sender] = {
                            "id": sender,
                            "name": sender,
                            "messages": [],
                            "last_timestamp": timestamp
                        }

                    ext = media_file.suffix.lower()
                    media_type = "unknown"
                    if ext in ['.jpg', '.jpeg', '.png', '.webp']: media_type = "image"
                    elif ext in ['.mp4', '.avi', '.mov']: media_type = "video"
                    elif ext in ['.ogg', '.mp3', '.wav']: media_type = "audio"
                    elif ext == '.bin': media_type = "document"

                    from_me = "_dashboard" in media_file.name
                    conversations[sender]["messages"].append({
                        "text": f"/logs_media/{date_folder.name}/midias_recebidas/{media_file.name}",
                        "fromMe": from_me,
                        "timestamp": timestamp,
                        "type": f"media_{media_type}"
                    })

                    if timestamp > conversations[sender]["last_timestamp"]:
                        conversations[sender]["last_timestamp"] = timestamp

    # Ordenar mensagens por timestamp
    for sender, data in conversations.items():
        data["messages"].sort(key=lambda x: x["timestamp"])

    sorted_convs = sorted(conversations.values(), key=lambda x: x["last_timestamp"], reverse=True)
    return {"conversations": sorted_convs}


@router.get("/admins")
async def get_admins():
    """Retorna os administradores lidos do .env."""
    admin_str = os.getenv("ADMIN_NUMBERS", "")
    admins = [n.strip() for n in admin_str.split(",") if n.strip()]

    master_str = os.getenv("ADMIN_MASTER_NUMBERS", "")
    master_admins = [n.strip() for n in master_str.split(",") if n.strip()]

    return {"admins": admins, "master_admins": master_admins}


@router.post("/admins")
async def update_admins(req: AdminUpdateRequest):
    """Atualiza a lista de administradores no .env."""
    new_admins_str = ",".join(req.admins)
    new_master_str = ",".join(req.master_admins)
    os.environ["ADMIN_NUMBERS"] = new_admins_str
    os.environ["ADMIN_MASTER_NUMBERS"] = new_master_str

    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            admin_updated = False
            master_updated = False
            for line in lines:
                if line.startswith("ADMIN_NUMBERS="):
                    f.write(f"ADMIN_NUMBERS={new_admins_str}\n")
                    admin_updated = True
                elif line.startswith("ADMIN_MASTER_NUMBERS="):
                    f.write(f"ADMIN_MASTER_NUMBERS={new_master_str}\n")
                    master_updated = True
                else:
                    f.write(line)
            if not admin_updated:
                f.write(f"\nADMIN_NUMBERS={new_admins_str}\n")
            if not master_updated:
                f.write(f"ADMIN_MASTER_NUMBERS={new_master_str}\n")

    return {"success": True, "admins": req.admins, "master_admins": req.master_admins}


@router.get("/env")
async def get_env():
    """Lê o arquivo .env."""
    if not ENV_FILE.exists():
        return {"env_content": ""}
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        return {"env_content": f.read()}


@router.post("/env")
async def update_env(req: EnvUpdateRequest):
    """Atualiza o arquivo .env."""
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(req.env_content)
    return {"success": True}


@router.post("/send")
async def send_dashboard_message(req: SendMessageRequest):
    """Envia uma mensagem de texto via Evolution API."""
    try:
        await send_text_message(req.number, req.text)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send_media")
async def send_dashboard_media(number: str = Form(...), file: UploadFile = File(...)):
    """Salva a mídia localmente e envia via Evolution API."""
    try:
        timestamp = int(datetime.now().timestamp())
        ext = ""
        if file.filename:
            parts = file.filename.rsplit(".", 1)
            if len(parts) > 1:
                ext = f".{parts[1]}"

        save_name = f"{number}_{timestamp}_dashboard{ext}"
        save_path = BASE_DIR / "temp_media" / save_name

        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        await send_media_message(number, str(save_path))

        # Salva cópia na pasta de mídias para aparecer no histórico
        today_str = datetime.now().strftime("%Y-%m-%d")
        dest_dir = LOGS_DIR / today_str / "midias_recebidas"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / save_name
        shutil.copy(save_path, dest_path)

        # Adiciona evento fictício no stealth log
        log_file = LOGS_DIR / today_str / f"stealth_log_{number}.log"
        fake_msg = {
            "messageType": (
                "imageMessage" if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']
                else "videoMessage" if ext.lower() in ['.mp4', '.avi']
                else "audioMessage" if ext.lower() in ['.ogg', '.mp3']
                else "documentMessage"
            ),
            "key": {"fromMe": True, "remoteJid": number},
            "messageTimestamp": timestamp,
            "message": {"conversation": f"[{file.filename}]"}
        }
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(fake_msg, ensure_ascii=False) + "\n")

        return {"success": True, "file": save_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
