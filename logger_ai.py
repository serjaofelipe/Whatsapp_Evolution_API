import os
import aiofiles
import asyncio
from datetime import datetime

LOG_FILE = "usage_ai.log"
_log_lock = asyncio.Lock()

async def log_ai_usage(remote_jid: str, ai_model: str, action: str, details: str = ""):
    """Registra uso da IA para monitoramento e controle de custos."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{remote_jid}] [{ai_model}] {action}"
    if details:
        log_line += f" | {details}"
    
    try:
        async with _log_lock:
            async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
                await f.write(log_line + "\n")
    except Exception as e:
        print(f"[Logger] Falha ao escrever log: {e}")
