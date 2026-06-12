import json
import os
import aiofiles
from typing import Dict, List, Any

HISTORY_FILE = "history.json"
MAX_HISTORY_LEN = 20

async def load_history() -> Dict[str, List[Any]]:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        async with aiofiles.open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        print(f"[StateManager] Erro ao carregar historico: {e}")
        return {}

async def save_history(history: Dict[str, List[Any]]):
    try:
        async with aiofiles.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            content = json.dumps(history, ensure_ascii=False, indent=2)
            await f.write(content)
    except Exception as e:
        print(f"[StateManager] Erro ao salvar historico: {e}")

async def get_messages(remote_jid: str) -> List[Any]:
    history = await load_history()
    return history.get(remote_jid, [])

async def set_messages(remote_jid: str, messages: List[Any]):
    history = await load_history()
    # Mantenha apenas os ultimos N itens para nao estourar o contexto/memoria
    if len(messages) > MAX_HISTORY_LEN:
        # Se tem system prompt no inicio, preserva o indice 0
        if len(messages) > 0 and isinstance(messages[0], dict) and messages[0].get("role") == "system":
            messages = [messages[0]] + messages[-(MAX_HISTORY_LEN-1):]
        else:
            messages = messages[-MAX_HISTORY_LEN:]
            
    history[remote_jid] = messages
    await save_history(history)
