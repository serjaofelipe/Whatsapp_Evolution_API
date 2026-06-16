"""
WhatsApp Template Atlas - Assistente IA
========================================
Motor de IA usando Groq (Llama 3.3) como cérebro principal
e Google Gemini Flash como fallback.

Inclui ferramentas de sistema, rede, visão, jogos e execução de scripts.
"""
import os
import subprocess
import json
import asyncio
import re
import unicodedata
import platform
from typing import Optional
from pathlib import Path
from groq import AsyncGroq
from dotenv import load_dotenv

from evolution_api_client import send_text_message
import state_manager
import logger_ai

# Skills
from skills.python_executor import run_dynamic_script
from skills.vision_manager import analyze_computer_screen
from skills.file_manager import write_to_file
from skills.system_manager import analyze_disks, analyze_folders, open_url, get_hardware_specs
from skills.network_manager import get_geolocation_and_ip, run_network_diagnostics

SISTEMA = platform.system()


def execute_system_command(command: str, is_confirmed: bool = False) -> str:
    """Executa um comando no terminal (PowerShell no Windows, bash no Mac)."""
    print(f"[OpenClaw] Executando comando: {command}")
    
    # Validação de Segurança
    command_lower = command.lower()
    destructive_list = ['rmdir', 'diskpart', 'mkfs', 'del ', 'format ', 'shutdown', 'reboot', 'erase ', 'rd ']
    
    if re.search(r'(?i)\b(rm|del|format|shutdown|reboot|rmdir|diskpart)\b', command) or any(cmd in command_lower for cmd in destructive_list):
        if not is_confirmed:
            return "Ação destrutiva detectada. Solicite confirmação ao usuário pelo WhatsApp (ex: 'Confirma que deseja rodar este comando perigoso?'). Se ele aprovar, chame novamente com is_confirmed=True."

    try:
        if SISTEMA == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, timeout=120
            )
        else:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True, timeout=120
            )
            
        # Tenta decodificar de forma robusta (CP850 > UTF-8 > Fallback)
        def robust_decode(b):
            if not b: return ""
            try: return b.decode('cp850')
            except: 
                try: return b.decode('utf-8')
                except: return b.decode('cp1252', errors='replace')
                
        output = robust_decode(result.stdout).strip()
        err = robust_decode(result.stderr).strip()
        
        if len(output) > 1000: output = output[:1000] + "\n...[TRUNCADO]"
        if len(err) > 1000: err = err[:1000] + "\n...[TRUNCADO]"
        if err: return f"Comando executado com alertas:\n{err}\n{output}"
        if not output: return "Comando executado com sucesso (sem saída)."
        return output
    except subprocess.TimeoutExpired:
        return "Erro: Timeout de 120 segundos."
    except Exception as e:
        return f"Erro ao executar: {str(e)}"


def get_groq_client():
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return AsyncGroq(api_key=api_key)
    return None


