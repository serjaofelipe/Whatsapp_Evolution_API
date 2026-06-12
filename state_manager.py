import json
import os
import aiofiles
import asyncio
import time
from typing import Dict, List, Any

HISTORY_FILE = "history.json"
MAX_HISTORY_LEN = 20

_state_lock = asyncio.Lock()

async def load_history() -> Dict[str, Any]:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        async with aiofiles.open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            
            cleaned_data = {}
            current_time = time.time()
            for k, v in data.items():
                if isinstance(v, list):
                    # Migrate old list format to dict with last_active
                    cleaned_data[k] = {"last_active": current_time, "messages": v}
                elif isinstance(v, dict) and "last_active" in v and "messages" in v:
                    # Clean up inactive for 30 days (2592000 seconds)
                    if current_time - v["last_active"] < 2592000:
                        cleaned_data[k] = v
                else:
                    # Keep as is if unknown format
                    cleaned_data[k] = v
            return cleaned_data
    except Exception as e:
        print(f"[StateManager] Erro ao carregar historico: {e}")
        return {}

async def save_history(history: Dict[str, Any]):
    try:
        async with aiofiles.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            content = json.dumps(history, ensure_ascii=False, indent=2)
            await f.write(content)
    except Exception as e:
        print(f"[StateManager] Erro ao salvar historico: {e}")

async def get_messages(remote_jid: str) -> List[Any]:
    async with _state_lock:
        history = await load_history()
        user_data = history.get(remote_jid, {})
        if isinstance(user_data, dict) and "messages" in user_data:
            return user_data["messages"]
        elif isinstance(user_data, list):
            return user_data
        return []

async def set_messages(remote_jid: str, messages: List[Any]):
    async with _state_lock:
        history = await load_history()
        # Mantenha apenas os ultimos N itens para nao estourar o contexto/memoria
        if len(messages) > MAX_HISTORY_LEN:
            # Se tem system prompt no inicio, preserva o indice 0
            if len(messages) > 0 and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                messages = [messages[0]] + messages[-(MAX_HISTORY_LEN-1):]
            else:
                messages = messages[-MAX_HISTORY_LEN:]
                
        history[remote_jid] = {"last_active": time.time(), "messages": messages}
        await save_history(history)
