import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
from google.generativeai.types import ChatSession # Para tipado claro

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
# 2. INSTRUCCIÓN MAESTRA AJUSTADA Y MEMORIA GLOBAL
# =========================================================================

# La instrucción maestra ELIMINA la REGLA de saludo, pues se maneja en el historial.
INSTRUCCION_SISTEMA_SIN_SALUDO = """
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu función es proveer información **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico de la **dieta VEGANA INTEGRAL** y los **8 Remedios Naturales**.
BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. ROL: Médico Especialista, Nutricionista y Naturista.
2. DIETA: Estrictamente VEGANA, INTEGRAL y BASADA EN PLANTAS.
3. TRIAGE: Mantén la regla de Alerta Roja si detectas emergencia extrema.
REGLAS DE RESPUESTA Y FLUJO FINAL:
1. FLUJO: **Analiza la pregunta y ve directo al diagnóstico y la prescripción natural.**
2. ENFOQUE ESPIRITUAL: La cita bíblica debe ser ALTAMENTE RELEVANTE al tema consultado (ej: Estrés -> Reposo; Dieta -> Cuerpo Templo).
3. FORMATO: Usa negritas, saltos de línea amplios y emojis de forma EXTENSIVA.
4. REFERENCIA MÉDICA: En CADA respuesta, refuerza la necesidad de consultar a tu médico personal.
"""

# Diccionario para almacenar las sesiones de chat de Gemini por número de celular (memoria).
chat_sessions = {} # type: dict[str, ChatSession] 

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]


# ==========================================
# 3. BASE DE DATOS Y MEMORIA
# ==========================================
def obtener_conexion():
    """Intenta establecer conexión con la base de datos."""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Conexión para entorno de producción (Render/otros)
            return psycopg2.connect(database_url, sslmode='require')
        # Conexión para entorno local de desarrollo
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


# --- 4. CEREBRO DE LA APLICACIÓN (LÓGICA CON FLUJO DIRECTO Y MEMORIA) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la sesión de chat con memoria y consulta a Gemini.
    Usa el celular como clave para mantener la conversación.
    """
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        # Usando comillas triples (""" """) para evitar errores de sintaxis en cadenas multilínea.
        return """
🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴

El síntoma que describes es una **emergencia médica grave**.
Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
Tu vida es la prioridad.

🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**
"""

    # === 2. LÓGICA NORMAL (IA CON JUICIO Y MEMORIA) ===
    try:
        if celular not in chat_sessions:
            print(f"🆕 Iniciando nueva sesión de chat para {celular}")
            
            # Se usa un historial inicial para forzar el saludo solo en el primer mensaje.
            historial_inicial = [
                {"role": "user", "parts": [
                    "A partir de ahora, usa estas instrucciones en toda nuestra conversación."
                ]},
                {"role": "model", "parts": [
                    "Saludos. Soy el Dr. Caleb, tu guía de salud. ¿En qué puedo ayudarte hoy?"
                ]}
            ]
            
            # El "system_instruction" mantiene el rol y reglas para el resto del chat.
            chat = model.start_chat(
                history=historial_inicial,
                system_instruction=INSTRUCCION_SISTEMA_SIN_SALUDO
            )
            chat_sessions[celular] = chat
        else:
            # Recuperamos la sesión existente.
            chat = chat_sessions[celular]
            print(f"🧠 Sesión de chat recuperada para {celular}")

        # Enviamos el mensaje del usuario a la sesión de chat activa.
        response = chat.send_message(mensaje_usuario)
     
        # Limpieza de formato y retorno (adecuado para Twilio/WhatsApp)
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
        
    except Exception as e:
        # En caso de error crítico de la API, se borra la sesión para intentar de nuevo.
        if celular in chat_sessions:
            del chat_sessions[celular]
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        # Usando comillas triples para el mensaje de error también.
        return """
⚠️ Lo siento, Dr. Caleb está en una consulta crítica.
Intenta de nuevo en un momento.
"""


# ==========================================
# 5. RUTAS WEB Y DE WHATSAPP
# ==========================================
@app.route('/')
def home():
    """Ruta de inicio para verificar que el servicio está activo."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Maneja los mensajes entrantes de WhatsApp o de la web."""
    # Obtener y limpiar el identificador del usuario (celular)
    celular_raw = request.values.get('From', 'Web User')
    celular = celular_raw.replace('whatsapp:', '')
    if celular.startswith('+'):
        celular = celular[1:]
        
    # Obtener el mensaje entrante
    mensaje_in = request.values.get('Body', '') or (request.get_json(silent=True) or {}).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # Consultar a Gemini y obtener la respuesta
    respuesta = consultar_gemini(celular, mensaje_in)
    
    # Guardar el historial de la interacción
    guardar_historial(celular, mensaje_in, respuesta)

    # Devolver la respuesta según la fuente (Twilio/XML o Web/JSON)
    if 'whatsapp' in celular_raw.lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO DIRECTO Y CON MEMORIA) - ACTIVO")
    # Asegúrate de que el archivo 'index.html' exista si usas la ruta '/'
    app.run(port=os.environ.get('PORT', 5000), debug=True)