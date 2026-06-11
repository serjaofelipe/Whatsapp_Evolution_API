import os
from pathlib import Path

def write_to_file(file_path: str, content: str) -> str:
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Arquivo criado: {file_path}"
    except Exception as e:
        return f"Erro: {str(e)}"
