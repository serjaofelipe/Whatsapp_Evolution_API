import json
import os
from typing import Dict, List, Any

HISTORY_FILE = "history.json"
MAX_HISTORY_LEN = 20

def load_history() -> Dict[str, List[Any]]:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[StateManager] Erro ao carregar historico: {e}")
        return {}

def save_history(history: Dict[str, List[Any]]):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[StateManager] Erro ao salvar historico: {e}")

def get_messages(remote_jid: str) -> List[Any]:
    history = load_history()
    return history.get(remote_jid, [])

def set_messages(remote_jid: str, messages: List[Any]):
    history = load_history()
    # Mantenha apenas os ultimos N itens para nao estourar o contexto/memoria
    if len(messages) > MAX_HISTORY_LEN:
        # Se tem system prompt no inicio, preserva o indice 0
        if len(messages) > 0 and isinstance(messages[0], dict) and messages[0].get("role") == "system":
            messages = [messages[0]] + messages[-(MAX_HISTORY_LEN-1):]
        else:
            messages = messages[-MAX_HISTORY_LEN:]
            
    history[remote_jid] = messages
    save_history(history)
