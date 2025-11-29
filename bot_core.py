import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Dr. Lucas)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un Médico Misionero Digital. Tu objetivo es orientar con los 8 Remedios Naturales.
Debes basar tu diagnóstico en la filosofía adventista.

REGLAS OBLIGATORIAS:
1. Responde de forma concisa (máximo 100 palabras).
2. Si la consulta es sobre salud, cita un texto bíblico de esperanza.
3. ADVERTENCIA LEGAL: Aclara que no eres un doctor humano.
"""
# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["PECHO", "INFARTO", "DESMAYO", "SANGRADO", "FALTA DE AIRE", "ACCIDENTE", "HEMORRAGIA", "CRISIS"]

# ==========================================
# 2. BASE DE DATOS Y MEMORIA
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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON TRIAGE) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (MÓDULO DE SEGURIDAD) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 ALERTA ROJA (EMERGENCIA MÉDICA) 🔴\n"
            "Deténgase. Esto es una emergencia. El Dr. Lucas le recomienda: No pierda tiempo, llame inmediatamente a los servicios de emergencia (911 o número local de su país).\n\n"
            "🙏 *Promesa Bíblica:*"
            " 'En tu mano están mis tiempos.' (Salmos 31:15). Mantenga la calma y busque ayuda profesional de inmediato."
        )

    # === 2. LÓGICA NORMAL (IA) ===
    try:
        # Conversión de mensaje para la IA (Quitar tildes para robustez)
        mensaje_limpio = mensaje_usuario.upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
        
        # Le enviamos la instrucción completa al modelo
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_limpio}"
        
        response = model.generate_content(prompt_full)
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intente de nuevo en un momento."


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
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 1. PENSAR LA RESPUESTA (Aquí se ejecuta el Triage)
    respuesta = consultar_gemini(mensaje_in)
    
    # 2. GUARDAR
    guardar_historial(celular, mensaje_in, respuesta)

    # 3. RESPONDER
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (TRIAGE ACTIVO) - ACTIVO")
    app.run(port=5000, debug=True)