def get_groq_tools(user_prompt: str = "") -> list:
    """Retorna todas as ferramentas disponíveis para o LLM."""
    
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    
    user_prompt_lower = remover_acentos(user_prompt.lower())
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_system_command",
                "description": f"Executa um comando no terminal do {'Windows (PowerShell)' if SISTEMA == 'Windows' else 'macOS (bash)'}. Use ';' para encadear comandos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "O comando a ser executado."},
                        "is_confirmed": {"type": "boolean", "description": "Sete como true se o usuário confirmou a execução de um comando perigoso."}
                    },
                    "required": ["command"]
                }
            }
        }
    ]
    
    script_tools = [
        {
            "type": "function",
            "function": {
                "name": "run_dynamic_script",
                "description": "Cria e executa um script Python dinâmico no computador. Use para automações, web scraping, scripts complexos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Código Python completo."},
                        "project_name": {"type": "string", "description": "Nome da pasta do projeto."},
                        "is_confirmed": {"type": "boolean", "description": "Sete como true se o usuário confirmou a execução."}
                    },
                    "required": ["code", "project_name"]
                }
            }
        }
    ]
    
    general_tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_computer_screen",
                "description": "Tira um print da tela e descreve o que está nela usando Gemini Vision.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Instruções do que analisar."}
                    },
                    "required": ["prompt"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_to_file",
                "description": "Cria ou sobrescreve um arquivo de texto/código.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Caminho absoluto do arquivo."},
                        "content": {"type": "string", "description": "Conteúdo do arquivo."}
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_disks",
                "description": "Lê todos os discos e retorna espaço total, usado e livre.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_hardware_specs",
                "description": "Obtém CPU, RAM, GPU e Sistema Operacional da máquina.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_folders",
                "description": "Varre subpastas de um caminho e retorna a mais pesada e a mais leve.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Caminho do diretório a analisar."}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_geolocation_and_ip",
                "description": "Descobre IP público, ISP, Cidade, Estado e País.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_network_diagnostics",
                "description": "SpeedTest real, ping do Google e conexões ativas.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "open_url",
                "description": "Abre um link no navegador (YouTube, sites, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL completa."}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_installed_games",
                "description": "Lista todos os jogos instalados (Steam, Epic, Riot, etc.) com tamanho em GB.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_game_size",
                "description": "Retorna o tamanho de um jogo específico instalado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "game_name": {"type": "string", "description": "Nome do jogo (parcial ou completo)."}
                    },
                    "required": ["game_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "launch_game",
                "description": "Abre/inicia um jogo no computador.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "game_name": {"type": "string", "description": "Nome do jogo."}
                    },
                    "required": ["game_name"]
                }
            }
        }
    ]
    
    final_tools = tools + general_tools
    if any(kw in user_prompt_lower for kw in ["pc", "computador", "terminal", "script", "codigo", "sistema"]):
        final_tools += script_tools
        
    return final_tools


async def dispatch_tool_call(function_name: str, arguments: str, remote_jid: str = "") -> str:
    """Executa a ferramenta solicitada."""
    try:
        args = json.loads(arguments) if arguments else {}
    except Exception as e:
        return f"Erro de JSON: {str(e)}"

    try:
        if function_name == "execute_system_command":
            return await asyncio.to_thread(execute_system_command, args.get("command", ""), args.get("is_confirmed", False))
        elif function_name == "run_dynamic_script":
            code = args.get("code", "")
            code_lower = code.lower()
            destructive_list = ['os.remove', 'shutil.rmtree', 'os.system("rm', 'subprocess.run("rm', 'subprocess.run("shutdown', 'os.system("shutdown', 'rm -rf']
            
            if (re.search(r'(?i)\b(os\.remove|shutil\.rmtree|os\.system\("rm|subprocess\.run\("shutdown|rm -rf)\b', code) or any(cmd in code_lower for cmd in destructive_list)) and not args.get("is_confirmed", False):
                return "Script destrutivo detectado. Solicite confirmação."
            return await asyncio.to_thread(run_dynamic_script, code, args.get("project_name", "Script_Avulso"))
        elif function_name == "analyze_computer_screen":
            return await asyncio.to_thread(analyze_computer_screen, args.get("prompt", ""))
        elif function_name == "write_to_file":
            return await asyncio.to_thread(write_to_file, args.get("file_path", ""), args.get("content", ""))
        elif function_name == "analyze_disks":
            return await asyncio.to_thread(analyze_disks)
        elif function_name == "get_hardware_specs":
            return await asyncio.to_thread(get_hardware_specs)
        elif function_name == "analyze_folders":
            return await asyncio.to_thread(analyze_folders, args.get("path", ""))
        elif function_name == "get_geolocation_and_ip":
            return await asyncio.to_thread(get_geolocation_and_ip)
        elif function_name == "run_network_diagnostics":
            return await asyncio.to_thread(run_network_diagnostics)
        elif function_name == "open_url":
            return await asyncio.to_thread(open_url, args.get("url", ""))
        elif function_name == "list_installed_games":
            from tools.games import get_installed_games
            jogos = await asyncio.to_thread(get_installed_games, True) # skip_size=True para não travar 20s
            if not jogos: return "Nenhum jogo encontrado."
            resultado = ""
            plataformas = {}
            for j in jogos:
                p = j["plataforma"]
                if p not in plataformas: plataformas[p] = []
                plataformas[p].append(j)
            for p_name, p_jogos in plataformas.items():
                resultado += f"\n[{p_name.upper()}]\n"
                for j in p_jogos:
                    size = j.get('tamanho_gb', 0)
                    size_str = f" ({size} GB)" if size > 0 else ""
                    resultado += f"  - {j['nome']}{size_str}\n"
            return resultado.strip()
        elif function_name == "get_game_size":
            from tools.games import get_game_size as _get_size
            info = await asyncio.to_thread(_get_size, args.get("game_name", ""))
            if info: return json.dumps(info, ensure_ascii=False)
            return f"Jogo '{args.get('game_name', '')}' não encontrado."
        elif function_name == "launch_game":
            from tools.games import get_installed_games, executar_jogo
            jogos = await asyncio.to_thread(get_installed_games)
            nome_busca = args.get("game_name", "").lower()
            alvo = next((j for j in jogos if nome_busca in j["nome"].lower()), None)
            if alvo:
                await asyncio.to_thread(executar_jogo, alvo["launch_cmd"])
                return f"Jogo '{alvo['nome']}' ({alvo['plataforma']}) iniciado!"
            return f"Jogo '{args.get('game_name', '')}' não encontrado."
        else:
            return f"Ferramenta não encontrada: {function_name}"
    except Exception as e:
        return f"Erro na ferramenta {function_name}: {str(e)}"


