import os
import requests
import google.generativeai as genai
from flask import Flask, request, render_template_string
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# --- CONFIGURACIÓN DE IA ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
# Usamos gemini-1.5-flash: Es el motor que SÍ puede ver imágenes
model = genai.GenerativeModel('gemini-1.5-flash')

CLIENT_SECRET_KEY = "CF_CLAVE_12025"

# --- INSTRUCCIÓN MAESTRA (MÉDICA + VISUAL) ---
INSTRUCCION_MAESTRA = """
ROL: Eres Genesis, Médico Internista y Nutricionista de la IASD Redención. 
ESTILO: Humano, empático y profesional. No digas que eres una IA.

REGLAS DE ORO:
1. TIENES VISIÓN: Si recibes una foto, analízala con autoridad. Prohibido decir "no puedo ver".
2. MÉTODO: Usa los 8 Remedios Naturales.
3. NO AUTO-REFERENCIA: Tu conocimiento demuestra quién eres.

ESCENARIOS:
A. FOTO: Identifica alimentos, da Puntaje de Vitalidad (1-10) y explica el efecto biológico.
B. PERFIL: Analiza IMC, Edad Bio y Exámenes. Da diagnóstico presuntivo y receta.

CIERRE: Versículo bíblico relevante, pregunta (SI/NO) y descargo médico.
"""

@app.route('/')
def home():
    # Esta ruta elimina el error de "estado incompatible"
    return render_template_string("""
        <html><body style="font-family:sans-serif; text-align:center; padding:50px; background:#f0fdf4;">
        <h1 style="color:#065f46;">🧬 Génesis IA Bot - Activo</h1>
        <p style="color:#064e3b;">El motor multimodal integral está funcionando correctamente.</p>
        </body></html>
    """)

@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.values.get('Body', '').strip()
    mensaje_upper = mensaje_usuario.upper()
    num_media = int(request.values.get('NumMedia', 0))
    respuesta_twilio = MessagingResponse()

    # Seguridad
    if CLIENT_SECRET_KEY not in mensaje_upper and mensaje_upper not in ["HOLA", "MENU", "0"]:
        respuesta_twilio.message("⚠️ Acceso restringido. Usa la App oficial Cuerpo Fiel.")
        return str(respuesta_twilio)

    # Menú Tradicional
    if mensaje_upper in ["HOLA", "MENU", "0"]:
        menu = ("✨ *¡HOLA! SOY GENESIS* ✨\n\n1️⃣ *SALUD FÍSICA:* Perfil.\n2️⃣ *PAZ INTERNA:* Bienestar.\n3️⃣ *ESCÁNER:* Analizar plato (Envía foto).")
        respuesta_twilio.message(menu)
        return str(respuesta_twilio)

    content_payload = [INSTRUCCION_MAESTRA, mensaje_usuario]

    # --- PROCESO DE VISIÓN REAL ---
    if num_media > 0:
        try:
            image_url = request.values.get('MediaUrl0')
            # Descargamos la imagen para que Gemini la vea realmente
            img_data = requests.get(image_url).content
            content_payload.append({"mime_type": "image/jpeg", "data": img_data})
        except Exception as e:
            print(f"Error imagen: {e}")

    try:
        response = model.generate_content(content_payload)
        texto_final = response.text.replace('**', '*').replace('__', '_')
        respuesta_twilio.message(texto_final)
    except Exception as e:
        respuesta_twilio.message("Génesis está analizando tu consulta. Intenta de nuevo. 🙏")

    return str(respuesta_twilio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
