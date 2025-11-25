import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, Response, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import re 

app = Flask(__name__)

# --- 1. CONFIGURACIÓN DE BASE DE DATOS ---
def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return None

def guardar_historial(celular, mensaje, respuesta):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)", (celular, mensaje, respuesta))
            conn.commit()
            cursor.close()
            conn.close()
        except:
            pass

# --- 2. CEREBRO (Inicialización Resiliente) ---
def consultar_gemini(mensaje_usuario):
    try:
        # Inicialización del modelo movida aquí para evitar el crash del servidor Gunicorn
        API_KEY = os.environ.get("GEMINI_API_KEY", "CLAVE_LOCAL_TEST") 
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
        
        INSTRUCCION_SISTEMA = """
        Eres 'Cuerpo Fiel', asistente de salud adventista. Tu base son los 8 Remedios Naturales (ADELANTE).
        Responde en máximo 100 palabras. Usa lenguaje cristiano, da consejos NEWSTART y termina con una cita bíblica (RV1960).
        """

        chat = model.start_chat(history=[])
        response = chat.send_message(f"{INSTRUCCION_SISTEMA}\n\nEl usuario dice: {mensaje_usuario}")
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        # Si falla, imprimimos el error real en Render logs y enviamos un mensaje de falla.
        print(f"❌ ERROR FATAL EN GEMINI: {e}")
        return "⚠️ Lo siento, mi cerebro está en mantenimiento. Intenta de nuevo en 1 minuto."

# --- 3. SERVIDOR WEB (RUTAS) ---
@app.route('/', methods=['GET'])
def health_check():
    """Ruta para chequeo de salud de Render."""
    return "OK", 200

@app.route('/webhooks/telegram', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos limpios
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', request.values.get('text', ''))
    
    print(f"📩 Recibido: {mensaje_in}")

    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)

    # 3. Guardar y Responder
    guardar_historial(celular, mensaje_in, respuesta)
    
    # 4. Responder a Telegram/Twilio (Formato XML)
    resp = MessagingResponse()
    resp.message(respuesta)
    return Response(str(resp), mimetype='application/xml')

if __name__ == '__main__':
    # Usar la variable de entorno 'PORT'
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 CUERPO FIEL 4.0 - ESTABILIZADO")
    app.run(host='0.0.0.0', port=port, debug=True)