PENDING_FALLBACKS = {}
GLOBAL_USE_GEMINI = {}

async def cleanup_fallback(remote_jid: str):
    await asyncio.sleep(120)
    if remote_jid in PENDING_FALLBACKS:
        del PENDING_FALLBACKS[remote_jid]
        print(f"[Fallback] TTL Expirado. Fallback limpo para {remote_jid}")
        await send_text_message(remote_jid, "⏳ *Aviso:* O tempo de 2 minutos para confirmar a troca de IA expirou. Comando cancelado.")

SYSTEM_PROMPT = (
    "Você é o Atlas, um assistente virtual supremo que reside no computador local do usuário. "
    "Você controla o computador remotamente via WhatsApp usando suas ferramentas.\n"
    f"Sistema Operacional detectado: {SISTEMA}.\n"
    "REGRA DE CONVERSA: Se o usuário disser apenas 'oi', 'tudo bem', ou fizer perguntas gerais, APENAS RESPONDA EM TEXTO. NÃO chame nenhuma ferramenta (como launch_game ou open_url) a menos que seja explicitamente pedido.\n"
    "REGRA DE JOGOS: SÓ inicie jogos se o usuário PEDIR EXPLICITAMENTE para abrir um jogo (ex: 'abra o jogo X', 'jogue Y'). NÃO INICIE JOGOS ALEATORIAMENTE.\n"
    "REGRA DO TERMINAL STATELESS: A ferramenta `execute_system_command` abre e fecha o terminal "
    "a cada chamada. SEMPRE encadeie comandos com ';' (ex: 'cd /pasta ; ls').\n"
    "REGRA DA VISÃO: Para analisar a tela, use `analyze_computer_screen`. NUNCA use `run_dynamic_script` para isso.\n"
    "REGRA WEB: Para abrir sites, músicas ou vídeos, use `open_url` IMEDIATAMENTE.\n"
    "REGRA DE REDE: Para speedtest/ping, use `run_network_diagnostics`. NÃO abra o site speedtest.net.\n"
    "REGRA DE DISCO: Para espaço em disco, use `analyze_disks`. Para pastas pesadas, use `analyze_folders`.\n"
    "REGRA DE INICIATIVA: NUNCA pergunte nomes para pastas/arquivos. Invente um nome coerente e faça imediatamente.\n"
    "Seja proativo, direto e eficiente."
)


