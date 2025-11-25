import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, Response
from twilio.twiml.messaging_response import MessagingResponse
import re 

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# Lee la clave de la variable de entorno de Render (o un placeholder si no existe)
API_KEY = os.environ.get("GEMINI_API_KEY", "PEGAR_TU_CLAVE_AQUI") 

try:
    genai.configure(api_key=API_KEY)
    # Usamos el modelo más estable que tu escáner encontró
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    # Este error solo saldrá si la llave no es válida o no está configurada en Render
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
# 2. CONFIGURACIÓN DE BASE DE DATOS (CLOUD Y LOCAL)
# ==========================================
def obtener_conexion():
    try:
        # 1. Conexión a la NUBE (Render)
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        
        # 2. Conexión LOCAL (Laptop)
        return psycopg2.connect(
            user="root", password="root", 
            host="localhost", port="5432", 
            database="cuerpo_fiel_db"
        )
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
            print(f"💾 Historial guardado.")
        except Exception:
            pass

# ==========================================
# 3. LÓGICA DE LA APLICACIÓN
# ==========================================
def consultar_gemini(mensaje_usuario):
    # Limpieza de input y manejo de saludos
    mensaje_norm = mensaje_usuario.upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
    
    # Manejo de saludo simplificado
    saludos = ["HOLA", "BUENOS", "INICIO", "AYUDA", "MENU", "DIAS", "TARDES"]
    if any(s in mensaje_norm for s in saludos):
        return (
            "👋 *¡Bienvenido a Cuerpo Fiel 4.0!* Soy tu asistente de salud adventista.\n\n"
            "🌿 *MI BASE:* 8 Remedios Naturales (ADELANTE).\n"
            "💡 *EJEMPLOS:* 'Glucosa 150', 'Presion 140', 'Tengo ansiedad'.\n\n"
            "⚠️ *AVISO LEGAL:* No soy un médico. Mis consejos son educativos."
        )

    try:
        chat = model.start_chat(history=[])
        prompt_final = f"{INSTRUCCION_SISTEMA}\n\nEl usuario dice: {mensaje_usuario}"
        
        response = chat.send_message(prompt_final)
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, mi cerebro central está saturado. Intenta de nuevo en 1 minuto."

# ==========================================
# 4. SERVIDOR WEB (RUTAS)
# ==========================================
@app.route('/webhooks/telegram', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos limpios
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '')
    
    # Soporte para pruebas locales (JSON)
    datos_json = request.get_json(silent=True) or {}
    mensaje_final = mensaje_in if mensaje_in else datos_json.get('mensaje', '')
    
    print(f"📩 Recibido: {mensaje_final}")

    # 2. Consultar y Guardar
    respuesta = consultar_gemini(mensaje_final)
    guardar_historial(celular, mensaje_final, respuesta)

    # 3. Responder a Twilio (OBLIGATORIO XML)
    resp = MessagingResponse()
    resp.message(respuesta)
    
    # Devolver respuesta con el header correcto
    return Response(str(resp), mimetype='application/xml')

if __name__ == '__main__':
    # Render usa la variable de entorno 'PORT'
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 CUERPO FIEL 4.0 - FINAL PORT: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)