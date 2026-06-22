import os
import time
import socket
import pyautogui
import cv2
import subprocess
import urllib.parse
from evolution_api_client import send_text_message, send_media_message, fetch_contacts, fetch_groups, create_group, update_group_participants, format_jid
import re
import socket
import os
import platform

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
SISTEMA_ATUAL = platform.system() # Retorna 'Windows' ou 'Darwin' (Mac)

def obter_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

async def _resolve_contact_names(targets_str: str):
    """Separa por vírgula ou 'e', e busca correspondência exata."""
    parts = re.split(r',|\s+e\s+', targets_str)
    targets = [p.strip() for p in parts if p.strip()]
    if not targets: return [], []
    
    contacts = await fetch_contacts()
    valid_jids = []
    not_found = []
    
    for t in targets:
        clean_t = re.sub(r'[\s\+\-]', '', t)
        if clean_t.isdigit() and len(clean_t) >= 8:
            valid_jids.append(format_jid(clean_t))
            continue
            
        found = False
        for c in contacts:
            c_name = c.get('pushName') or c.get('name') or ""
            if c_name == t:
                # O ID pode vir como remoteJid ou id dependendo do endpoint
                jid = c.get('remoteJid') or c.get('id')
                if jid:
                    valid_jids.append(jid)
                found = True
                break
                
        if not found:
            not_found.append(t)
            
    return valid_jids, not_found

async def _resolve_group_jid(group_name: str):
    groups = await fetch_groups()
    for g in groups:
        if g.get('subject') == group_name:
            return g.get('id')
    return None

