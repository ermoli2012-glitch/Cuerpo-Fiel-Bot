import os
import requests
import datetime
import google.generativeai as genai
from flask import Flask, request, jsonify
from pymongo import MongoClient 
import telebot # Librería de Telegram Bot API

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE SEGURIDAD Y ENTORNO
# ==========================================
# Estas variables se leen del panel de Render (Medio ambiente)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') 
MONGO_URI = os.environ.get('MONGO_URI')
API_KEY = os.environ.get('GEMINI_API_KEY') 
RENDER_URL = "https://cuerpo-fiel-bot.onrender.com" # Reemplazar con tu URL base de Render

# Inicialización global de los clientes
try:
    # 1. Inicialización de Gemini
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    # 2. Inicialización de Telegram
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
except Exception as e:
    print(f"❌ ERROR CRÍTICO DE INICIO: {e}")
    # Si la aplicación falla aquí, Render la reiniciará

# ==========================================
# 2. BASE DE DATOS (MongoDB)
# ==========================================
def obtener_coleccion():
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_database('cuerpo_fiel_db') # Nombre de tu base de datos
        return db.historial_chats
    except Exception as e:
        return None

def guardar_historial(chat_id, mensaje, respuesta):
    coleccion = obtener_coleccion()
    if coleccion:
        try:
            coleccion.insert_one({
                "usuario_id": chat_id,
                "mensaje": mensaje,
                "respuesta_ai": respuesta,
                "fecha": datetime.datetime.now()
            })
            print(f"💾 Historial guardado para chat {chat_id}")
        except Exception as e:
            print(f"⚠️ Error al guardar en Mongo: {e}")

# ==========================================
# 3. LÓGICA (GEMINI)
# ==========================================
INSTRUCCION_SISTEMA = """
Eres 'Cuerpo Fiel', el asistente de salud adventista.
Responde de forma breve (máximo 100 palabras) y espiritual, usando los 8 Remedios Naturales. Termina con un versículo bíblico.
"""

def consultar_gemini(mensaje_usuario):
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{INSTRUCCION_SISTEMA}\n\nUsuario: {mensaje_usuario}")
        return response.text
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GEMINI: {e}")
        return "⚠️ Lo siento, mi cerebro IA está fallando. Intenta de nuevo en un momento."

# ==========================================
# 4. RUTAS DE FLASK (El Escucha y el Activador)
# ==========================================

# A. RUTA PARA ESTABLECER EL WEBHOOK (El FIX que faltaba)
@app.route('/setwebhook', methods=['GET'])
def set_webhook_route():
    if not TELEGRAM_TOKEN: return "ERROR: TELEGRAM_TOKEN no configurado en Render ENV", 500
    
    # La URL a la que Telegram enviará los mensajes
    webhook_url = f"{RENDER_URL}/{TELEGRAM_TOKEN}"
    
    # Le decimos a Telegram dónde está nuestro bot
    s = bot.set_webhook(url=webhook_url)

    if s:
        return f"✅ Webhook de Telegram establecido correctamente en: {webhook_url}", 200
    else:
        return "❌ Fallo al establecer el webhook de Telegram.", 500


# B. RUTA PARA RECIBIR MENSAJES (El endpoint activo: /TELEGRAM_TOKEN)
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook_receiver():
    if not TELEGRAM_TOKEN: return "ERROR: TOKEN NOT SET", 500

    try:
        # Procesar el JSON que envía Telegram
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        
        if update.message:
            message = update.message
            chat_id = message.chat.id
            mensaje_usuario = message.text

            # 1. Consultar IA y obtener respuesta
            respuesta_texto = consultar_gemini(mensaje_usuario)
            
            # 2. Guardar en MongoDB
            guardar_historial(chat_id, mensaje_usuario, respuesta_texto)

            # 3. Enviar Respuesta de vuelta a Telegram
            bot.send_message(chat_id, respuesta_texto)
        
        return "OK", 200
    except Exception as e:
        print(f"❌ ERROR CRÍTICO AL PROCESAR MENSAJE: {e}")
        return "ERROR INTERNO", 500


if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 (TELEGRAM/MONGO) - Activo")
    # Nota: Render usa gunicorn, no app.run
    pass