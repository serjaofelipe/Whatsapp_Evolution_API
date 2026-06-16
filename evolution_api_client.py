import httpx
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
GLOBAL_API_KEY = os.getenv("AUTHENTICATION_API_KEY", "")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "Atlas")

HEADERS = {
    "apikey": GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

_http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(60.0, connect=10.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    headers=HEADERS
)

def format_jid(phone: str) -> str:
    if "@lid" in phone:
        return phone
    has_plus = phone.strip().startswith('+')
    clean_phone = ''.join(filter(str.isdigit, phone))
    if has_plus:
        return clean_phone
    if len(clean_phone) >= 12:
        return clean_phone
    if len(clean_phone) in [10, 11]:
        return f"55{clean_phone}"
    return clean_phone

async def send_text_message(phone: str, text: str):
    url = f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}"
    jid = phone if "@g.us" in phone else format_jid(phone)
    payload = {"number": jid, "text": text, "delay": 1200}
    try:
        response = await _http_client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"[Evolution API] HTTPStatusError ao enviar mensagem para {phone}: {e} - Resposta: {e.response.text}")
        return None
    except Exception as e:
        print(f"[Evolution API] Erro ao enviar mensagem para {phone}: {e}")
        return None

async def download_media_message(message_id: str) -> str:
    url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{INSTANCE_NAME}"
    payload = {"message": {"key": {"id": message_id}}, "convertToMp4": False}
    try:
        response = await _http_client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("base64", "")
    except Exception as e:
        print(f"[Evolution API] Erro ao baixar mídia: {e}")
        return ""

async def send_media_message(phone: str, file_path: str, mediatype: str = "document", caption: str = ""):
    url = f"{EVOLUTION_API_URL}/message/sendMedia/{INSTANCE_NAME}"
    jid = phone if "@g.us" in phone else format_jid(phone)
    try:
        import mimetypes
        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            file_bytes = await f.read()
            b64_data = base64.b64encode(file_bytes).decode("utf-8")
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        if "image" in mime_type: mediatype = "image"
        elif "video" in mime_type: mediatype = "video"
        elif "audio" in mime_type: mediatype = "audio"
        else: mediatype = "document"
        file_name = Path(file_path).name
        payload = {"number": jid, "mediatype": mediatype, "caption": caption, "media": b64_data, "fileName": file_name}
        async with httpx.AsyncClient(timeout=120.0, headers=HEADERS) as upload_client:
            response = await upload_client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[Evolution API] Erro ao enviar mídia {file_path} para {phone}: {e}")
        return None
