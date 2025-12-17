import os
import requests
import google.generativeai as genai
from flask import Flask, request, render_template_string
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# --- CONFIGURACIÓN DE IA ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

CLIENT_SECRET_KEY = "CF_CLAVE_12025"

INSTRUCCION_SISTEMA = """
ROL: Eres Genesis, Médico Internista y Nutricionista de la IASD Redención.
TIENES VISIÓN: Puedes ver y analizar fotos de comida con precisión.
REGLA CRÍTICA: NUNCA digas "no puedo ver la foto". Si recibes una imagen, identifícala detalladamente.
ESTRUCTURA:
1. Identifica ingredientes.
2. Da 'Puntaje de Vitalidad' (1-10) según 8 Remedios Naturales.
3. Explica beneficio fisiológico.
4. Cierra con versículo bíblico y pregunta interactiva (SI/NO).
"""

# --- RUTA PARA EVITAR EL ERROR 404 ---
@app.route('/')
def home():
    return render_template_string("""
        <html><body style="font-family:sans-serif; text-align:center; padding:50px;">
        <h1>🧬 Génesis IA Bot - Activo</h1>
        <p>El servidor está funcionando correctamente.</p>
        </body></html>
    """)

# --- RUTA DEL BOT ---
@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.values.get('Body', '').strip()
    num_media = int(request.values.get('NumMedia', 0))
    respuesta_twilio = MessagingResponse()
    
    # Seguridad
    if CLIENT_SECRET_KEY not in mensaje_usuario.upper() and mensaje_usuario.upper() != "HOLA":
        respuesta_twilio.message("⚠️ Acceso Restringido. Usa la App oficial.")
        return str(respuesta_twilio)

    content_payload = [INSTRUCCION_SISTEMA, mensaje_usuario]

    # PROCESAR IMAGEN REAL
    if num_media > 0:
        try:
            image_url = request.values.get('MediaUrl0')
            # Descargamos la imagen de Twilio para pasársela a Gemini
            img_data = requests.get(image_url).content
            content_payload.append({"mime_type": "image/jpeg", "data": img_data})
        except Exception as e:
            print(f"Error imagen: {e}")

    try:
        response = model.generate_content(content_payload)
        texto_final = response.text.replace('**', '*').replace('__', '_')
        respuesta_twilio.message(texto_final)
    except Exception as e:
        respuesta_twilio.message("Génesis está analizando tu consulta. Intenta de nuevo en un momento. 🙏")

    return str(respuesta_twilio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
