import os
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import re

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE IA Y SEGURIDAD
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
# Usamos gemini-1.5-flash por su capacidad multimodal y rapidez
model = genai.GenerativeModel('gemini-1.5-flash')

CLIENT_SECRET_KEY = "CF_CLAVE_12025"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA UNIFICADA
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis, Médico Especialista en Medicina Interna y Nutricionista de la IASD Redención.
TU ESTILO: 100% Humano, empático y profesional. No digas "Soy una IA".

REGLAS DE PROCESAMIENTO:
1. SI LLEGA UNA FOTO: Identifica alimentos, da Puntaje Edénico (1-10) y explica el beneficio biológico.
2. SI LLEGA UN PERFIL DE SALUD: Analiza IMC, Edad Bio y métricas. Da un diagnóstico presuntivo y pasos de acción.
3. SI ES UNA PREGUNTA GENERAL: Responde basándote en los 8 Remedios Naturales.

CIERRE OBLIGATORIO:
- Un versículo bíblico relevante.
- Pregunta interactiva: '¿Deseas saber más (SI/NO) sobre este punto o ver el Menú?'
- Descargo: 'Consulte a su médico tratante. 🙏'
"""

# =========================================================================
# 3. MENÚS DE NAVEGACIÓN
# =========================================================================
MENU_PRINCIPAL = """
✨ *¡HOLA! SOY GENESIS* ✨
Tu Guía Integral de Salud. ¿Cómo puedo ayudarte hoy?

1️⃣ *MI SALUD FÍSICA:* Análisis de Perfil y Exámenes.
2️⃣ *MI PAZ INTERNA:* Bienestar emocional y test mental.
3️⃣ *MI COMUNIDAD:* Iglesias y Radio AWR.
4️⃣ *ESCÁNER NUTRICIONAL:* Analizar mi plato (Envía foto).

*Responde el número o 0 para volver.*
"""

SUB_MENU_SALUD = """
🩺 *Área 1: Salud Física*
P. *PROGRESO:* Ver mi puntaje.
C. *CONSULTA:* Preguntar sobre un síntoma.
O. *PROTOCOLOS:* Guías de HTA o Diabetes.
"""

# ==========================================
# 4. LÓGICA DEL BOT
# ==========================================

@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.values.get('Body', '').strip()
    mensaje_upper = mensaje_usuario.upper()
    num_media = int(request.values.get('NumMedia', 0))
    respuesta_twilio = MessagingResponse()

    # --- VALIDACIÓN DE SEGURIDAD ---
    if CLIENT_SECRET_KEY not in mensaje_upper and mensaje_upper not in ["HOLA", "0", "1", "2", "3", "4"]:
        respuesta_twilio.message("⚠️ Acceso restringido. Usa la App oficial Cuerpo Fiel.")
        return str(respuesta_twilio)

    # --- LÓGICA DE MENÚS (SIN IA) ---
    if mensaje_upper == "HOLA" or mensaje_upper == "0":
        respuesta_twilio.message(MENU_PRINCIPAL)
        return str(respuesta_twilio)
    
    if mensaje_upper == "1":
        respuesta_twilio.message(SUB_MENU_SALUD)
        return str(respuesta_twilio)

    # --- LÓGICA DE IA (MULTIMODAL) ---
    content_payload = [INSTRUCCION_SISTEMA, mensaje_usuario]

    # Si hay una imagen (Escáner Nutricional)
    if num_media > 0:
        try:
            image_url = request.values.get('MediaUrl0')
            img_data = requests.get(image_url).content
            content_payload.append({"mime_type": "image/jpeg", "data": img_data})
        except Exception as e:
            print(f"Error imagen: {e}")

    try:
        # Llamada a Gemini
        response = model.generate_content(content_payload)
        texto_final = response.text.replace('**', '*').replace('__', '_')
        respuesta_twilio.message(texto_final)
    except Exception as e:
        respuesta_twilio.message("Génesis está analizando tus datos. Por favor, intenta de nuevo. 🙏")

    return str(respuesta_twilio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
