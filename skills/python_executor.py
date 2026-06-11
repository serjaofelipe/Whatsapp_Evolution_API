import os
import subprocess
from pathlib import Path

BASE_PROJECTS_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "projects"

def run_dynamic_script(code: str, project_name: str = "Script_Avulso") -> str:
    try:
        BASE_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        project_dir = BASE_PROJECTS_DIR / project_name.replace(" ", "_")
        project_dir.mkdir(parents=True, exist_ok=True)
        script_path = project_dir / "main.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        result = subprocess.run(["python", "main.py"], cwd=str(project_dir), capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        err = result.stderr.strip()
        if len(output) > 2000: output = output[:2000] + "\n...[TRUNCADO]"
        if len(err) > 2000: err = err[:2000] + "\n...[TRUNCADO]"
        final = f"Script executado: {script_path}\n"
        if err: final += f"Erros:\n{err}\n"
        if output: final += f"Saída:\n{output}\n"
        if not output and not err: final += "Sem saída."
        return final
    except subprocess.TimeoutExpired:
        return "Timeout (120s)."
    except Exception as e:
        return f"Erro: {str(e)}"
