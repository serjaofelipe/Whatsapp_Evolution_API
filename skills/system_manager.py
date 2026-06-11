import os
import psutil
from pathlib import Path
import platform

def bytes_to_gb(bytes_val: int) -> float:
    return round(bytes_val / (1024**3), 2)

def analyze_disks() -> str:
    result = "=== Relatório de Discos ===\n"
    try:
        partitions = psutil.disk_partitions(all=False)
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                result += f"Disco {partition.device} ({partition.fstype}):\n"
                result += f"  Total: {bytes_to_gb(usage.total)} GB\n"
                result += f"  Usado: {bytes_to_gb(usage.used)} GB ({usage.percent}%)\n"
                result += f"  Livre: {bytes_to_gb(usage.free)} GB\n\n"
            except PermissionError:
                result += f"Disco {partition.device}: Acesso Negado.\n\n"
            except Exception as e:
                result += f"Disco {partition.device}: Erro ({str(e)}).\n\n"
        return result
    except Exception as e:
        return f"Erro ao analisar discos: {str(e)}"

def get_dir_size(path: str) -> int:
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try: total_size += os.path.getsize(fp)
                    except (PermissionError, FileNotFoundError): continue
    except Exception: pass
    return total_size

def analyze_folders(path: str) -> str:
    if not os.path.exists(path):
        return f"Erro: O caminho {path} não existe."
    result = f"=== Análise da Pasta: {path} ===\n"
    try:
        subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
        if not subfolders:
            return result + "Nenhuma subpasta encontrada."
        result += f"Total de pastas: {len(subfolders)}\n\n"
        folder_sizes = {}
        for folder in subfolders:
            folder_sizes[folder] = get_dir_size(folder)
        if not folder_sizes:
            return result + "Não foi possível ler o tamanho."
        sorted_folders = sorted(folder_sizes.items(), key=lambda x: x[1])
        result += f"🔥 Mais Pesada: {sorted_folders[-1][0]} com {bytes_to_gb(sorted_folders[-1][1])} GB\n"
        result += f"🪶 Mais Leve: {sorted_folders[0][0]} com {bytes_to_gb(sorted_folders[0][1])} GB\n"
        return result
    except Exception as e:
        return f"Erro: {str(e)}"

def open_url(url: str) -> str:
    try:
        import webbrowser
        webbrowser.open(url)
        return f"URL aberta: {url}"
    except Exception as e:
        return f"Erro ao abrir URL: {str(e)}"

def get_hardware_specs() -> str:
    try:
        import subprocess
        os_info = f"OS: {platform.system()} {platform.release()} ({platform.version()})"
        cpu_info = f"Processador: {platform.processor()}"
        cpu_cores = f"Núcleos: {psutil.cpu_count(logical=False)} Físicos / {psutil.cpu_count(logical=True)} Lógicos"
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        ram_info = f"RAM Total: {ram_gb} GB"
        gpu_info = "GPU: Não identificada"
        try:
            if platform.system() == "Windows":
                gpu_cmd = subprocess.run(["powershell", "-Command", "(Get-CimInstance Win32_VideoController).Name"], capture_output=True, text=True, timeout=5)
            else:
                gpu_cmd = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=5)
            if gpu_cmd.stdout.strip():
                gpu_info = f"GPU: {gpu_cmd.stdout.strip().split(chr(10))[0]}"
        except: pass
        return f"=== Hardware ===\n{os_info}\n{cpu_info}\n{cpu_cores}\n{ram_info}\n{gpu_info}"
    except Exception as e:
        return f"Erro: {str(e)}"
