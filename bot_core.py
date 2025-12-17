import os
import requests
import google.generativeai as genai
from flask import Flask, request, render_template_string
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Configuración de IA
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

CLIENT_SECRET_KEY = "CF_CLAVE_12025"

# LA UNIÓN DE TUS DOS INSTRUCCIONES (MÉDICA + VISUAL)
INSTRUCCION_MAESTRA = """
ROL: Eres Genesis, Médico Especialista en Medicina Interna y Nutricionista del Ministerio de Salud Adventista.
TU ESTILO: 100% HUMANO, empático y profesional. No digas que eres una IA.

REGLAS DE ORO:
1. TIENES VISIÓN: Si recibes una foto, analízala con autoridad médica. Nunca digas "no puedo ver".
2. NO AUTO-REFERENCIA: No uses frases como "Como médico" o "Mi rol es". Tu conocimiento demuestra quién eres.
3. ESTÁNDAR: Te basas en los 8 Remedios Naturales y la nutrición basada en plantas.

ESCENARIOS:
A. SI LLEGA UNA FOTO: Identifica alimentos, da Puntaje de Vitalidad (1-10) y explica el efecto biológico.
B. SI LLEGA UN PERFIL: Analiza IMC, Edad Bio y Exámenes. Da un diagnóstico presuntivo y una receta de acción.

CIERRE OBLIGATORIO:
- Versículo bíblico relevante al tema.
- Pregunta: '¿Te gustaría saber más (SI/NO) sobre este Remedio Natural o los otros 7 pilares?'
- Descargo: 'Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏'
"""

@app.route('/')
def home():
    return render_template_string("""
        <html><body style="font-family:sans-serif; text-align:center; padding:50px; background:#f0fdf4;">
        <h1 style="color:#065f46;">🧬 Génesis IA Bot - Activo</h1>
        <p style="color:#064e3b;">El servidor multimodal integral está funcionando correctamente.</p>
        </body></html>
    """)

@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.values.get('Body', '').strip()
    mensaje_upper = mensaje_usuario.upper()
    num_media = int(request.values.get('NumMedia', 0))
    respuesta_twilio = MessagingResponse()

    # Seguridad
    if CLIENT_SECRET_KEY not in mensaje_upper and mensaje_upper not in ["HOLA", "MENU", "0", "1", "2", "3"]:
        respuesta_twilio.message("⚠️ Acceso restringido. Usa la App oficial Cuerpo Fiel.")
        return str(respuesta_twilio)

    # Menú que tanto te gusta
    if mensaje_upper in ["HOLA", "MENU", "0"]:
        menu = ("✨ *¡HOLA! SOY GENESIS* ✨\nTu Guía Saludable.\n\n"
                "1️⃣ *SALUD FÍSICA:* Perfil y Exámenes.\n"
                "2️⃣ *PAZ INTERNA:* Bienestar emocional.\n"
                "3️⃣ *ESCÁNER:* Analizar mi plato (Envía foto).")
        respuesta_twilio.message(menu)
        return str(respuesta_twilio)

    content_payload = [INSTRUCCION_MAESTRA, mensaje_usuario]

    # PROCESO DE VISIÓN REAL (CORREGIDO)
    if num_media > 0:
        try:
            image_url = request.values.get('MediaUrl0')
            img_data = requests.get(image_url).content
            content_payload.append({"mime_type": "image/jpeg", "data": img_data})
        except: pass

    try:
        response = model.generate_content(content_payload)
        texto_final = response.text.replace('**', '*').replace('__', '_')
        respuesta_twilio.message(texto_final)
    except:
        respuesta_twilio.message("Génesis está analizando tus datos. Por favor, intenta de nuevo. 🙏")

    return str(respuesta_twilio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
