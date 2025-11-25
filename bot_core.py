import os 
import psycopg2
import google.generativeai as genai
from flask import Flask, request, Response, jsonify # Importamos Response para la respuesta XML
from twilio.twiml.messaging_response import MessagingResponse
import re 

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# (Tu clave API es ignorada aquí, pero se lee de la variable de entorno de Render)
API_KEY = os.environ.get("GEMINI_API_KEY", "TU_CLAVE_LOCAL") 

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    # Si falla, el bot responderá con el error de respaldo
    pass 

# INSTRUCCIÓN MAESTRA para Gemini
INSTRUCCION_SISTEMA = """
Eres 'Cuerpo Fiel', asistente de salud adventista.
Tu base son los 8 Remedios Naturales (ADELANTE).
REGLAS OBLIGATORIAS: Responde corto (máximo 100 palabras) y usa un versículo bíblico.
"""
# ... (rest of the functions: obtener_conexion, guardar_historial, consultar_gemini are here) ...

# ==========================================
# 4. SERVIDOR WEB (RUTAS)
# ==========================================

# ⚠️ RUTA AGREGADA PARA QUE RENDER NO MATE EL SERVIDOR 
@app.route('/', methods=['GET'])
def health_check():
    """Ruta para chequeo de salud de Render. Debe retornar 200 OK."""
    return "OK", 200

@app.route('/webhooks/telegram', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos limpios
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', request.values.get('text', '')) # Manejo de Telegram/Twilio
    
    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)
    
    # 4. Responder a Telegram/Twilio
    if 'whatsapp' in celular.lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        # Devolver XML con el header correcto
        return Response(str(resp), mimetype='application/xml')

    # Si es Telegram o prueba local, devolvemos JSON (o simplemente el 200 OK que espera Telegram)
    return jsonify({"status": "success", "response": respuesta}), 200