import os # <--- NECESARIO PARA LEER EL PUERTO DE RENDER
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, Response
from twilio.twiml.messaging_response import MessagingResponse
import re 

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# OJO: DEBES PEGAR TU CLAVE AQUI, AUNQUE EN LA NUBE USARÁ VARIABLES DE ENTORNO.
API_KEY = "8101058820:AAH04AcCXiQTXRAaqkDe5BaQC-_iHp9uG7o" 

try:
    genai.configure(api_key=API_KEY)
    # Usamos el modelo estable que tu escáner encontró
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"⚠️ Error configurando Gemini: {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Bot)
INSTRUCCION_SISTEMA = """
Eres 'Cuerpo Fiel', asistente de salud médico-misionero de la Iglesia Adventista (Distrito Redención).
Tu base son los 8 Remedios Naturales (ADELANTE).

REGLAS OBLIGATORIAS:
1. SÉ MUY BREVE: Tus respuestas NO deben pasar de 100 palabras.
2. Si detectas un síntoma, da un consejo basado en NEWSTART y una promesa bíblica.
3. ADVERTENCIA LEGAL: Aclara que no eres un médico humano.
"""

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
DB_CONFIG = {
    "user": "root", "password": "root", 
    "host": "localhost", "port": "5432",
    "database": "cuerpo_fiel_db"
}

def obtener_conexion():
    try:
        # 1. Conexión a la NUBE (Render)
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        
        # 2. Conexión LOCAL (Laptop)
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

# ==========================================
# 3. LÓGICA DE LA APLICACIÓN
# ==========================================
def consultar_gemini(mensaje_usuario):
    # Limpieza de input y manejo de saludos
    mensaje_norm = mensaje_usuario.upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
    
    # Manejo de saludo simplificado
    if any(s in mensaje_norm for s in ["HOLA", "MENU", "DIAS"]):
        return ("👋 ¡Bienvenido a Cuerpo Fiel 4.0! Soy tu asistente de salud basado en los 8 Remedios Naturales. "
                "Escribe un síntoma (ej: 'Glucosa 120') o una emoción (ej: 'Ansiedad').")

    try:
        chat = model.start_chat(history=[])
        prompt_final = f"{INSTRUCCION_SISTEMA}\n\nEl usuario dice: {mensaje_usuario}"
        
        response = chat.send_message(prompt_final)
        # Limpieza final de la respuesta
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, mi cerebro central está saturado. Intenta de nuevo en un momento."

# ==========================================
# 4. SERVIDOR WEB (RUTAS)
# ==========================================
@app.route('/webhooks/telegram', methods=['POST']) # RUTA DE TELEGRAM
@app.route('/chat', methods=['POST']) # RUTA DE TWILIO/TESTING
def chat():
    # 1. Recibir y obtener datos limpios
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', request.values.get('text', ''))
    
    # 2. Consultar y Guardar
    respuesta = consultar_gemini(mensaje_in)
    guardar_historial(celular, mensaje_in, respuesta)

    # 3. Responder (Para Twilio, simplemente devolvemos XML)
    if 'whatsapp' in celular.lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        # Devolver XML con el header correcto para Twilio
        return Response(str(resp), mimetype='application/xml')

    # 4. Responder a Telegram/Local (JSON)
    return jsonify({"status": "success", "response": respuesta}), 200

if __name__ == '__main__':
    # Render usa la variable de entorno 'PORT' (o el puerto 8080 si no está definida)
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 CUERPO FIEL 4.0 - FINAL PORT: {port}")
    # Gunicorn se encargará de ejecutar esto en la nube, pero lo dejamos para pruebas locales
    app.run(host='0.0.0.0', port=port, debug=True)