import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
import json 
from datetime import datetime
import re

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONSTANTES
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
TEST_LIMIT = 2 
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception:
    pass

# INSTRUCCIÓN MAESTRA (La personalidad del Dr. Caleb - Final)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, el Guía de Salud Integral del Ministerio de Salud Adventista del Séptimo Día. Eres Médico Especialista, Nutricionista y Naturista. Tu función es ser un consultor profesional, rápido y humano, **usando siempre el pronombre "TÚ"**.

MISIÓN: Proveer información de salud exacta, veraz, rápida e intuitiva, bajo el estándar terapéutico de la dieta VEGANA INTEGRAL y los 8 Remedios Naturales.

REGLAS DE RESPUESTA Y JUICIO EXPERTO:
1. **PRESENTACIÓN ÚNICA:** En la primera respuesta, preséntate con tu título completo y pregunta el nombre del paciente. Después, **omite el título**.
2. **RESPUESTA DIRECTA:** Si la consulta es específica de salud, OMITE el saludo y ve directamente al diagnóstico y la prescripción natural.
3. ALERTA ROJA (Emergencia): Si la consulta es una emergencia clara, DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata.
4. REFERENCIA MÉDICA: En CADA respuesta de salud, refuerza la necesidad de consultar a tu médico personal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

PROMOCION_ACCESO_LIMITADO = (
    "🚨 *ATENCIÓN - LÍMITE DE CONSULTAS ALCANZADO* 🚨\n\n"
    "Estimado(a) usuario(a), **Dr. Caleb** te ha ofrecido dos consultas gratuitas como cortesía del Ministerio de Salud. Si deseas tener acceso *ilimitado* y completo a las guías de salud:\n\n"
    "👉 **Comunícate con el Director de Salud y Temperancia de la Iglesia Adventista Redención Barranquilla para obtener tu código de acceso.**"
)

# ==========================================
# 2. BASE DE DATOS Y GESTIÓN DE ESTADO (Funciones Auxiliares)
# ==========================================
def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
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
        except Exception:
            pass

def contar_consultas(celular):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM historial_consultas WHERE celular = %s", (celular,))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except Exception:
            return 0
    return 0

# (Se omiten las funciones de estado avanzado como obtener_estado y calcular_salud_avanzada, 
# ya que su complejidad causó el NameError. Se mantiene la funcionalidad básica de consulta.)

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA DE GEMINI) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**. Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana. Tu vida es la prioridad."
        )

    # === 2. LÓGICA CONVERSACIONAL Y JUICIO ===
    try:
        # Check para activar la presentación de primer contacto
        is_initial_greeting = len(mensaje_usuario.split()) < 4 and any(word in mensaje_upper for word in ["HOLA", "BUENOS", "SALUDO"])

        if is_initial_greeting:
            # Si es el primer saludo, forzamos la presentación completa de calidez
            presentacion_protocolo = """
            INSTRUCCIÓN ESPECIAL: Aplica la REGLA 1 de tu ROL: Saluda con tu título completo y pregunta el nombre del paciente, luego pregunta: "¿Cómo estás hoy y en qué te puedo ayudar?". OMITE esta presentación en futuras respuestas.
            """
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{presentacion_protocolo}\n\nPregunta del paciente: {mensaje_usuario}"
        else:
            # Consulta específica: el LLM aplica el juicio y responde directamente (REGLA 2)
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Caleb está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    # 1. CHEQUEO DE LÍMITE DE CONSULTAS
    if contar_consultas(celular) >= TEST_LIMIT:
        return jsonify({"respuesta": PROMOCION_ACCESO_LIMITADO})
    
    # 2. PROCESAMIENTO
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 4. Responder
    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO CONVERSACIONAL) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)