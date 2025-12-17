import os
import requests
import google.generativeai as genai
from flask import Flask, request, render_template_string
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE IA (MODELO MULTIMODAL)
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
# Usamos gemini-1.5-flash porque es el que mejor procesa imágenes y texto juntos
model = genai.GenerativeModel('gemini-1.5-flash')

CLIENT_SECRET_KEY = "CF_CLAVE_12025"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA UNIFICADA (UNIÓN DE TODAS LAS VERSIONES)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis, Médico Especialista en Medicina Interna y Nutricionista Clínico de la IASD Redención. 
Tu estilo es 100% HUMANO, empático y profesional. No digas "Soy una IA" o "Soy de texto".

// --- REGLAS DE ORO ---
1. TIENES OJOS: Si recibes una imagen, analízala directamente. Identifica ingredientes y porciones.
2. CONTEXTO DE FE: Alinea todo a los 8 Remedios Naturales.
3. FORMATO: Usa negritas y emojis.

// --- ESCENARIOS DE RESPUESTA ---
A. SI EL USUARIO ENVÍA UNA FOTO: 
   - Identifica cada alimento.
   - Da un 'Puntaje de Vitalidad' (1-10).
   - Explica el beneficio biológico en el cuerpo.
   - Sugiere una mejora natural con amor.

B. SI EL USUARIO ENVÍA UN PERFIL (Texto con IMC, Edad Bio, etc):
   - Realiza un análisis clínico detallado.
   - Genera un diagnóstico presuntivo.
   - Da una receta de estilo de vida basada en los pilares más débiles.

C. SI EL USUARIO NAVEGA EL MENÚ:
   - Responde según el área (Salud Física, Paz Interna, Comunidad).

CIERRE OBLIGATORIO:
- Versículo bíblico relevante.
- Pregunta: '¿Te gustaría saber más (SI/NO) sobre este punto o ver el Menú?'
- Descargo: 'Consulte a su médico tratante para un diagnóstico completo. 🙏'
"""

# ==========================================
# 3. RUTAS DEL SERVIDOR
# ==========================================

@app.route('/')
def home():
    return render_template_string("""
        <html><body style="font-family:sans-serif; text-align:center; padding:50px; background:#f0fdf4;">
        <h1 style="color:#065f46;">🧬 Génesis IA Bot - Activo</h1>
        <p style="color:#064e3b;">El servidor multimodal está funcionando correctamente.</p>
        <div style="margin-top:20px; font-size:12px; color:#666;">IASD Redención - Barranquilla</div>
        </body></html>
    """)

@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.values.get('Body', '').strip()
    mensaje_upper = mensaje_usuario.upper()
    num_media = int(request.values.get('NumMedia', 0))
    respuesta_twilio = MessagingResponse()

    # --- VALIDACIÓN DE SEGURIDAD ---
    if CLIENT_SECRET_KEY not in mensaje_upper and mensaje_upper not in ["HOLA", "0", "1", "2", "3", "4", "MENU", "INICIO"]:
        respuesta_twilio.message("⚠️ Acceso restringido. Por favor, usa la aplicación oficial Cuerpo Fiel.")
        return str(respuesta_twilio)

    # --- LÓGICA DE MENÚS RÁPIDOS ---
    if mensaje_upper in ["HOLA", "MENU", "INICIO", "0"]:
        menu = ("✨ *¡HOLA! SOY GENESIS* ✨\nTu Guía Saludable.\n\n"
                "1️⃣ *MI SALUD FÍSICA:* Análisis de Perfil y Exámenes.\n"
                "2️⃣ *MI PAZ INTERNA:* Mente y Bienestar.\n"
                "3️⃣ *MI COMUNIDAD:* Iglesias y Radio.\n"
                "4️⃣ *ESCÁNER:* Analizar mi plato (Envía foto).")
        respuesta_twilio.message(menu)
        return str(respuesta_twilio)

    # --- PREPARACIÓN DE PAYLOAD MULTIMODAL ---
    content_list = [INSTRUCCION_SISTEMA, mensaje_usuario]

    # SI LLEGA IMAGEN (ESCÁNER NUTRICIONAL)
    if num_media > 0:
        try:
            image_url = request.values.get('MediaUrl0')
            # Descargar la imagen de WhatsApp/Twilio
            img_data = requests.get(image_url).content
            content_list.append({
                "mime_type": "image/jpeg",
                "data": img_data
            })
        except Exception as e:
            print(f"Error al bajar imagen: {e}")

    # --- CONSULTA A GEMINI ---
    try:
        response = model.generate_content(content_list)
        texto_final = response.text.replace('**', '*').replace('__', '_')
        respuesta_twilio.message(texto_final)
    except Exception as e:
        print(f"Error Gemini: {e}")
        respuesta_twilio.message("Génesis está analizando tu consulta. Por favor, intenta de nuevo en un momento. 🙏")

    return str(respuesta_twilio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
