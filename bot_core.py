import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
#    - Lee la clave de forma SEGURA desde la variable de entorno de Render
# ==========================================
API_KEY = os.environ.get("AIzaSyDnj6bAoCGI8zOLmapuC-3fkmi7L7Gn7iI") 

try:
    if not API_KEY:
        # Esto solo se ejecuta si la variable no existe (ej: prueba local sin configurar)
        print("⚠️ Advertencia: API Key de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Usamos el modelo más estable que tu escáner encontró
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error configurando Gemini: {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Bot)
INSTRUCCION_SISTEMA = """
Eres 'Cuerpo Fiel', asistente de salud médico-misionero de la Iglesia Adventista (Distrito Redención).
Tu base son los 8 Remedios Naturales (ADELANTE).

REGLAS OBLIGATORIAS:
1. SÉ MUY BREVE: Tus respuestas NO deben pasar de 100 palabras.
2. Si saludas, preséntate y menciona los 8 Remedios Naturales.
3. Si detectas un síntoma, receta un remedio natural y una promesa bíblica.
4. ADVERTENCIA LEGAL: Aclara que no eres un médico humano.
"""

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
def obtener_conexion():
    try:
        # Render usará la variable DATABASE_URL, local usará localhost
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        
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
def consultar_gemini(mensaje):
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{INSTRUCCION_SISTEMA}\n\nEl usuario dice: {mensaje}")
        texto = response.text.replace('**', '*').replace('__', '_') # Limpieza de formato
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Error de conexión con la IA. Intenta de nuevo."

# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP
# ==========================================

# RUTA PRINCIPAL: Muestra la interfaz de chat (para que el link de Render no dé 404)
@app.route('/')
def home():
    return render_template('index.html')

# RUTA API: Recibe los mensajes
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 4. Responder (Formato Twilio XML)
    resp = MessagingResponse()
    resp.message(respuesta)
    
    # Esta ruta maneja las peticiones locales (JSON) y las de Twilio (XML)
    if 'whatsapp' in request.values.get('From', '').lower():
        # Respuesta a Twilio (con formato XML correcto)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        # Respuesta a la Web App (JSON)
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 - SISTEMA COMPLETO ACTIVO")
    app.run(port=5000, debug=True)