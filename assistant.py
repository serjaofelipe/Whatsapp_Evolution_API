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
import platform
from typing import Optional
from pathlib import Path
from groq import AsyncGroq
from dotenv import load_dotenv

from evolution_api_client import send_text_message

# Skills
from skills.python_executor import run_dynamic_script
from skills.vision_manager import analyze_computer_screen
from skills.file_manager import write_to_file
from skills.system_manager import analyze_disks, analyze_folders, open_url, get_hardware_specs
from skills.network_manager import get_geolocation_and_ip, run_network_diagnostics

SISTEMA = platform.system()


def execute_system_command(command: str) -> str:
    """Executa um comando no terminal (PowerShell no Windows, bash no Mac)."""
    print(f"[Assistant] Executando comando: {command}")
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


def get_tools():
    """Retorna todas as ferramentas disponíveis para o LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_system_command",
                "description": f"Executa um comando no terminal do {'Windows (PowerShell)' if SISTEMA == 'Windows' else 'macOS (bash)'}. Use ';' para encadear comandos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "O comando a ser executado."}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_dynamic_script",
                "description": "Cria e executa um script Python dinâmico no computador. Use para automações, web scraping, scripts complexos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Código Python completo."},
                        "project_name": {"type": "string", "description": "Nome da pasta do projeto."}
                    },
                    "required": ["code", "project_name"]
                }
            }
        },
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


async def dispatch_tool_call(function_name: str, arguments: str, remote_jid: str = "") -> str:
    """Executa a ferramenta solicitada."""
    try:
        args = json.loads(arguments) if arguments else {}
    except Exception as e:
        return f"Erro de JSON: {str(e)}"

    try:
        if function_name == "execute_system_command":
            return await asyncio.to_thread(execute_system_command, args.get("command", ""))
        elif function_name == "run_dynamic_script":
            return await asyncio.to_thread(run_dynamic_script, args.get("code", ""), args.get("project_name", "Script_Avulso"))
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
            jogos = await asyncio.to_thread(get_installed_games)
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

SYSTEM_PROMPT = (
    "Você é o Atlas, um assistente virtual supremo que reside no computador local do usuário. "
    "Você controla o computador remotamente via WhatsApp usando suas ferramentas.\n"
    f"Sistema Operacional detectado: {SISTEMA}.\n"
    "REGRA DO TERMINAL STATELESS: A ferramenta `execute_system_command` abre e fecha o terminal "
    "a cada chamada. SEMPRE encadeie comandos com ';' (ex: 'cd /pasta ; ls').\n"
    "REGRA DA VISÃO: Para analisar a tela, use `analyze_computer_screen`. NUNCA use `run_dynamic_script` para isso.\n"
    "REGRA WEB: Para abrir sites, músicas ou vídeos, use `open_url` IMEDIATAMENTE.\n"
    "REGRA DE REDE: Para speedtest/ping, use `run_network_diagnostics`. NÃO abra o site speedtest.net.\n"
    "REGRA DE DISCO: Para espaço em disco, use `analyze_disks`. Para pastas pesadas, use `analyze_folders`.\n"
    "REGRA DE INICIATIVA: NUNCA pergunte nomes para pastas/arquivos. Invente um nome coerente e faça imediatamente.\n"
    "Seja proativo, direto e eficiente."
)


async def process_assistant_request(remote_jid: str, text: Optional[str] = None, media_path: Optional[str] = None):
    """Processa uma requisição de chat com IA (Groq + Gemini fallback)."""
    global PENDING_FALLBACKS, GLOBAL_USE_GEMINI

    groq_client = get_groq_client()
    if not groq_client:
        await send_text_message(remote_jid, "Erro: GROQ_API_KEY não configurada.")
        return

    try:
        user_prompt = text or ""
        force_gemini = GLOBAL_USE_GEMINI.get(remote_jid, False)

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

            if not user_prompt:
                return

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

        tools = get_tools()
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
                    if "429" in error_str or "rate_limit_exceeded" in error_str or "503" in error_str:
                        if not force_gemini:
                            PENDING_FALLBACKS[remote_jid] = messages
                            await send_text_message(remote_jid,
                                "⚠️ *Limite do Groq atingido.*\n\n"
                                "Deseja trocar para o *Gemini Flash*?\n\n"
                                "Digite *Y* para sim."
                            )
                            return

                        # Fallback para Gemini
                        import httpx
                        google_key = os.getenv("GOOGLE_API_KEY")
                        if not google_key:
                            await send_text_message(remote_jid, "Groq esgotou e GOOGLE_API_KEY não está configurada.")
                            return

                        async with httpx.AsyncClient() as client:
                            resp = await client.post(
                                'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                                headers={'Authorization': f'Bearer {google_key}'},
                                json={
                                    'model': 'gemini-2.5-flash',
                                    'messages': messages,
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
                    tool_result = await dispatch_tool_call(function_name, tool_call.function.arguments, remote_jid)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_result,
                    })
            else:
                final_text = str(response_message.content) if response_message.content else "Processo concluído."
                await send_text_message(remote_jid, final_text)
                return

        await send_text_message(remote_jid, "Limite máximo de execuções atingido.")

    except Exception as e:
        error_msg = str(e)
        print(f"[Assistant] Erro Crítico: {error_msg}")
        await send_text_message(remote_jid, f"Erro crítico: {error_msg}")