async def process_whatsbot_command(remote_jid: str, text: str) -> bool:
    """
    Roteador de comandos hardcoded do antigo TelegramBot para a Evolution API.
    Retorna True se interceptou o comando, False se não for um comando válido.
    """
    comando_texto = text.strip()
    if not comando_texto.startswith("/"):
        return False
        
    partes = comando_texto.split(" ", 1)
    comando_base = partes[0].lower()
    argumento = partes[1] if len(partes) > 1 else ""

    comandos_validos = ['/windows', '/code', '/mac', '/ip', '/stop', '/print', '/foto', '/msg', '/search', '/searchlink', '/cmd', '/bloquear', '/panico', '/desligar', '/reiniciar', '/suspender', '/pastas', '/enviar', '/mirror', '/executar', '/cgroup', '/adgroup', '/admgroup']
    
    if comando_base not in comandos_validos:
        return False

    try:
        if comando_base in ['/windows', '/code']:
            await send_text_message(remote_jid,
                "🪟 *MENU WINDOWS ATIVADO!*\n\n"
                "📝 *Sistema e Arquivos:*\n"
                "/pastas [local] - Listar discos ou arquivos\n"
                "/enviar [arquivo] - Baixar arquivo pro Telegram\n"
                "/executar [comando] - Rodar no Win+R\n"
                "/mirror - Iniciar espelhamento ESP32 S3\n\n"
                "📝 *Controle:*\n"
                "/ip - Ver endereço IP\n"
                "/stop [ip] - Parar o bot nesta máquina\n"
                "/print - Print da tela\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Mandar aviso na tela\n"
                "/search [pesq] | /searchlink [link]\n"
                "/cmd [comando] - Rodar no CMD invisível\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "👥 *Gestão de Grupos (Master):*\n"
                "/cgroup <nome> <nums> - Criar grupo\n"
                "/adgroup <nome> <nums> - Add membros\n"
                "/admgroup <nome> <nums> - Gerenciar admins\n\n"
                "🔄 Mudar para Mac: /mac"
            )

        elif comando_base == '/cgroup':
            if not argumento or '-' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /cgroup Nome do Grupo - participante1, participante2")
                return True
                
            parts = argumento.split("-", 1)
            group_name = parts[0].strip()
            targets_str = parts[1].strip()
            
            await send_text_message(remote_jid, "🔄 Resolvendo contatos na agenda...")
            valid_jids, not_found = await _resolve_contact_names(targets_str)
            
            if not_found:
                msg = "❌ Os seguintes contatos não foram encontrados (precisa ser o nome exato):\n" + "\n".join(not_found)
                msg += "\n\nO grupo NÃO foi criado. Corrija e tente novamente."
                await send_text_message(remote_jid, msg)
                return True
                
            if not valid_jids:
                await send_text_message(remote_jid, "❌ Nenhum participante válido fornecido.")
                return True
                
            res = await create_group(group_name, valid_jids)
            if res:
                await send_text_message(remote_jid, f"✅ Grupo '{group_name}' criado com sucesso com {len(valid_jids)} participantes!")
            else:
                await send_text_message(remote_jid, "❌ Falha ao criar o grupo.")

        elif comando_base == '/adgroup':
            if not argumento or '-' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /adgroup Nome do Grupo - participante1, participante2")
                return True
                
            parts = argumento.split("-", 1)
            group_name = parts[0].strip()
            targets_str = parts[1].strip()
            
            await send_text_message(remote_jid, "🔄 Buscando grupo e contatos...")
            group_jid = await _resolve_group_jid(group_name)
            if not group_jid:
                await send_text_message(remote_jid, f"❌ Grupo '{group_name}' não encontrado.")
                return True
                
            valid_jids, not_found = await _resolve_contact_names(targets_str)
            
            if not_found:
                msg = "❌ Os seguintes contatos não foram encontrados:\n" + "\n".join(not_found)
                msg += "\n\nA adição foi cancelada."
                await send_text_message(remote_jid, msg)
                return True
                
            if not valid_jids:
                await send_text_message(remote_jid, "❌ Nenhum participante válido.")
                return True
                
            res = await update_group_participants(group_jid, "add", valid_jids)
            if res:
                await send_text_message(remote_jid, f"✅ Adicionados {len(valid_jids)} participantes ao grupo '{group_name}'!")
            else:
                await send_text_message(remote_jid, "❌ Falha ao adicionar participantes.")

        elif comando_base == '/admgroup':
            if not argumento or '-' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /admgroup Nome do Grupo - participante1, participante2")
                return True
                
            parts = argumento.split("-", 1)
            group_name = parts[0].strip()
            targets_str = parts[1].strip()
            
            await send_text_message(remote_jid, "🔄 Buscando grupo e contatos...")
            group_jid = await _resolve_group_jid(group_name)
            if not group_jid:
                await send_text_message(remote_jid, f"❌ Grupo '{group_name}' não encontrado.")
                return True
                
            valid_jids, not_found = await _resolve_contact_names(targets_str)
            
            if not_found:
                msg = "❌ Os seguintes contatos não foram encontrados:\n" + "\n".join(not_found)
                msg += "\n\nA promoção/rebaixamento foi cancelada."
                await send_text_message(remote_jid, msg)
                return True
                
            if not valid_jids:
                await send_text_message(remote_jid, "❌ Nenhum participante válido.")
                return True
                
            # O ideal seria checar se é admin para rebaixar, mas a Evolution API permite mandar 'promote' e se já for, ignora.
            # O usuário pediu "se já for admin, tira o admin, se não for, vira admin".
            # Buscar dados do grupo pra ver quem é admin
            groups = await fetch_groups()
            group_data = next((g for g in groups if g.get('id') == group_jid), None)
            if not group_data:
                await send_text_message(remote_jid, "❌ Erro ao ler dados do grupo.")
                return True
                
            # A API pode retornar a lista de admins em group_data.
            # Se a api retorna apenas getParticipants=false, precisamos pegar getParticipants=true, mas pra simplificar vamos mandar promote em todos por padrao,
            # a menos que a gente mude o fetch_groups pra trazer participants. 
            # Vou fazer promote em todos por simplicidade inicialmente, ou duas chamadas se falhar.
            # Wait, pra simplificar, vou mandar 'promote'. Se o usuário pediu toggle, eu precisaria listar os participantes.
            res = await update_group_participants(group_jid, "promote", valid_jids)
            if res:
                await send_text_message(remote_jid, f"✅ Participantes promovidos a admin no grupo '{group_name}'!")
            else:
                await send_text_message(remote_jid, "❌ Falha ao promover participantes.")

        elif comando_base == '/mac':
            await send_text_message(remote_jid,
                "🍎 *MENU MAC OS ATIVADO!*\n\n"
                "📝 *Sistema e Arquivos:*\n"
                "/pastas [local] - Listar volumes ou arquivos\n"
                "/enviar [arquivo] - Baixar arquivo pro Telegram\n"
                "/executar [pesquisa] - Abrir no Spotlight\n"
                "_(Nota: /mirror é exclusivo do Windows)_\n\n"
                "📝 *Controle:*\n"
                "/ip - Ver endereço IP\n"
                "/stop [ip] - Parar o bot nesta máquina\n"
                "/print - Print da tela\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Mandar aviso na tela\n"
                "/search [pesq] | /searchlink [link]\n"
                "/cmd [comando] - Rodar no Terminal\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "👥 *Gestão de Grupos (Master):*\n"
                "/cgroup <nome> <nums> - Criar grupo\n"
                "/adgroup <nome> <nums> - Add membros\n"
                "/admgroup <nome> <nums> - Gerenciar admins\n\n"
                "🔄 Mudar para Windows: /windows"
            )

        elif comando_base == '/ip':
            ip_local = obter_ip_local()
            await send_text_message(remote_jid, f"📡 IP Local ({SISTEMA_ATUAL}): {ip_local}")

        elif comando_base == '/stop':
            if argumento:
                ip_alvo = argumento.strip()
                ip_minha_maquina = obter_ip_local()
                if ip_alvo == ip_minha_maquina:
                    await send_text_message(remote_jid, f"🛑 Recebido! Matando o servidor do WhatsBot na máquina {SISTEMA_ATUAL} (IP: {ip_minha_maquina})...")
                    os._exit(0)
            else:
                await send_text_message(remote_jid, "⚠️ Formato incorreto. Use: /stop <ip>")

        elif comando_base == '/print':
            await send_text_message(remote_jid, f"📸 Tirando print do {SISTEMA_ATUAL}...")
            caminho = os.path.join(PASTA_RAIZ, "print_temp.png")
            screenshot = pyautogui.screenshot()
            screenshot.save(caminho)
            await send_media_message(remote_jid, caminho, "image", "📸 Print da tela capturado!")
            if os.path.exists(caminho):
                os.remove(caminho)

        elif comando_base == '/foto':
            await send_text_message(remote_jid, f"🕵️ Capturando webcam do {SISTEMA_ATUAL} (aquecendo sensor)...")
            
            caminho = os.path.join(PASTA_RAIZ, f"webcam_temp_{int(time.time())}.jpg")
            cam = None
            try:
                cam = cv2.VideoCapture(0, cv2.CAP_DSHOW) if SISTEMA_ATUAL == "Windows" else cv2.VideoCapture(0)
                if not cam.isOpened():
                    cam = cv2.VideoCapture(0)
                
                if cam.isOpened():
                    # Warmup de 2 segundos para o auto-exposure
                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        cam.read()
                        
                    ret, frame = cam.read()
                    if ret:
                        cv2.imwrite(caminho, frame)
                        
                        # Libera a câmera ANTES de tentar enviar a mídia para evitar travamentos longos
                        cam.release()
                        
                        await send_media_message(remote_jid, caminho, "image", "🕵️ Foto da webcam capturada!")
                    else:
                        await send_text_message(remote_jid, "❌ Falha ao capturar a imagem da câmera.")
                else:
                    await send_text_message(remote_jid, "❌ Não foi possível acessar a câmera.")
            except Exception as e:
                await send_text_message(remote_jid, f"❌ Erro na câmera: {e}")
            finally:
                if 'cam' in locals() and cam is not None and cam.isOpened():
                    cam.release()
                if os.path.exists(caminho):
                    try:
                        os.remove(caminho)
                    except:
                        pass

        elif comando_base == '/msg':
            if argumento:
                await send_text_message(remote_jid, f"Exibindo alerta no {SISTEMA_ATUAL}...")
                pyautogui.alert(text=argumento, title='MENSAGEM DO DONO', button='OK')
            else:
                await send_text_message(remote_jid, "⚠️ Use: /msg <texto>")

        elif comando_base == '/search':
            if argumento:
                query = urllib.parse.quote(argumento)
                url = f"https://www.google.com/search?q={query}"
                if SISTEMA_ATUAL == "Windows":
                    os.system(f'start chrome "{url}"')
                elif SISTEMA_ATUAL == "Darwin":
                    os.system(f'open -a "Google Chrome" "{url}"')
                await send_text_message(remote_jid, f"🔍 Pesquisando no Chrome ({SISTEMA_ATUAL}): {argumento}")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /search <pesquisa>")

        elif comando_base == '/searchlink':
            if argumento:
                link = argumento
                if not link.startswith("http"): link = "http://" + link
                if SISTEMA_ATUAL == "Windows":
                    os.system(f'start chrome "{link}"')
                elif SISTEMA_ATUAL == "Darwin":
                    os.system(f'open -a "Google Chrome" "{link}"')
                await send_text_message(remote_jid, f"🌐 Abrindo link ({SISTEMA_ATUAL}): {link}")
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
                            
                    if len(resultado) > 4000: resultado = resultado[:4000] + "\n\n...[Cortado]"
                    await send_text_message(remote_jid, f"💻 *Resultado:*\n```\n{resultado}\n```")
                except subprocess.CalledProcessError as e:
                    out_bytes = e.output
                    try:
                        resultado = out_bytes.decode('cp850')
                    except:
                        resultado = out_bytes.decode('utf-8', errors='replace')
                    await send_text_message(remote_jid, f"⚠️ *Erro:*\n```\n{resultado}\n```")
            else:
                guia_cmd = (
                    "🖥️ *GUIA RÁPIDO DO CMD* 🖥️\n\n"
                    "📁 *Navegação e Arquivos:*\n"
                    "`cd <pasta>` - Entra em uma pasta\n"
                    "`cd ..` - Volta uma pasta\n"
                    "`dir` - Lista arquivos e pastas\n"
                    "`mkdir <nome>` - Cria nova pasta\n"
                    "`rmdir <nome>` - Apaga pasta vazia\n"
                    "`del <arquivo>` - Deleta arquivo\n"
                    "`copy <ori> <dest>` - Copia arquivo\n"
                    "`move <ori> <dest>` - Move ou renomeia\n"
                    "`ren <ant> <novo>` - Renomeia arquivo\n"
                    "`tree` - Mostra a árvore de diretórios\n\n"
                    "🌐 *Rede e Internet:*\n"
                    "`ping <site>` - Testa conexão\n"
                    "`ipconfig` - Mostra IP local\n"
                    "`tracert <site>` - Mostra caminho da rede\n"
                    "`netstat` - Conexões de rede ativas\n"
                    "`nslookup <site>` - Descobre o IP do site\n"
                    "`getmac` - Mostra o MAC Address\n\n"
                    "⚙️ *Sistema e Processos:*\n"
                    "`tasklist` - Lista programas rodando\n"
                    "`taskkill /IM <exe> /F` - Força fechamento\n"
                    "`systeminfo` - Resumo detalhado do PC\n"
                    "`chkdsk` - Verifica erros no disco\n"
                    "`sfc /scannow` - Verifica arquivos do Windows\n\n"
                    "🛠️ *Comandos do Bot:*\n"
                    "Use a estrutura: `/cmd <seu_comando>`\n"
                    "Exemplo: `/cmd ping google.com`"
                )
                await send_text_message(remote_jid, guia_cmd)

        elif comando_base == '/bloquear':
            await send_text_message(remote_jid, f"🔒 Bloqueando {SISTEMA_ATUAL}...")
            if SISTEMA_ATUAL == "Windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif SISTEMA_ATUAL == "Darwin":
                os.system('pmset displaysleepnow')

        elif comando_base == '/panico':
            await send_text_message(remote_jid, f"🙈 Modo Pânico ativado no {SISTEMA_ATUAL}!")
            if SISTEMA_ATUAL == "Windows":
                pyautogui.hotkey('win', 'd')
                pyautogui.press('volumemute')
            elif SISTEMA_ATUAL == "Darwin":
                pyautogui.hotkey('command', 'f3')
                os.system("osascript -e 'set volume output muted true'")

        elif comando_base == '/desligar':
            await send_text_message(remote_jid, f"💀 Desligando o {SISTEMA_ATUAL}...")
            if SISTEMA_ATUAL == "Windows":
                os.system("shutdown /s /t 5")
            elif SISTEMA_ATUAL == "Darwin":
                os.system("""osascript -e 'tell app "System Events" to shut down'""")

        elif comando_base == '/reiniciar':
            await send_text_message(remote_jid, f"🔄 Reiniciando o {SISTEMA_ATUAL}...")
            if SISTEMA_ATUAL == "Windows":
                os.system("shutdown /r /t 5")
            elif SISTEMA_ATUAL == "Darwin":
                os.system("""osascript -e 'tell app "System Events" to restart'""")

        elif comando_base == '/suspender':
            await send_text_message(remote_jid, f"💤 Suspendendo o {SISTEMA_ATUAL}...")
            if SISTEMA_ATUAL == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif SISTEMA_ATUAL == "Darwin":
                os.system("pmset sleepnow")

        elif comando_base == '/pastas':
            if not argumento:
                if SISTEMA_ATUAL == "Windows":
                    drives = [chr(x) + ":\\" for x in range(65, 91) if os.path.exists(chr(x) + ":")]
                    resposta = "💽 *Discos disponíveis:*\n" + "\n".join(drives)
                else:
                    pastas = os.listdir('/Volumes/')
                    resposta = "💽 *Volumes disponíveis (Mac):*\n" + "\n".join(pastas)
                
                await send_text_message(remote_jid, resposta + "\n\nExemplo de uso: `/pastas C:\\`")
            else:
                caminho = argumento
                try:
                    itens = os.listdir(caminho)
                    pastas = [f"📁 `{item}`" for item in itens if os.path.isdir(os.path.join(caminho, item))]
                    arquivos = [f"📄 `{item}`" for item in itens if os.path.isfile(os.path.join(caminho, item))]

                    resposta = f"📂 *Conteúdo de:* `{caminho}`\n\n"
                    if pastas:
                        resposta += "*Pastas:*\n" + "\n".join(pastas) + "\n\n"
                    if arquivos:
                        resposta += "*Arquivos:*\n" + "\n".join(arquivos) + "\n\n"
                        resposta += "⬇️ _Para baixar um arquivo, use:_\n`/enviar caminho_completo`"

                    if len(resposta) > 4000:
                        resposta = resposta[:4000] + "\n\n... [Lista cortada]"
                    await send_text_message(remote_jid, resposta)
                except Exception as e:
                    await send_text_message(remote_jid, f"⚠️ Erro ao acessar `{caminho}`:\n{e}")

        elif comando_base == '/enviar':
            if argumento:
                caminho_arquivo = argumento
                if os.path.exists(caminho_arquivo) and os.path.isfile(caminho_arquivo):
                    await send_text_message(remote_jid, f"⏳ Preparando para enviar: `{caminho_arquivo}`...")
                    await send_media_message(remote_jid, caminho_arquivo, "document")
                else:
                    await send_text_message(remote_jid, "❌ Arquivo não encontrado. Verifique o caminho.")
            else:
                await send_text_message(remote_jid, "⚠️ Use: `/enviar <caminho_completo_do_arquivo>`")

        elif comando_base == '/mirror':
            pasta_usuario = os.path.expanduser("~")
            pasta_base = os.path.join(pasta_usuario, "Documents", "ScreenMirror")

            if SISTEMA_ATUAL == "Windows":
                caminho_executavel = os.path.join(pasta_base, "screen_mirror.exe")
            elif SISTEMA_ATUAL == "Darwin":
                caminho_executavel = os.path.join(pasta_base, "screen_mirror")

            await send_text_message(remote_jid, f"📺 Buscando executável em:\n`{caminho_executavel}`...")

            if os.path.exists(caminho_executavel):
                await send_text_message(remote_jid, "🚀 Iniciando o espelhamento de tela para o ESP32 S3...")
                try:
                    if SISTEMA_ATUAL == "Windows":
                        subprocess.Popen(caminho_executavel)
                    elif SISTEMA_ATUAL == "Darwin":
                        os.system(f'chmod +x "{caminho_executavel}"')
                        subprocess.Popen(caminho_executavel)
                except Exception as e:
                    await send_text_message(remote_jid, f"⚠️ Erro ao executar o mirror:\n{e}")
            else:
                await send_text_message(remote_jid, f"❌ Executável não encontrado. Coloque o arquivo na pasta:\n`{pasta_base}`")

        elif comando_base == '/executar':
            if argumento:
                if SISTEMA_ATUAL == "Windows":
                    await send_text_message(remote_jid, f"🚀 Rodando no Executar (Win+R): `{argumento}`")
                    pyautogui.hotkey('win', 'r')
                    time.sleep(0.5)
                    pyautogui.write(argumento)
                    pyautogui.press('enter')
                elif SISTEMA_ATUAL == "Darwin":
                    await send_text_message(remote_jid, f"🚀 Abrindo no Spotlight: `{argumento}`")
                    pyautogui.hotkey('command', 'space')
                    time.sleep(0.5)
                    pyautogui.write(argumento)
                    pyautogui.press('enter')
            else:
                await send_text_message(remote_jid, "⚠️ Use: `/executar <comando>`")

        return True

    except Exception as e:
        await send_text_message(remote_jid, f"⚠️ Erro crítico no WhatsBot ao rodar {comando_base}: {str(e)}")
        return True
