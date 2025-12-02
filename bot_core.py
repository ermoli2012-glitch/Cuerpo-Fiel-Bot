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
model = None

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Usamos el modelo más rápido y eficiente para chat
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA MODIFICADA (PRIORIZANDO EL MENÚ DE SERVICIOS)
# =========================================================================

# La IA va a responder esto en CADA interacción (saludo repetitivo y menú).
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu función es proveer información **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico de la **dieta VEGANA INTEGRAL** y los **8 Remedios Naturales**.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. ROL: Médico Especialista, Nutricionista y Naturista.
2. DIETA: Estrictamente VEGANA, INTEGRAL y BASADA EN PLANTAS.
3. TRIAGE: Mantén la regla de Alerta Roja si detectas emergencia extrema.

REGLAS DE RESPUESTA Y FLUJO FINAL:
1. INTRODUCCIÓN: **¡ESTA REGLA ES LA PRIORIDAD MÁXIMA!** En cada respuesta, inicia con un saludo breve y tu rol: "Saludos. Soy el Dr. Caleb, tu guía de salud...", e **INMEDIATAMENTE PRESENTA EL MENÚ DE SERVICIOS** antes de responder la pregunta del usuario.
2. MENÚ DE SERVICIOS: Presenta esta información usando **negritas y emojis**:
    * **Servicios de Salud:** Provee información clínica (diagnóstico y prescripción natural).
    * **Cursos Personalizados:** Ofrece enlaces y detalles sobre cursos personalizados de salud.
    * **Centros y Comunidades:** Proporciona datos de contacto para Centros de Vida Sana e Iglesias Adventistas cercanas.
    * **Radio Adventista (AWR):** Incluye la invitación con el link de la radio: [https://awr.org/es/colombia](https://awr.org/es/colombia).
3. FLUJO: Después de presentar el menú, **Analiza la pregunta y ve directo al diagnóstico y la prescripción natural.**
4. ENFOQUE ESPIRITUAL: La cita bíblica debe ser ALTAMENTE RELEVANTE al tema consultado.
5. FORMATO: Usa negritas, saltos de línea amplios y emojis de forma EXTENSIVA.
6. REFERENCIA MÉDICA: En CADA respuesta, refuerza la necesidad de consultar a tu médico personal.
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# ==========================================
# 3. BASE DE DATOS Y MEMORIA 
# ==========================================
def obtener_conexion():
    """Intenta establecer conexión con la base de datos, priorizando DATABASE_URL."""
    database_url = os.environ.get('DATABASE_URL')
    
    try:
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        else:
            return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
   
    except Exception as e:
        print(f"❌ Error al conectar a la DB: {e}")
        return None

def guardar_historial(celular, mensaje, respuesta):
    """Guarda la interacción en la base de datos."""
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)", (celular, mensaje, respuesta))
            conn.commit()
            cursor.close()
     
        except Exception as e:
            print(f"❌ Error al guardar en DB: {e}")
            pass
        finally:
            if conn:
                conn.close()


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO DIRECTO ORIGINAL) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Consulta a Gemini sin usar memoria de sesión, usando la Instrucción Maestra completa.
    """
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return """
🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴

El síntoma que describes es una **emergencia médica grave**.
Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
Tu vida es la prioridad.

🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**
"""

    # === 2. LÓGICA NORMAL (IA CON JUICIO) ===
    try:
        # Aquí se envía la Instrucción Maestra completa con el menú de servicios
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        # Usamos generate_content
        response = model.generate_content(prompt_full)
     
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return """
⚠️ Lo siento, Dr. Caleb está en una consulta crítica.
Intenta de nuevo en un momento.
"""


# ==========================================
# 5. RUTAS WEB Y DE WHATSAPP (Sin cambios)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    celular_raw = request.values.get('From', 'Web User')
    celular = celular_raw.replace('whatsapp:', '')
    if celular.startswith('+'):
        celular = celular[1:]
        
    mensaje_in = request.values.get('Body', '') or (request.get_json(silent=True) or {}).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    respuesta = consultar_gemini(celular, mensaje_in)
    
    guardar_historial(celular, mensaje_in, respuesta)

    if 'whatsapp' in celular_raw.lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO DIRECTO ORIGINAL) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)
