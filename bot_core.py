import os
import psycopg2
import google.generativeai as genai
import requests # Necesario para enviar la respuesta a la API de Telegram
from flask import Flask, request, jsonify

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE TELEGRAM Y GEMINI
# ==========================================
TELEGRAM_TOKEN = "6101058028:AAHh44CxCK10TXRAAq0e5I8a0C-_iik9pGf67Q" # TU TOKEN
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

API_KEY_GEMINI = "PEGAR_TU_CLAVE_AQUI" # TU CLAVE GEMINI

try:
    genai.configure(api_key=API_KEY_GEMINI)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except:
    pass

# INSTRUCCIÓN MAESTRA para Gemini (Cerebro)
INSTRUCCION = """
Eres 'Cuerpo Fiel', el Asistente de Salud Misionero del Distrito Redención.
Tu base son los 8 Remedios Naturales (ADELANTE).
Responde en máximo 100 palabras. Usa lenguaje cristiano y termina con una cita bíblica (RV1960).
"""

# --- 2. CONFIGURACIÓN DE BASE DE DATOS (RENDER) ---
def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception as e:
        return None

def guardar_historial(celular, mensaje, respuesta):
    # Función para guardar en el historial (simplificada)
    pass 

def consultar_gemini(mensaje_usuario):
    try:
        chat = model.start_chat(history=[])
        prompt_final = f"{INSTRUCCION}\n\nEl usuario dice: {mensaje_usuario}"
        response = chat.send_message(prompt_final)
        # Limpieza de seguridad
        return response.text.replace('**', '*').replace('__', '_') 
    except Exception as e:
        print(f"❌ Error Google: {e}")
        return "⚠️ Error de conexión con la IA. Intenta en 1 minuto."

# --- 3. SERVIDOR WEBHOOK ---
@app.route('/webhooks/telegram', methods=['POST'])
@app.route('/chat', methods=['POST'])
def telegram_webhook():
    try:
        # Telegram envía un objeto JSON completo (la 'update')
        update = request.get_json()
        
        # Extraer el chat_id (a quién responder) y el mensaje
        chat_id = update['message']['chat']['id']
        mensaje_in = update['message']['text']
        
        print(f"📩 Recibido de Telegram ({chat_id}): {mensaje_in}")
        
        # Consultar IA
        respuesta = consultar_gemini(mensaje_in)
        
        # Enviar respuesta DE VUELTA a la API de Telegram
        payload = {
            'chat_id': chat_id,
            'text': respuesta,
            'parse_mode': 'Markdown'
        }
        
        requests.post(TELEGRAM_API_URL, data=payload)

        # 200 OK es la respuesta que Telegram espera
        return jsonify(status="success"), 200 

    except Exception as e:
        # Manejo de errores de conexión/parsing
        print(f"⚠️ ERROR FATAL EN WEBHOOK: {e}")
        return jsonify(status="error", error=str(e)), 500

if __name__ == '__main__':
    # Usaremos un puerto diferente para no interferir con otros servicios locales
    app.run(port=8080, debug=True)