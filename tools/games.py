import os
import glob
import re
import json
import subprocess

def _get_dir_size_gb(path):
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
                except (OSError, PermissionError): pass
    except (OSError, PermissionError): pass
    return round(total / (1024**3), 2)

def _format_size(gb):
    if gb < 1: return f"{round(gb * 1024)} MB"
    return f"{gb} GB"

def get_installed_games(skip_size=False):
    jogos = []
    steam_paths = [r"C:\Program Files (x86)\Steam\steamapps", r"D:\SteamLibrary\steamapps"]
    for spath in steam_paths:
        if os.path.exists(spath):
            for acf in glob.glob(os.path.join(spath, "appmanifest_*.acf")):
                try:
                    with open(acf, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        name_match = re.search(r'"name"\s+"([^"]+)"', content)
                        size_match = re.search(r'"SizeOnDisk"\s+"(\d+)"', content)
                        installdir_match = re.search(r'"installdir"\s+"([^"]+)"', content)
                        if name_match:
                            app_id = acf.split("_")[-1].replace(".acf", "")
                            size_gb = round(int(size_match.group(1)) / (1024**3), 2) if size_match else 0
                            install_path = os.path.join(spath, "common", installdir_match.group(1)) if installdir_match else ""
                            jogos.append({"nome": name_match.group(1), "plataforma": "Steam", "launch_cmd": f"steam://rungameid/{app_id}", "tamanho_gb": size_gb, "install_path": install_path})
                except: pass
    epic_manifest_dir = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
    if os.path.exists(epic_manifest_dir):
        for item in glob.glob(os.path.join(epic_manifest_dir, "*.item")):
            try:
                with open(item, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    display_name = data.get("DisplayName")
                    app_name = data.get("AppName")
                    install_location = data.get("InstallLocation", "")
                    install_size = data.get("InstallSize", 0)
                    if display_name and app_name:
                        size_gb = round(install_size / (1024**3), 2) if install_size else 0
                        if size_gb == 0 and install_location and os.path.exists(install_location) and not skip_size:
                            size_gb = _get_dir_size_gb(install_location)
                        jogos.append({"nome": display_name, "plataforma": "Epic Games", "launch_cmd": f"com.epicgames.launcher://apps/{app_name}?action=launch&silent=true", "tamanho_gb": size_gb, "install_path": install_location})
            except: pass
    solitaire_app_id = r"shell:appsFolder\Microsoft.MicrosoftSolitaireCollection_8wekyb3d8bbwe!App"
    jogos.append({"nome": "Paciencia (Microsoft Solitaire)", "plataforma": "Microsoft Store", "launch_cmd": f"explorer.exe {solitaire_app_id}", "tamanho_gb": 0.1, "install_path": "Microsoft Store App"})
    return jogos

def get_game_size(game_name):
    jogos = get_installed_games()
    for j in jogos:
        if game_name.lower() in j["nome"].lower():
            return {"nome": j["nome"], "plataforma": j["plataforma"], "tamanho": _format_size(j.get("tamanho_gb", 0)), "tamanho_gb": j.get("tamanho_gb", 0), "install_path": j.get("install_path", "?")}
    return None

def executar_jogo(launch_cmd):
    if launch_cmd.startswith(("steam://", "com.epicgames.launcher://", "uplay://", "minecraft://")):
        os.startfile(launch_cmd)
    else:
        try:
            if ".exe" in launch_cmd:
                parts = launch_cmd.split('"')
                if len(parts) > 1:
                    subprocess.Popen(launch_cmd, shell=True, cwd=os.path.dirname(parts[1]))
                else:
                    subprocess.Popen(launch_cmd, shell=True)
            else:
                subprocess.Popen(launch_cmd, shell=True)
        except Exception as e:
            try: os.startfile(launch_cmd.replace('"', ''))
            except: pass
