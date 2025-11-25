import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, Response, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import re 

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# Lee la clave de la variable de entorno de Render (seguro)
API_KEY = os.environ.get("GEMINI_API_KEY", "CLAVE_LOCAL_TEST") 
try:
    genai.configure(api_key=API_KEY)
    # El modelo más estable que encontramos
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    # Este error se imprimirá en los logs de Render
    print(f"❌ ERROR CONFIGURANDO GEMINI: {e}")

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS (RENDER)
# ==========================================
def obtener_conexion():
    try:
        # Usa la variable de entorno que Render provee directamente
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        # Fallback para pruebas locales
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception:
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
# ... (rest of the functions are here) ...

# --- CEREBRO DE LA APLICACIÓN (SIN CAMBIOS) ---
def consultar_gemini(mensaje_usuario):
    # Lógica de Gemini (sin cambios, ya probada)
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"Instrucciones: {mensaje_usuario}")
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, mi cerebro está en mantenimiento. Intenta de nuevo en 1 minuto."

# ==========================================
# 3. SERVIDOR WEB (RUTAS BLINDADAS)
# ==========================================
@app.route('/', methods=['GET'])
def health_check():
    """Ruta para chequeo de salud de Render."""
    return "OK", 200

@app.route('/webhooks/telegram', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    # ... (rest of chat logic to save history and return XML) ...
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', request.values.get('text', ''))
    
    print(f"📩 Recibido: {mensaje_in}")

    respuesta = consultar_gemini(mensaje_in)
    guardar_historial(celular, mensaje_in, respuesta)

    resp = MessagingResponse()
    resp.message(respuesta)
    
    return Response(str(resp), mimetype='application/xml')

# ESTO ES LO CRÍTICO: SOLO DEJAR QUE GUNICORN LO ARRANQUE
# Eliminamos la función __name__ == main para que Render use solo el Procfile.

# Agrega esta línea para que Python no se queje de la indentación:
print("Listo para la ultima fase.")