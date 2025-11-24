import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# OJO: DEBES PEGAR TU CLAVE AQUI, AUNQUE EN LA NUBE USARÁ VARIABLES DE ENTORNO.
API_KEY = "AIzaSyAeKvHeSo9RRnVo-LSmSwYyb3n5lsKWp8o" 

try:
    genai.configure(api_key=API_KEY)
    # Usamos el modelo más estable que tu escáner encontró (necesario para que funcione)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"⚠️ Error configurando Gemini. Verifica la clave. {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Bot)
INSTRUCCION_SISTEMA = """
Eres 'Cuerpo Fiel', asistente de salud médico-misionero de la Iglesia Adventista (Distrito Redención).
Tu base son los 8 Remedios Naturales (ADELANTE).

REGLAS OBLIGATORIAS:
1. SÉ MUY BREVE: Tus respuestas NO deben pasar de 100 palabras.
2. Si saludas, preséntate y menciona los 8 Remedios Naturales.
3. Si detectas un síntoma, da un consejo de salud y una promesa bíblica.
4. ADVERTENCIA LEGAL: Aclara que no eres un médico humano.
"""

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS (CLOUD Y LOCAL)
# ==========================================
# Render usará DATABASE_URL; Local usará DB_CONFIG
def obtener_conexion():
    try:
        # 1. Conexión a la NUBE (Render)
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # En la nube, usamos el URL completo que provee Render
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

# --- 3. CEREBRO DE LA APLICACIÓN ---
def consultar_gemini(mensaje_usuario):
    # La parte de saludos y aviso legal
    saludos = ["HOLA", "BUENOS", "INICIO", "AYUDA", "MENU", "DIAS", "TARDES"]
    if any(s in mensaje_usuario.upper() for s in saludos):
        return (
            "👋 *¡Bienvenido a Cuerpo Fiel 4.0!*\n"
            "Soy tu asistente del Ministerio de Salud, basado en la filosofía de la *Iglesia Adventista del Séptimo Día*.\n\n"
            "🌿 *MI PROPÓSITO:*\n"
            "Toda recomendación está fundamentada en la Biblia y los 8 Remedios Naturales (ADELANTE).\n\n"
            "💡 *EJEMPLOS:* 'Glucosa 150', 'Presion 140', 'Tengo ansiedad'.\n\n"
            "⚠️ *AVISO IMPORTANTE:*\n"
            "Soy una inteligencia artificial. *NO suplanto el juicio clínico de un médico.*"
        )

    try:
        # Limpieza de seguridad y consulta a la IA
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{INSTRUCCION_SISTEMA}\n\nEl usuario dice: {mensaje_usuario}")
        texto = response.text.replace('**', '*').replace('__', '_') # Limpieza de markdown
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, mi cerebro central está saturado. Intenta de nuevo en 1 minuto."

# ==========================================
# 4. SERVIDOR WEB (RUTAS)
# ==========================================
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos limpios
    celular = request.values.get('From', 'Test').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '')
    
    # 2. Consultar IA
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar y registrar
    guardar_historial(celular, mensaje_in, respuesta)
    print(f"📩 Recibido de {celular}. Enviando respuesta...")

    # 4. Responder a Twilio (con formato XML correcto)
    resp = MessagingResponse()
    resp.message(respuesta)
    
    # Devolver respuesta con el header correcto para Twilio
    return str(resp), 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 (CLOUD READY) - ACTIVO")
    # Este 'run' solo funciona localmente. Gunicorn lo usará en la nube.
    app.run(port=5000, debug=True)