async def process_assistant_request(remote_jid: str, text: Optional[str] = None, media_path: Optional[str] = None, force_gemini_turn: bool = False):
    """Processa uma requisição de chat com IA (Groq + Gemini fallback)."""
    global PENDING_FALLBACKS, GLOBAL_USE_GEMINI

    groq_client = get_groq_client()
    if not groq_client:
        await send_text_message(remote_jid, "Erro: GROQ_API_KEY não configurada.")
        return

    try:
        user_prompt = text or ""
        force_gemini = force_gemini_turn or GLOBAL_USE_GEMINI.get(remote_jid, False)

        # Verifica se está pendente de confirmação de fallback
        if remote_jid in PENDING_FALLBACKS:
            if user_prompt.strip().lower() == 'y':
                force_gemini = True
                GLOBAL_USE_GEMINI[remote_jid] = True
                messages = PENDING_FALLBACKS[remote_jid]
                del PENDING_FALLBACKS[remote_jid]
                await send_text_message(remote_jid, "🔄 Conectado ao Gemini Flash! Retomando...")
            else:
                del PENDING_FALLBACKS[remote_jid]
                await send_text_message(remote_jid, "❌ Mudança cancelada.")
                return
        else:
            # Transcreve áudio se vier mídia
            if media_path:
                if str(media_path).lower().endswith(('.ogg', '.mp3', '.wav', '.m4a')):
                    await send_text_message(remote_jid, "🎤 Ouvindo áudio com Whisper...")
                    with open(media_path, "rb") as audio_file:
                        transcription = await groq_client.audio.transcriptions.create(
                            file=(media_path, audio_file.read()),
                            model="whisper-large-v3",
                            response_format="text"
                        )
                    transcribed_text = str(transcription).strip()
                    print(f"🎤 [WHISPER] '{transcribed_text}'")
                    if user_prompt:
                        user_prompt += f"\n[Áudio: {transcribed_text}]"
                    else:
                        user_prompt = transcribed_text
                else:
                    # É uma imagem ou outro documento
                    if not force_gemini:
                        print("[Assistant] Imagem recebida. Forçando Gemini Flash pois Groq não tem visão nativa.")
                        force_gemini = True
                        GLOBAL_USE_GEMINI[remote_jid] = True

            if not user_prompt and not media_path:
                return

            messages = await state_manager.get_messages(remote_jid)
            if not messages:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                
            messages.append({"role": "user", "content": user_prompt})
            await state_manager.set_messages(remote_jid, messages)

        tools = get_groq_tools(user_prompt)
        max_turns = 15

        for turn in range(max_turns):
            try:
                try:
                    if force_gemini:
                        raise Exception("429 force gemini bypass")

                    response = await groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        max_tokens=4096
                    )
                    response_message = response.choices[0].message
                    tool_calls = response_message.tool_calls

                    msg_dict = {"role": response_message.role, "content": response_message.content}
                    if tool_calls:
                        msg_dict["tool_calls"] = [
                            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                            for tc in tool_calls
                        ]
                    messages.append(msg_dict)

                except Exception as api_err:
                    error_str = str(api_err)
                    
                    # Se não for o bypass forçado do gemini, trata como erro real do Groq
                    if "429 force gemini bypass" not in error_str:
                        if not force_gemini:
                            print(f"[OpenClaw] Erro no Groq detectado: {error_str}. Aguardando confirmação para Gemini...")
                            PENDING_FALLBACKS[remote_jid] = messages
                            asyncio.create_task(cleanup_fallback(remote_jid))
                            await state_manager.set_messages(remote_jid, messages)
                            
                            # Se for limite de cota
                            if "429" in error_str or "rate_limit" in error_str.lower() or "503" in error_str:
                                await send_text_message(remote_jid, "⚠️ *Alerta: Limite de uso do Groq atingido.*\n\nO servidor recusou a conexão temporariamente.\n\nDeseja que eu troque o cérebro para o **Gemini Flash** e continue seu projeto exatamente de onde parei?\n\nDigite *Y* para sim.")
                            else:
                                await send_text_message(remote_jid, "⚠️ *Alerta: Ocorreu uma instabilidade ou falha no Groq.*\n\nDeseja que eu troque o cérebro para o **Gemini Flash** e continue seu projeto exatamente de onde parei?\n\nDigite *Y* para sim.")
                            return
                            
                    # Se chegou aqui, force_gemini é True, então processa o Fallback diretamente
                        import httpx
                        google_key = os.getenv("GOOGLE_API_KEY")
                        if not google_key:
                            await send_text_message(remote_jid, "Groq esgotou e GOOGLE_API_KEY não está configurada.")
                            return

                        async with httpx.AsyncClient() as client:
                            # Sanitiza o histórico para o Gemini (remove tool_calls anteriores para evitar erros 400 de sintaxe rígida)
                            sanitized = []
                            for m in messages:
                                role = m.get("role")
                                content = str(m.get("content") or "")
                                if role == "system":
                                    sanitized.append(m)
                                elif role == "user" and content:
                                    sanitized.append({"role": "user", "content": content})
                                elif role == "assistant" and content:
                                    sanitized.append({"role": "assistant", "content": content})
                                elif role == "tool" and content:
                                    name = m.get("name", "Desconhecida")
                                    sanitized.append({"role": "user", "content": f"[Resultado da Ferramenta {name}]:\n{content}"})
                                    
                            # Mescla roles consecutivos
                            merged = []
                            for m in sanitized:
                                if not merged: merged.append(m)
                                else:
                                    if merged[-1]["role"] == m["role"]:
                                        merged[-1]["content"] += "\n" + m["content"]
                                    else:
                                        merged.append(m)
                                        
                            # Garante que termine com user
                            if merged and merged[-1]["role"] != "user":
                                merged.append({"role": "user", "content": "Continue."})

                            resp = await client.post(
                                'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                                headers={'Authorization': f'Bearer {google_key}'},
                                json={
                                    'model': 'gemini-2.5-flash',
                                    'messages': merged,
                                    'tools': tools,
                                    'tool_choice': 'auto',
                                    'max_tokens': 4096
                                },
                                timeout=120
                            )
                            if resp.status_code != 200:
                                raise Exception(f"Gemini API Error: {resp.text}")

                            response_json = resp.json()
                            msg_data = response_json['choices'][0]['message']

                            class FakeToolCall:
                                def __init__(self, id, name, args):
                                    self.id = id
                                    class Func: pass
                                    self.function = Func()
                                    self.function.name = name
                                    self.function.arguments = args

                            tool_calls = []
                            if 'tool_calls' in msg_data:
                                for tc in msg_data['tool_calls']:
                                    tool_calls.append(FakeToolCall(tc['id'], tc['function']['name'], tc['function']['arguments']))

                            class FakeMsg: pass
                            response_message = FakeMsg()
                            response_message.content = msg_data.get('content')

                            messages.append(msg_data)
                    else:
                        raise api_err

            except Exception as api_err:
                error_str = str(api_err)
                if "invalid_request_error" in error_str or "tool_use_failed" in error_str:
                    await send_text_message(remote_jid, "O cérebro tropeçou na sintaxe. Tente simplificar o pedido.")
                    return
                else:
                    raise api_err

            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    await logger_ai.log_ai_usage(remote_jid, "Groq/Gemini", "Chamou Tool", function_name)
                    tool_result = await dispatch_tool_call(function_name, tool_call.function.arguments, remote_jid)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_result,
                    })
                    
                    if function_name == "delegate_to_antigravity":
                        await state_manager.set_messages(remote_jid, messages)
                        return
                        
                await state_manager.set_messages(remote_jid, messages)
            else:
                await logger_ai.log_ai_usage(remote_jid, "Groq/Gemini", "Mensagem de Texto", f"Tamanho: {len(response_message.content or '')} chars")
                if response_message.content:
                    await send_text_message(remote_jid, response_message.content)
                await state_manager.set_messages(remote_jid, messages)
                break

    except Exception as e:
        error_msg = str(e)
        print(f"[Assistant] Erro Crítico: {error_msg}")
        if "connect" in error_msg.lower() or "timeout" in error_msg.lower() or "socket" in error_msg.lower():
            await send_text_message(remote_jid, "⚠️ Ops, parece que estou com problemas de conexão e estou temporariamente offline. Tente novamente em alguns minutos!")
        else:
            await send_text_message(remote_jid, f"Erro crítico: {error_msg[:100]}...")
