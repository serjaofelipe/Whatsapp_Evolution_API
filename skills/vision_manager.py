import os
import pyautogui
import cv2
import google.generativeai as genai
from pathlib import Path
import time
import platform

SISTEMA = platform.system()

def analyze_computer_screen(prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Erro: GOOGLE_API_KEY não configurada no .env."
    temp_img_path = None
    try:
        genai.configure(api_key=api_key)
        vision_model = genai.GenerativeModel("gemini-2.5-flash")
        temp_img_path = Path(__file__).parent.parent / "temp_media" / f"screen_{int(time.time())}.png"
        temp_img_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_img_path)
        with open(temp_img_path, "rb") as img_f:
            image_bytes = img_f.read()
        contents = [{"mime_type": "image/png", "data": image_bytes}, prompt or "Descreva o que está na minha tela."]
        response = vision_model.generate_content(contents)
        return f"Análise da Tela:\n{response.text}"
    except Exception as e:
        return f"Erro ao analisar tela: {str(e)}"
    finally:
        if temp_img_path and os.path.exists(temp_img_path):
            try: os.remove(temp_img_path)
            except: pass

def analyze_computer_webcam(prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Erro: GOOGLE_API_KEY não configurada."
    temp_img_path = None
    try:
        genai.configure(api_key=api_key)
        vision_model = genai.GenerativeModel("gemini-2.5-flash")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if SISTEMA == "Windows" else cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Erro: Câmera inacessível."
        start_time = time.time()
        while time.time() - start_time < 2.0:
            cap.read()
        ret, frame = cap.read()
        if not ret:
            return "Erro: Falha ao capturar imagem."
        temp_img_path = Path(__file__).parent.parent / "temp_media" / f"webcam_{int(time.time())}.png"
        temp_img_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(temp_img_path), frame)
        with open(temp_img_path, "rb") as img_f:
            image_bytes = img_f.read()
        contents = [{"mime_type": "image/png", "data": image_bytes}, prompt or "Descreva o que você vê."]
        response = vision_model.generate_content(contents)
        return f"Análise da Câmera:\n{response.text}"
    except Exception as e:
        return f"Erro: {str(e)}"
    finally:
        try:
            if 'cap' in locals() and cap is not None and cap.isOpened():
                cap.release()
                cv2.destroyAllWindows()
        except: pass
        if temp_img_path and os.path.exists(temp_img_path):
            try: os.remove(temp_img_path)
            except: pass
