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
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    # Si la clave no está en el entorno (solo para pruebas locales), la ignoramos
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Usamos el modelo exacto que tu escáner encontró y que es estable
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

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
        # Este error es esperado si el bot corre local y Docker está apagado
        print(f"❌ Error conectando a BD: {e}")
        return None

def guardar_historial(celular, mensaje, respuesta):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)",
                (celular, mensaje, respuesta)
            )
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

# RUTA 1: Muestra la interfaz de chat al entrar al link de Render
@app.route('/')
def home():
    return render_template('index.html')

# RUTA 2: Recibe los mensajes y devuelve la respuesta
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

    # 4. Responder
    # Si viene de Twilio (por haber configurado el webhook)
    if 'whatsapp' in request.values.get('From', '').lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        # Devolvemos XML con el header correcto
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        # Si viene de la Web App (JSON)
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 (CLOUD READY - FINAL) - ACTIVO")
    app.run(port=5000, debug=True)