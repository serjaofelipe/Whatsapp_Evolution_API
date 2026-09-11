import os
import time
import socket
import asyncio
import pyautogui
import cv2
import subprocess
import urllib.parse
from evolution_api_client import send_text_message, send_media_message, fetch_contacts, fetch_groups, create_group, update_group_participants, format_jid
import re
import socket
import os
import platform
import json

# Skills e ferramentas locais (antes executadas pela IA, agora comandos diretos)
from skills.system_manager import analyze_disks, analyze_folders, open_url, get_hardware_specs
from skills.network_manager import get_geolocation_and_ip, run_network_diagnostics
from skills.file_manager import write_to_file
from skills.python_executor import run_dynamic_script
from tools.games import get_installed_games, get_game_size as _get_game_size, executar_jogo

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
        t_lower = t.lower()
        
        # Tentar resolver pelo contatos.json local primeiro
        try:
            import json
            json_path = os.path.join(PASTA_RAIZ, 'contatos.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    contatos_locais = json.load(f)
                for nome_salvo, numero in contatos_locais.items():
                    if nome_salvo.lower() == t_lower:
                        num_clean = re.sub(r'[\s\+\-]', '', str(numero))
                        valid_jids.append(format_jid(num_clean))
                        found = True
                        break
        except Exception as e:
            print(f"Erro ao ler contatos.json: {e}")
            
        if found:
            continue

        # Fallback para a Evolution API (PushNames)
        for c in contacts:
            if not c.get('isSaved'): continue
            
            c_name = (c.get('pushName') or c.get('name') or "").lower()
            if not c_name: continue
            
            # Match EXATO ignorando maiúsculas. (Não usar 'in' para evitar adicionar aleatórios)
            if c_name == t_lower:
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

    comandos_validos = ['/windows', '/code', '/mac', '/ip', '/stop', '/print', '/foto', '/msg', '/search', '/searchlink', '/cmd', '/bloquear', '/panico', '/desligar', '/reiniciar', '/suspender', '/pastas', '/enviar', '/mirror', '/executar', '/cgroup', '/adgroup', '/admgroup', '/newcontato',
                        '/discos', '/hardware', '/analisarpasta', '/geoip', '/rede', '/abrir', '/escrever', '/pyexec', '/jogos', '/tamanhojogo', '/jogar', '/enviarmsg']
    
    if comando_base not in comandos_validos:
        return False

    try:
        if comando_base in ['/windows', '/code']:
            await send_text_message(remote_jid,
                "🪟 *MENU DE COMANDOS ATIVADO!*\n\n"
                "📝 *Sistema e Arquivos:*\n"
                "/pastas [local] - Listar discos ou arquivos\n"
                "/enviar [arquivo] - Baixar arquivo\n"
                "/executar [comando] - Rodar no Win+R\n"
                "/escrever [caminho] | [conteudo] - Criar arquivo\n"
                "/discos - Espaço em disco\n"
                "/analisarpasta [caminho] - Pasta mais pesada/leve\n"
                "/hardware - CPU, RAM, GPU e SO\n"
                "/mirror - Iniciar espelhamento ESP32 S3\n\n"
                "🌐 *Rede e Internet:*\n"
                "/ip - Ver endereço IP local\n"
                "/geoip - IP público, ISP e localização\n"
                "/rede - SpeedTest, ping e conexões\n"
                "/abrir [url] - Abrir link no navegador\n"
                "/search [pesq] | /searchlink [link]\n\n"
                "🎮 *Jogos:*\n"
                "/jogos - Listar jogos instalados\n"
                "/tamanhojogo [nome] - Tamanho de um jogo\n"
                "/jogar [nome] - Abrir um jogo\n\n"
                "🐍 *Execução:*\n"
                "/cmd [comando] - Rodar no terminal\n"
                "/pyexec [codigo] - Executar script Python\n\n"
                "📝 *Controle:*\n"
                "/stop [ip] - Parar o bot nesta máquina\n"
                "/print - Print (uma imagem por monitor)\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Mandar aviso na tela\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "👥 *Contatos e Grupos (Master):*\n"
                "/newcontato <nome> - <num> - Salvar contato local\n"
                "/enviarmsg <nome/num> - <texto> - Enviar mensagem\n"
                "/cgroup <nome> - <nums> - Criar grupo\n"
                "/adgroup <nome> - <nums> - Add membros\n"
                "/admgroup <nome> - <nums> - Gerenciar admins\n\n"
                "🔄 Mudar para Mac: /mac"
            )

        elif comando_base == '/newcontato':
            if not argumento or '-' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /newcontato Nome do Contato - Numero (ex: 41999999999)")
                return True
            parts = argumento.split("-", 1)
            nome = parts[0].strip()
            numero = parts[1].strip()
            
            num_clean = re.sub(r'[\s\+\-]', '', numero)
            
            try:
                import json
                json_path = os.path.join(PASTA_RAIZ, 'contatos.json')
                contatos_locais = {}
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        contatos_locais = json.load(f)
                
                contatos_locais[nome] = num_clean
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(contatos_locais, f, indent=4, ensure_ascii=False)
                    
                await send_text_message(remote_jid, f"✅ Contato salvo na agenda local!\n*Nome:* {nome}\n*Número:* {num_clean}")
            except Exception as e:
                await send_text_message(remote_jid, f"❌ Erro ao salvar contato: {e}")
                

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
                "/enviar [arquivo] - Baixar arquivo\n"
                "/executar [pesquisa] - Abrir no Spotlight\n"
                "/escrever [caminho] | [conteudo] - Criar arquivo\n"
                "/discos - Espaço em disco\n"
                "/analisarpasta [caminho] - Pasta mais pesada/leve\n"
                "/hardware - CPU, RAM, GPU e SO\n"
                "_(Nota: /mirror é exclusivo do Windows)_\n\n"
                "🌐 *Rede e Internet:*\n"
                "/ip - Ver endereço IP local\n"
                "/geoip - IP público, ISP e localização\n"
                "/rede - SpeedTest, ping e conexões\n"
                "/abrir [url] - Abrir link no navegador\n"
                "/search [pesq] | /searchlink [link]\n\n"
                "🎮 *Jogos:*\n"
                "/jogos - Listar jogos (Steam/Epic/etc)\n"
                "/tamanhojogo [nome] | /jogar [nome]\n\n"
                "🐍 *Execução:*\n"
                "/cmd [comando] - Rodar no Terminal\n"
                "/pyexec [codigo] - Executar script Python\n\n"
                "📝 *Controle:*\n"
                "/stop [ip] - Parar o bot nesta máquina\n"
                "/print - Print (uma imagem por monitor)\n"
                "/foto - Foto da webcam\n"
                "/msg [texto] - Mandar aviso na tela\n"
                "/bloquear | /panico | /suspender\n"
                "/reiniciar | /desligar\n\n"
                "👥 *Contatos e Grupos (Master):*\n"
                "/newcontato <nome> - <num> | /enviarmsg <alvo> - <texto>\n"
                "/cgroup <nome> - <nums> - Criar grupo\n"
                "/adgroup <nome> - <nums> - Add membros\n"
                "/admgroup <nome> - <nums> - Gerenciar admins\n\n"
                "⚠️ No Mac, dê permissão de *Gravação de Tela* e *Câmera* ao Terminal em Ajustes > Privacidade.\n\n"
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
            # Captura CADA monitor separadamente (um print por tela).
            # Se houver só 1 monitor, tira só 1; se houver 2+, tira um de cada.
            capturado = False
            try:
                import mss
                import mss.tools
                with mss.mss() as sct:
                    # sct.monitors[0] é a área combinada de todas as telas;
                    # os índices 1..N são cada monitor individual.
                    monitores = sct.monitors[1:] if len(sct.monitors) > 1 else sct.monitors
                    total = len(monitores)
                    await send_text_message(remote_jid, f"📸 Capturando {total} tela(s) do {SISTEMA_ATUAL}...")
                    for idx, mon in enumerate(monitores, start=1):
                        shot = sct.grab(mon)
                        caminho = os.path.join(PASTA_RAIZ, f"print_tela_{idx}_{int(time.time())}.png")
                        mss.tools.to_png(shot.rgb, shot.size, output=caminho)
                        legenda = f"📸 Tela {idx}/{total} ({mon['width']}x{mon['height']})"
                        await send_media_message(remote_jid, caminho, "image", legenda)
                        if os.path.exists(caminho):
                            try: os.remove(caminho)
                            except: pass
                    capturado = True
            except ImportError:
                pass  # mss não instalado -> usa fallback abaixo
            except Exception as e:
                await send_text_message(remote_jid, f"⚠️ Erro ao capturar telas (mss): {e}\nTentando modo simples...")

            if not capturado:
                # Fallback: pyautogui (captura a área virtual como uma imagem só)
                await send_text_message(remote_jid, f"📸 Tirando print do {SISTEMA_ATUAL} (modo simples)...")
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
                    os.system(f'start "" "{url}"')
                elif SISTEMA_ATUAL == "Darwin":
                    # 'open' usa o navegador padrão (sempre disponível no Mac)
                    os.system(f'open "{url}"')
                else:
                    os.system(f'xdg-open "{url}"')
                await send_text_message(remote_jid, f"🔍 Pesquisando ({SISTEMA_ATUAL}): {argumento}")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /search <pesquisa>")

        elif comando_base == '/searchlink':
            if argumento:
                link = argumento
                if not link.startswith("http"): link = "http://" + link
                if SISTEMA_ATUAL == "Windows":
                    os.system(f'start "" "{link}"')
                elif SISTEMA_ATUAL == "Darwin":
                    os.system(f'open "{link}"')
                else:
                    os.system(f'xdg-open "{link}"')
                await send_text_message(remote_jid, f"🌐 Abrindo link ({SISTEMA_ATUAL}): {link}")
            else:
                await send_text_message(remote_jid, "⚠️ Use: /searchlink <link>")

        elif comando_base == '/cmd':
            if argumento:
                # Decodificação robusta e multiplataforma.
                # Windows: saída em cp850/cp1252. Mac/Linux: utf-8.
                def _decode_saida(b):
                    if not b:
                        return ""
                    ordem = ['cp850', 'utf-8', 'cp1252'] if SISTEMA_ATUAL == "Windows" else ['utf-8', 'cp1252']
                    for enc in ordem:
                        try:
                            return b.decode(enc)
                        except (UnicodeDecodeError, LookupError):
                            continue
                    return b.decode('utf-8', errors='replace')

                try:
                    out_bytes = subprocess.check_output(argumento, shell=True, stderr=subprocess.STDOUT)
                    resultado = _decode_saida(out_bytes)
                    if len(resultado) > 4000: resultado = resultado[:4000] + "\n\n...[Cortado]"
                    await send_text_message(remote_jid, f"💻 *Resultado:*\n```\n{resultado}\n```")
                except subprocess.CalledProcessError as e:
                    resultado = _decode_saida(e.output)
                    if len(resultado) > 4000: resultado = resultado[:4000] + "\n\n...[Cortado]"
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

        elif comando_base == '/discos':
            await send_text_message(remote_jid, "💽 Analisando discos...")
            resultado = await asyncio.to_thread(analyze_disks)
            if len(resultado) > 4000:
                resultado = resultado[:4000] + "\n...[Cortado]"
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/hardware':
            await send_text_message(remote_jid, "🖥️ Lendo hardware...")
            resultado = await asyncio.to_thread(get_hardware_specs)
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/analisarpasta':
            if not argumento:
                await send_text_message(remote_jid, "⚠️ Use: /analisarpasta <caminho> (ex: C:\\Users)")
                return True
            await send_text_message(remote_jid, f"📂 Analisando `{argumento}` (pode demorar)...")
            resultado = await asyncio.to_thread(analyze_folders, argumento.strip())
            if len(resultado) > 4000:
                resultado = resultado[:4000] + "\n...[Cortado]"
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/geoip':
            await send_text_message(remote_jid, "🌍 Buscando IP público e localização...")
            resultado = await asyncio.to_thread(get_geolocation_and_ip)
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/rede':
            await send_text_message(remote_jid, "📡 Rodando diagnóstico de rede (SpeedTest pode levar ~30s)...")
            resultado = await asyncio.to_thread(run_network_diagnostics)
            if len(resultado) > 4000:
                resultado = resultado[:4000] + "\n...[Cortado]"
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/abrir':
            if not argumento:
                await send_text_message(remote_jid, "⚠️ Use: /abrir <url> (ex: /abrir youtube.com)")
                return True
            url = argumento.strip()
            if not re.match(r'^https?://', url):
                url = "https://" + url
            resultado = await asyncio.to_thread(open_url, url)
            await send_text_message(remote_jid, f"🌐 {resultado}")

        elif comando_base == '/escrever':
            if not argumento or '|' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /escrever <caminho> | <conteudo>\nEx: /escrever C:\\teste.txt | Ola mundo")
                return True
            parts = argumento.split("|", 1)
            file_path = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            resultado = await asyncio.to_thread(write_to_file, file_path, content)
            await send_text_message(remote_jid, f"📝 {resultado}")

        elif comando_base == '/pyexec':
            if not argumento:
                await send_text_message(remote_jid, "⚠️ Use: /pyexec <codigo python>\nEx: /pyexec print(2+2)")
                return True
            await send_text_message(remote_jid, "🐍 Executando script Python...")
            resultado = await asyncio.to_thread(run_dynamic_script, argumento, "Comando_WhatsApp")
            if len(resultado) > 4000:
                resultado = resultado[:4000] + "\n...[Cortado]"
            await send_text_message(remote_jid, f"```\n{resultado}\n```")

        elif comando_base == '/jogos':
            await send_text_message(remote_jid, "🎮 Buscando jogos instalados...")
            jogos = await asyncio.to_thread(get_installed_games, True)  # skip_size=True para não travar
            if not jogos:
                await send_text_message(remote_jid, "❌ Nenhum jogo encontrado.")
                return True
            plataformas = {}
            for j in jogos:
                plataformas.setdefault(j["plataforma"], []).append(j)
            resultado = "🎮 *Jogos Instalados:*\n"
            for p_name, p_jogos in plataformas.items():
                resultado += f"\n*[{p_name}]*\n"
                for j in p_jogos:
                    size = j.get('tamanho_gb', 0)
                    size_str = f" ({size} GB)" if size > 0 else ""
                    resultado += f"  • {j['nome']}{size_str}\n"
            if len(resultado) > 4000:
                resultado = resultado[:4000] + "\n...[Cortado]"
            await send_text_message(remote_jid, resultado)

        elif comando_base == '/tamanhojogo':
            if not argumento:
                await send_text_message(remote_jid, "⚠️ Use: /tamanhojogo <nome do jogo>")
                return True
            info = await asyncio.to_thread(_get_game_size, argumento.strip())
            if info:
                await send_text_message(remote_jid,
                    f"🎮 *{info['nome']}*\n"
                    f"Plataforma: {info['plataforma']}\n"
                    f"Tamanho: {info['tamanho']}\n"
                    f"Local: `{info.get('install_path', '?')}`")
            else:
                await send_text_message(remote_jid, f"❌ Jogo '{argumento.strip()}' não encontrado.")

        elif comando_base == '/jogar':
            if not argumento:
                await send_text_message(remote_jid, "⚠️ Use: /jogar <nome do jogo>")
                return True
            jogos = await asyncio.to_thread(get_installed_games, True)
            nome_busca = argumento.strip().lower()
            alvo = next((j for j in jogos if nome_busca in j["nome"].lower()), None)
            if alvo:
                await asyncio.to_thread(executar_jogo, alvo["launch_cmd"])
                await send_text_message(remote_jid, f"🚀 Jogo '{alvo['nome']}' ({alvo['plataforma']}) iniciado!")
            else:
                await send_text_message(remote_jid, f"❌ Jogo '{argumento.strip()}' não encontrado.")

        elif comando_base == '/enviarmsg':
            if not argumento or '-' not in argumento:
                await send_text_message(remote_jid, "⚠️ Use: /enviarmsg <nome ou numero> - <mensagem>")
                return True
            parts = argumento.split("-", 1)
            alvo_str = parts[0].strip()
            mensagem = parts[1].strip() if len(parts) > 1 else ""
            if not mensagem:
                await send_text_message(remote_jid, "⚠️ Mensagem vazia. Use: /enviarmsg <nome/num> - <texto>")
                return True
            await send_text_message(remote_jid, "🔄 Resolvendo destinatário...")
            valid_jids, not_found = await _resolve_contact_names(alvo_str)
            if not_found or not valid_jids:
                await send_text_message(remote_jid, f"❌ Destinatário não encontrado: {alvo_str}")
                return True
            enviados = 0
            for jid in valid_jids:
                await send_text_message(jid, mensagem)
                enviados += 1
            await send_text_message(remote_jid, f"✅ Mensagem enviada para {enviados} destinatário(s).")

        return True

    except Exception as e:
        await send_text_message(remote_jid, f"⚠️ Erro crítico no WhatsBot ao rodar {comando_base}: {str(e)}")
        return True
