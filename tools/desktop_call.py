import time
import webbrowser
import pyautogui
import os

def iniciar_chamada_desktop(numero_limpo: str):
    """
    Usa o protocolo nativo 'whatsapp://' para abrir o app WhatsApp Desktop
    focado na conversa do número, e usa Visão Computacional para clicar no 
    ícone de chamada de vídeo.
    """
    try:
        pyautogui.FAILSAFE = False
        print(f"[Desktop Call] Iniciando chamada de vídeo para o número {numero_limpo}...")
        
        # Abre o aplicativo oficial do WhatsApp no Windows
        url = f"whatsapp://send?phone={numero_limpo}"
        webbrowser.open(url)
        
        # Aguarda a janela do WhatsApp Desktop carregar a conversa e ganhar foco
        time.sleep(4)
        
        # Caminho da imagem que o PyAutoGUI vai procurar na tela
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "video_icon.png")
        
        if not os.path.exists(icon_path):
            print(f"[Desktop Call] ERRO: A imagem de referência não existe em {icon_path}.")
            print("Por favor, tire um print pequeno do ícone da câmera de vídeo no WhatsApp e salve como 'video_icon.png' na pasta 'tools'.")
            return
            
        print("[Desktop Call] Procurando ícone de câmera de vídeo na tela...")
        # Localiza o centro da imagem na tela (confidence=0.8 requer opencv-python)
        posicao = pyautogui.locateCenterOnScreen(icon_path, confidence=0.8)
        
        if posicao:
            x, y = int(posicao.x), int(posicao.y)
            print(f"[Desktop Call] Ícone encontrado na posição ({x}, {y}). Clicando...")
            
            # Move o mouse primeiro suavemente (ajuda o app UWP a registrar o foco)
            pyautogui.moveTo(x, y, duration=0.3)
            time.sleep(0.2)
            
            # Executa o PRIMEIRO clique
            pyautogui.click()
            
            # Aguarda 2 segundos para garantir o registro do app
            time.sleep(2)
            
            # Executa o SEGUNDO clique para garantir a chamada
            pyautogui.click()
            
            print("[Desktop Call] Chamada iniciada com sucesso (com duplo clique de segurança)!")
        else:
            print("[Desktop Call] Ícone de câmera de vídeo NÃO encontrado na tela.")
            
    except Exception as e:
        print(f"[Desktop Call] Erro ao tentar ligar: {e}")
