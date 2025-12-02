import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
import json 
import re 
from datetime import datetime

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

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD FINAL: DIRECTA Y ESPECIALIZADA)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición, Naturista, y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu función es ser un consultor profesional, rápido, cálido y humano, **usando siempre el pronombre "TÚ"**.

MISIÓN: Provee información de salud exacta, veraz, rápida e intuitiva, bajo el estándar terapéutico de la dieta VEGANA INTEGRAL y los 8 Remedios Naturales.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. DIETA: Las recomendaciones nutricionales son estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS.
2. REMEDIOS: Aplica los 8 Remedios Naturales de forma precisa.

REGLAS DE RESPUESTA Y FLUJO FINAL:
1. **PRESENTACIÓN ÚNICA (Flujo Conversacional):** Si es el primer mensaje del paciente, debes usar una presentación formal. En las respuestas siguientes, OMITE por completo el título y el saludo largo, y ve directo a la consulta, actuando como un médico en un diálogo continuo.
2. **ABORDAJE DIRECTO:** Siempre aborda la inquietud del usuario de forma inmediata.
3. FORMATO VISUAL: Utiliza formato Markdown (negritas, listas, saltos de línea amplios y emojis) extensivamente.
4. REFERENCIA MÉDICA: En CADA respuesta de salud, refuerza la necesidad de consultar a tu médico personal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

# ==========================================
# 2. BASE DE DATOS Y GESTIÓN DE ESTADO (Funciones)
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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON FLUJO DIRECTO) ---
def consultar_gemini(mensaje_usuario, is_first_contact):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**. Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local). Tu vida es la prioridad."
        )

    # === 2. LÓGICA CONVERSACIONAL Y JUICIO DIRECTO ===
    try:
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"

        if is_first_contact:
            # Si es el primer mensaje, agregamos la instrucción de presentación al prompt
            presentacion_protocolo = "INSTRUCCIÓN EXTRA: Aplica la REGLA 1 (PRESENTACIÓN ÚNICA) y usa este formato: 'Saludos. Soy el Dr. Caleb, tu guía de salud. ¿Cuál es tu nombre y en qué te puedo ayudar?'"
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{presentacion_protocolo}\n\nPregunta del paciente: {mensaje_usuario}"
        else:
             # Si no es el primer mensaje, la IA va directo al diagnóstico sin repetir el encabezado.
            prompt_full = f"Continúa la conversación como un médico profesional. Pregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Caleb está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Añadiendo la restricción)
# ==========================================
PROMOCION_ACCESO_LIMITADO = (
    "🚨 *ATENCIÓN - LÍMITE DE CONSULTAS ALCANZADO* 🚨\n\n"
    "Estimado(a) usuario(a), **Dr. Caleb** te ha ofrecido dos consultas gratuitas como cortesía del Ministerio de Salud. Si deseas tener acceso *ilimitado* y completo a las guías de salud:\n\n"
    "👉 **Comunícate con el Director de Salud y Temperancia de la Iglesia Adventista Redención Barranquilla para obtener tu código de acceso.**"
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    # 1. Chequear si es el primer contacto para la introducción
    is_first_contact = contar_consultas(celular) == 0

    # 2. CHEQUEO DE LÍMITE DE CONSULTAS (Si se agota, bloquea)
    if contar_consultas(celular) >= TEST_LIMIT and not is_first_contact:
        return jsonify({"respuesta": PROMOCION_ACCESO_LIMITADO})
    
    # 3. PROCESAMIENTO
    respuesta = consultar_gemini(mensaje_in, is_first_contact)
    
    # 4. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 5. Responder
    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO CONVERSACIONAL FLUIDO) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)