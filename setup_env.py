"""
Preparação do ambiente antes de subir o Docker (chamado pelo start.bat / start.command).

- Gera o .env se não existir (chave da Evolution API, portas, nome do projeto).
- Escolhe portas livres: se a porta configurada estiver ocupada por outro
  programa (ou por outra cópia deste bot), usa a próxima livre e grava no .env.
- Dá um nome de projeto Docker próprio para esta pasta, para várias cópias
  rodarem na mesma máquina sem uma "roubar" os containers da outra.
- Avisa se a sessão do WhatsApp foi copiada de outra pasta/máquina.

Só usa a biblioteca padrão (roda antes do pip install).

Códigos de saída: 0 = ok, 2 = este mesmo bot já está rodando, 1 = erro.
"""
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
OWNER_MARKER = ROOT / "evolution_instances" / ".owner"

DEFAULTS = {
    "SERVER_PORT": "8000",
    "EVOLUTION_PORT": "8080",
    "INSTANCE_NAME": "Atlas",
    "ADMIN_NUMBERS": "",
    "ADMIN_MASTER_NUMBERS": "",
    "MESSAGE_MAX_AGE_SECONDS": "1800",
}


# ================= .env =================
def read_env():
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    values = {}
    for line in lines:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    return lines, values


def write_env(lines, updates):
    """Atualiza as chaves existentes no lugar e acrescenta as novas no fim."""
    pending = dict(updates)
    out = []
    for line in lines:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m and m.group(1) in pending:
            out.append(f"{m.group(1)}={pending.pop(m.group(1))}")
        else:
            out.append(line)
    if pending:
        if not out:
            out = [
                "# ==========================================",
                "# GERAÇÃO AUTOMÁTICA DE AMBIENTE (Template)",
                "# ==========================================",
            ]
        out.append("")
        out += [f"{k}={v}" for k, v in pending.items()]
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


# ================= Docker =================
def docker(*args):
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def same_dir(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def project_owner_dirs(project):
    """Pastas de onde vieram os containers que já usam este nome de projeto."""
    out = docker("ps", "-a", "--filter", f"label=com.docker.compose.project={project}",
                 "--format", '{{.Label "com.docker.compose.project.working_dir"}}')
    return {d for d in out.splitlines() if d}


def default_project_name():
    # Mesmo nome que o docker compose usa por padrão (nome da pasta normalizado),
    # assim instalações antigas continuam usando os containers que já existem.
    return re.sub(r"[^a-z0-9_-]", "", ROOT.name.lower()) or "whatsajax"


def choose_project_name(current):
    name = current or default_project_name()
    owners = project_owner_dirs(name)
    if any(not same_dir(d, ROOT) for d in owners):
        # Outra pasta já usa esse nome: cria um nome exclusivo para esta pasta.
        suffix = hashlib.sha1(os.path.normcase(str(ROOT)).encode()).hexdigest()[:6]
        name = f"{default_project_name()}-{suffix}"
        print(f"[setup] Já existe outra cópia do bot com esses containers. Usando o projeto '{name}'.")
    return name


def our_evolution_running(project):
    return bool(docker("ps", "-q", "--filter", f"label=com.docker.compose.project={project}",
                       "--filter", "label=com.docker.compose.service=evolution-api"))


# ================= Portas =================
def port_in_use(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        pass
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        s.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def next_free_port(start, taken):
    port = start
    while port in taken or port_in_use(port):
        port += 1
    return port


def bot_running_here(port):
    """True se quem está na porta é este mesmo bot (mesma pasta)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/instance-info", timeout=2) as r:
            return same_dir(json.load(r).get("base_dir", ""), ROOT)
    except Exception:
        return False


# ================= Sessão copiada =================
def check_session_owner():
    me = f"{socket.gethostname()}|{os.path.normcase(str(ROOT))}"
    if OWNER_MARKER.exists():
        owner = OWNER_MARKER.read_text(encoding="utf-8").strip()
        if owner != me:
            print("=" * 60)
            print("[setup] ATENÇÃO: os dados do WhatsApp desta pasta vieram de outra")
            print(f"        máquina/pasta ({owner.split('|')[0]}).")
            print("        Se a outra cópia continuar rodando com o mesmo número, as")
            print("        duas vão brigar pela sessão. Para começar limpo, apague as")
            print("        pastas evolution_db_data, evolution_instances e")
            print("        evolution_redis_data e leia o QR Code de novo.")
            print("=" * 60)
    OWNER_MARKER.parent.mkdir(parents=True, exist_ok=True)
    OWNER_MARKER.write_text(me, encoding="utf-8")


# ================= Principal =================
def main():
    is_new = not ENV_PATH.exists()
    lines, env = read_env()
    updates = {}

    for key, value in DEFAULTS.items():
        if key not in env:
            updates[key] = value
    if not env.get("AUTHENTICATION_API_KEY"):
        key = secrets.token_hex(16).upper()
        updates["AUTHENTICATION_API_KEY"] = key
        updates["GLOBAL_API_KEY"] = key

    project = choose_project_name(env.get("COMPOSE_PROJECT_NAME"))
    if project != env.get("COMPOSE_PROJECT_NAME"):
        updates["COMPOSE_PROJECT_NAME"] = project

    # Porta do bot: se já é este mesmo bot rodando, não sobe outro.
    server_port = int(env.get("SERVER_PORT") or DEFAULTS["SERVER_PORT"])
    if port_in_use(server_port):
        if bot_running_here(server_port):
            print(f"[setup] Este bot já está rodando em http://localhost:{server_port}/dashboard")
            return 2
        new_port = next_free_port(server_port + 1, set())
        print(f"[setup] Porta {server_port} ocupada por outro programa. Bot vai usar a porta {new_port}.")
        server_port = new_port
    updates["SERVER_PORT"] = str(server_port)

    # Porta da Evolution API: se os nossos containers já estão nela, mantém.
    evo_port = int(env.get("EVOLUTION_PORT") or DEFAULTS["EVOLUTION_PORT"])
    if evo_port == server_port or (port_in_use(evo_port) and not our_evolution_running(project)):
        new_port = next_free_port(evo_port + 1, {server_port})
        print(f"[setup] Porta {evo_port} ocupada. Evolution API vai usar a porta {new_port}.")
        evo_port = new_port
    updates["EVOLUTION_PORT"] = str(evo_port)

    evo_url = env.get("EVOLUTION_API_URL", "")
    if not evo_url or re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?/?$", evo_url):
        updates["EVOLUTION_API_URL"] = f"http://localhost:{evo_port}"

    updates = {k: v for k, v in updates.items() if env.get(k) != v}
    if updates:
        write_env(lines, updates)
        if is_new:
            print("[setup] Arquivo .env criado. Lembre de preencher ADMIN_MASTER_NUMBERS.")

    check_session_owner()
    print(f"[setup] Projeto Docker: {project} | Evolution: {evo_port} | Bot: {server_port}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[setup] ERRO: {e}")
        sys.exit(1)
