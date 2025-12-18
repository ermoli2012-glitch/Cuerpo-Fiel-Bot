import os
import base64
import psycopg2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
# IMPORTANTE: CORS permite que tu frontend en Netlify se comunique con este servidor en Render
CORS(app) 

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
    
    genai.configure(api_key=API_KEY)
    # Usamos gemini-1.5-flash: es el modelo que soporta visión (imágenes) y es muy rápido
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# --- DATOS DE CONTACTO Y ENLACES ---
WHATSAPP_CONTACTO_PSICOLOGIA = "proximamente"
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA Y MENÚS
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis, Médico Especialista en Medicina Interna y Nutricionista Clínico. 
Visible al usuario como: Tu Guía Saludable del Ministerio de Salud Adventista.
ESTILO: 100% Humano, empático y cálido.
ESTÁNDAR: Estilo de vida basado en plantas y los 8 Remedios Naturales.
"""

EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "AMBULANCIA", "911", "ASFIXIA"]

MENU_SERVICIOS = """
⭐ *¡HOLA! SOY GENESIS* ⭐
🤝 Selecciona una opción:
0️⃣ EVALUACIÓN | 1️⃣ CONSULTA CLÍNICA | 2️⃣ APOYO PSICOLÓGICO
3️⃣ COMUNIDAD DE FE | 4️⃣ RADIO | 5️⃣ EJERCICIO
6️⃣ HTA | 7️⃣ DIABETES | 8️⃣ CORAZÓN
"""

# ==========================================
# 3. BASE DE DATOS
# ==========================================
def obtener_conexion():
    database_url = os.environ.get('DATABASE_URL')
    try:
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception as e:
        print(f"❌ Error DB: {e}")
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
        except Exception as e:
            print(f"❌ Error al guardar: {e}")

# ==========================================
# 4. LÓGICA DE INTELIGENCIA
# ==========================================
def consultar_gemini(celular, mensaje_usuario):
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    if any(keyword in mensaje_limpio for keyword in EMERGENCY_KEYWORDS):
        return "🔴 *ALERTA ROJA: LLAME A EMERGENCIAS (911)*. Su vida es prioridad."

    if mensaje_limpio in ["HOLA", "MENU", "INICIO", "SALIR"]:
        return MENU_SERVICIOS 

    try:
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        response = model.generate_content(prompt_full)
        return response.text.replace('**', '*').replace('__', '_')
    except Exception as e:
        return "⚠️ Genesis está en una consulta crítica. Intenta en un momento."

# ==========================================
# 5. RUTAS DEL SERVIDOR
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

# CORRECCIÓN: Nombre de función único para evitar el AssertionError en Render
@app.route('/analizar_comida', methods=['POST'])
def endpoint_analizar_comida_visual():
    try:
        data = request.get_json()
        image_data = data.get('image')
        if not image_data:
            return jsonify({"error": "No image"}), 400

        # Limpiar el encabezado base64 si el frontend lo envía
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        
        image_bytes = base64.b64decode(image_data)

        prompt = "Analiza esta comida como Médico y Nutricionista de Génesis: identifica alimentos, salud (1-10) y consejo médico breve basado en los 8 remedios naturales."
        
        # Llamada multimodal (texto + imagen)
        response = model.generate_content([
            prompt, 
            {'mime_type': 'image/jpeg', 'data': image_bytes}
        ])
        
        return jsonify({"respuesta": response.text})
    except Exception as e:
        print(f"Error Cámara: {e}")
        return jsonify({"respuesta": "Génesis no pudo analizar la imagen en este momento."}), 500

@app.route('/chat', methods=['POST'])
def chat():
    celular_raw = request.values.get('From', 'Web User')
    celular = celular_raw.replace('whatsapp:', '').replace('+', '')
        
    mensaje_in = request.values.get('Body', '') or (request.get_json(silent=True) or {}).get('mensaje', '')
    
    respuesta = consultar_gemini(celular, mensaje_in)
    guardar_historial(celular, mensaje_in, respuesta)

    if 'whatsapp' in celular_raw.lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 GENESIS ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)
