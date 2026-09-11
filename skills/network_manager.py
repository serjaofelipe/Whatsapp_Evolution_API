import subprocess
import requests
import platform

def get_geolocation_and_ip() -> str:
    try:
        response = requests.get("https://ipinfo.io/json", timeout=10)
        data = response.json()
        result = "=== Geolocalização e IP ===\n"
        result += f"IP Público: {data.get('ip', '?')}\n"
        result += f"Cidade: {data.get('city', '?')}\n"
        result += f"Estado: {data.get('region', '?')}\n"
        result += f"País: {data.get('country', '?')}\n"
        result += f"ISP: {data.get('org', '?')}\n"
        return result
    except Exception as e:
        return f"Erro: {str(e)}"

def run_network_diagnostics() -> str:
    SISTEMA = platform.system()
    result = "=== Diagnóstico de Rede ===\n\n"
    try:
        if SISTEMA == "Windows":
            ping_res = subprocess.run(["ping", "-n", "4", "8.8.8.8"], capture_output=True, text=True)
        else:
            ping_res = subprocess.run(["ping", "-c", "4", "8.8.8.8"], capture_output=True, text=True)
        result += f"[1] Ping:\n{ping_res.stdout.strip()}\n\n"
        if SISTEMA == "Windows":
            net_res = subprocess.run(["netstat", "-an", "-p", "tcp"], capture_output=True, text=True)
        else:
            net_res = subprocess.run(["netstat", "-an"], capture_output=True, text=True)
        lines = net_res.stdout.split("\n")
        established = [l.strip() for l in lines if "ESTABLISHED" in l][:10]
        result += "[2] Conexões Ativas (Top 10):\n" + "\n".join(established) + "\n\n"
        import sys
        speed_res = subprocess.run([sys.executable, "-m", "speedtest", "--simple"], capture_output=True, text=True)
        if speed_res.returncode == 0:
            result += f"[3] SpeedTest:\n{speed_res.stdout.strip()}"
        else:
            result += f"[3] SpeedTest Erro: {speed_res.stderr.strip()}"
        return result
    except Exception as e:
        return f"Erro: {str(e)}"
