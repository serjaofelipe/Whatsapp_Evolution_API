"""
WhatsApp Template Atlas - WhatsBot
====================================
Comandos hardcoded (/code, /print, /foto, /cmd, etc.)
Compatível com Windows e macOS.
"""
import os
import time
import socket
import pyautogui
import cv2
import subprocess
import urllib.parse
import platform
from datetime import datetime

from evolution_api_client import send_text_message, send_media_message

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
SISTEMA = platform.system()  # 'Windows' ou 'Darwin' (Mac)


def obter_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


async def process_whatsbot_command(remote_jid: str, text: str) -> bool:
    """
    Roteador de comandos hardcoded. Retorna True se interceptou, False se não.
    """
    comando_texto = text.strip()
    if not comando_texto.startswith("/"):
        return False

    partes = comando_texto.split(" ", 1)
    comando_base = partes[0].lower()
    argumento = partes[1] if len(partes) > 1 else ""

    comandos_validos = [
        '/windows', '/code', '/mac', '/ip', '/stop', '/print', '/foto',
        '/msg', '/search', '/searchlink', '/cmd', '/bloquear', '/panico',
        '/desligar', '/reiniciar', '/suspender', '/pastas', '/enviar',
        '/mirror', '/executar'
    ]

    if comando_base not in comandos_validos:
        return False

    try:
        if comando_base in ['/windows', '/code']:
            await send_text_message(remote_jid,
                "🪟 *MENU WINDOWS ATIVADO!*\n\n"
                "📝 *Sistema e Arquivos:*\n"
                "/pastas [local] - Listar discos ou arquivos\n"
                "/enviar [arquivo] - Baixar arquivo\n"
                "/executar [comando] - Rodar no Win+R\n"
                "/mirror - Espelhamento ESP32 S3\n\n"
                "📝 *Controle:*\n"
                "/ip - Ver endereço IP\n"
                "/stop [ip] - Parar o bot\n"
                "/print - Print da tela\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Aviso na tela\n"
                "/search [pesq] | /searchlink [link]\n"
                "/cmd [comando] - Rodar no CMD\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "🔄 Mudar para Mac: /mac"
            )

        elif comando_base == '/mac':
            await send_text_message(remote_jid,
                "🍎 *MENU MAC OS ATIVADO!*\n\n"
                "📝 *Sistema e Arquivos:*\n"
                "/pastas [local] - Listar volumes ou arquivos\n"
                "/enviar [arquivo] - Baixar arquivo\n"
                "/executar [pesquisa] - Abrir no Spotlight\n\n"
                "📝 *Controle:*\n"
                "/ip - Ver endereço IP\n"
                "/stop [ip] - Parar o bot\n"
                "/print - Print da tela\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Aviso na tela\n"
                "/search [pesq] | /searchlink [link]\n"
                "/cmd [comando] - Rodar no Terminal\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "🔄 Mudar para Windows: /windows"
            )

        elif comando_base == '/ip':
            ip_local = obter_ip_local()
            await send_text_message(remote_jid, f"📡 IP Local ({SISTEMA}): {ip_local}")

        elif comando_base == '/stop':
            if argumento:
                ip_alvo = argumento.strip()
                ip_local = obter_ip_local()
                if ip_alvo == ip_local:
                    await send_text_message(remote_jid, f"🛑 Parando o bot em {SISTEMA} (IP: {ip_local})...")
                    os._exit(0)
            else:
                await send_text_message(remote_jid, "⚠️ Use: /stop <ip>")

        elif comando_base == '/print':
            await send_text_message(remote_jid, f"📸 Tirando print do {SISTEMA}...")
            caminho = os.path.join(PASTA_RAIZ, "print_temp.png")
            screenshot = pyautogui.screenshot()
            screenshot.save(caminho)
            await send_media_message(remote_jid, caminho, "image", "📸 Print capturado!")
            if os.path.exists(caminho): os.remove(caminho)

        elif comando_base == '/foto':
            await send_text_message(remote_jid, f"🕵️ Capturando webcam do {SISTEMA}...")
            caminho = os.path.join(PASTA_RAIZ, f"webcam_temp_{int(time.time())}.jpg")
            cam = None
            try:
                cam = cv2.VideoCapture(0, cv2.CAP_DSHOW) if SISTEMA == "Windows" else cv2.VideoCapture(0)
                if not cam.isOpened():
                    cam = cv2.VideoCapture(0)
                if cam.isOpened():
                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        cam.read()
                    ret, frame = cam.read()
                    if ret:
                        cv2.imwrite(caminho, frame)
                        cam.release()
                        await send_media_message(remote_jid, caminho, "image", "🕵️ Foto da webcam!")
                    else:
                        await send_text_message(remote_jid, "❌ Falha ao capturar imagem.")
                else:
                    await send_text_message(remote_jid, "❌ Câmera inacessível.")
            except Exception as e:
                await send_text_message(remote_jid, f"❌ Erro na câmera: {e}")
            finally:
                if cam is not None and cam.isOpened(): cam.release()
                if os.path.exists(caminho):
                    try: os.remove(caminho)
                    except: pass

        elif comando_base == '/msg':
            if argumento:
                await send_text_message(remote_jid, f"Exibindo alerta no {SISTEMA}...")
                pyautogui.alert(text=argumento, title='MENSAGEM DO DONO', button='OK')
            else:
                await send_text_message(remote_jid, "⚠️ Use: /msg <texto>")

        elif comando_base == '/search':
            if argumento:
                query = urllib.parse.quote(argumento)
                url = f"https://www.google.com/search?q={query}"
                if SISTEMA == "Windows":
                    os.system(f'start chrome "{url}"')
                elif SISTEMA == "Darwin":
                    os.system(f'open -a "Google Chrome" "{url}"')
                await send_text_message(remote_jid, f"🔍 Pesquisando: {argumento}")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /search <pesquisa>")

        elif comando_base == '/searchlink':
            if argumento:
                link = argumento if argumento.startswith("http") else "http://" + argumento
                if SISTEMA == "Windows":
                    os.system(f'start chrome "{link}"')
                elif SISTEMA == "Darwin":
                    os.system(f'open -a "Google Chrome" "{link}"')
                await send_text_message(remote_jid, f"🌐 Abrindo: {link}")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /searchlink <link>")

        elif comando_base == '/cmd':
            if argumento:
                try:
                    out_bytes = subprocess.check_output(argumento, shell=True, stderr=subprocess.STDOUT)
                    try:
                        resultado = out_bytes.decode('cp850')
                    except UnicodeDecodeError:
                        try:
                            resultado = out_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            resultado = out_bytes.decode('cp1252', errors='replace')
                            
                    if len(resultado) > 4000: resultado = resultado[:4000] + "\n...[Cortado]"
                    await send_text_message(remote_jid, f"💻 *Resultado:*\n```\n{resultado}\n```")
                except subprocess.CalledProcessError as e:
                    out_bytes = e.output
                    try:
                        resultado = out_bytes.decode('cp850')
                    except:
                        resultado = out_bytes.decode('utf-8', errors='replace')
                    await send_text_message(remote_jid, f"⚠️ *Erro:*\n```\n{resultado}\n```")
            else:
                await send_text_message(remote_jid, "🖥️ Use: /cmd <comando>")

        elif comando_base == '/bloquear':
            await send_text_message(remote_jid, f"🔒 Bloqueando {SISTEMA}...")
            if SISTEMA == "Windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif SISTEMA == "Darwin":
                os.system('pmset displaysleepnow')

        elif comando_base == '/panico':
            await send_text_message(remote_jid, f"🙈 Modo Pânico no {SISTEMA}!")
            if SISTEMA == "Windows":
                pyautogui.hotkey('win', 'd')
                pyautogui.press('volumemute')
            elif SISTEMA == "Darwin":
                pyautogui.hotkey('command', 'f3')
                os.system("osascript -e 'set volume output muted true'")

        elif comando_base == '/desligar':
            await send_text_message(remote_jid, f"💀 Desligando {SISTEMA}...")
            if SISTEMA == "Windows":
                os.system("shutdown /s /t 5")
            elif SISTEMA == "Darwin":
                os.system("""osascript -e 'tell app "System Events" to shut down'""")

        elif comando_base == '/reiniciar':
            await send_text_message(remote_jid, f"🔄 Reiniciando {SISTEMA}...")
            if SISTEMA == "Windows":
                os.system("shutdown /r /t 5")
            elif SISTEMA == "Darwin":
                os.system("""osascript -e 'tell app "System Events" to restart'""")

        elif comando_base == '/suspender':
            await send_text_message(remote_jid, f"💤 Suspendendo {SISTEMA}...")
            if SISTEMA == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif SISTEMA == "Darwin":
                os.system("pmset sleepnow")

        elif comando_base == '/pastas':
            if not argumento:
                if SISTEMA == "Windows":
                    drives = [chr(x) + ":\\" for x in range(65, 91) if os.path.exists(chr(x) + ":")]
                    resposta = "💽 *Discos disponíveis:*\n" + "\n".join(drives)
                else:
                    pastas = os.listdir('/Volumes/')
                    resposta = "💽 *Volumes (Mac):*\n" + "\n".join(pastas)
                await send_text_message(remote_jid, resposta + "\n\nExemplo: /pastas C:\\")
            else:
                caminho = argumento
                try:
                    itens = os.listdir(caminho)
                    pastas_list = [f"📁 `{item}`" for item in itens if os.path.isdir(os.path.join(caminho, item))]
                    arquivos_list = [f"📄 `{item}`" for item in itens if os.path.isfile(os.path.join(caminho, item))]
                    resposta = f"📂 *Conteúdo de:* `{caminho}`\n\n"
                    if pastas_list: resposta += "*Pastas:*\n" + "\n".join(pastas_list) + "\n\n"
                    if arquivos_list: resposta += "*Arquivos:*\n" + "\n".join(arquivos_list) + "\n\n⬇️ _Para baixar:_ `/enviar caminho_completo`"
                    if len(resposta) > 4000: resposta = resposta[:4000] + "\n...[Cortado]"
                    await send_text_message(remote_jid, resposta)
                except Exception as e:
                    await send_text_message(remote_jid, f"⚠️ Erro: {e}")

        elif comando_base == '/enviar':
            if argumento:
                if os.path.exists(argumento) and os.path.isfile(argumento):
                    await send_text_message(remote_jid, f"⏳ Enviando: `{argumento}`...")
                    await send_media_message(remote_jid, argumento, "document")
                else:
                    await send_text_message(remote_jid, "❌ Arquivo não encontrado.")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /enviar <caminho>")

        elif comando_base == '/mirror':
            pasta_base = os.path.join(os.path.expanduser("~"), "Documents", "ScreenMirror")
            if SISTEMA == "Windows":
                exe = os.path.join(pasta_base, "screen_mirror.exe")
            else:
                exe = os.path.join(pasta_base, "screen_mirror")

            if os.path.exists(exe):
                await send_text_message(remote_jid, "📺 Iniciando espelhamento...")
                if SISTEMA == "Darwin":
                    os.system(f'chmod +x "{exe}"')
                subprocess.Popen(exe)
            else:
                await send_text_message(remote_jid, f"❌ Executável não encontrado em:\n`{pasta_base}`")

        elif comando_base == '/executar':
            if argumento:
                if SISTEMA == "Windows":
                    await send_text_message(remote_jid, f"🚀 Win+R: `{argumento}`")
                    pyautogui.hotkey('win', 'r')
                    time.sleep(0.5)
                    pyautogui.write(argumento)
                    pyautogui.press('enter')
                elif SISTEMA == "Darwin":
                    await send_text_message(remote_jid, f"🚀 Spotlight: `{argumento}`")
                    pyautogui.hotkey('command', 'space')
                    time.sleep(0.5)
                    pyautogui.write(argumento)
                    pyautogui.press('enter')
            else:
                await send_text_message(remote_jid, "⚠️ Use: /executar <comando>")

        return True

    except Exception as e:
        await send_text_message(remote_jid, f"⚠️ Erro no WhatsBot ({comando_base}): {str(e)}")
        return True
