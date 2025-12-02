import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
from google.generativeai.types import ChatSession # Importar el tipo para mayor claridad

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
# 💡 CAMBIO CLAVE 1: INSTRUCCIÓN MAESTRA AJUSTADA Y MEMORIA GLOBAL
# =========================================================================

# Ajustamos la instrucción. ELIMINAMOS la REGLA 1 (saludo) para que no se repita. 
# Dejaremos que la IA inicie el saludo en el primer mensaje.
INSTRUCCION_SISTEMA_SIN_SALUDO = """
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu función es proveer información **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico de la **dieta VEGANA INTEGRAL** y los **8 Remedios Naturales**.
BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. ROL: Médico Especialista, Nutricionista y Naturista.
2. DIETA: Estrictamente VEGANA, INTEGRAL y BASADA EN PLANTAS.
3. TRIAGE: Mantén la regla de Alerta Roja si detectas emergencia extrema.
REGLAS DE RESPUESTA Y FLUJO FINAL:
2. FLUJO: **Analiza la pregunta y ve directo al diagnóstico y la prescripción natural.**
3. ENFOQUE ESPIRITUAL: La cita bíblica debe ser ALTAMENTE RELEVANTE al tema consultado (ej: Estrés -> Reposo; Dieta -> Cuerpo Templo).
4. FORMATO: Usa negritas, saltos de línea amplios y emojis de forma EXTENSIVA.
5. REFERENCIA MÉDICA: En CADA respuesta, refuerza la necesidad de consultar a tu médico personal.
"""

# Diccionario para almacenar las sesiones de chat (memoria)
# La clave será el número de celular.
chat_sessions = {} # type: dict[str, ChatSession] 

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]


# ==========================================
# 2. BASE DE DATOS Y MEMORIA (Sin cambios)
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
     
        except Exception as e:
            print(f"❌ Error al guardar en DB: {e}")
            pass
        finally:
            # Aseguramos el cierre de la conexión incluso si falla la escritura
            conn.close()


# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON FLUJO DIRECTO) ---
# 💡 CAMBIO CLAVE 2: La función ahora recibe el celular para gestionar la memoria.
def consultar_gemini(celular, mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**.
            Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
            Tu vida es la prioridad.\n\n"
            "🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él;
            y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**"
        )

    # === 2. LÓGICA NORMAL (IA CON JUICIO) ===
    try:
        # 💡 CAMBIO CLAVE 3: Gestión de la Sesión de Chat (Memoria)
        if celular not in chat_sessions:
            # Si es un usuario nuevo, iniciamos una sesión con la instrucción maestra.
            # Nota: La primera respuesta de la IA incluirá ahora el saludo.
            print(f"🆕 Iniciando nueva sesión de chat para {celular}")
            
            # Para la primera interacción, ANTES de la INSTRUCCION_SISTEMA, 
            # añadiremos una instrucción ÚNICA para el saludo
            historial_inicial = [
                {"role": "user", "parts": [
                    "A partir de ahora, usa estas instrucciones en toda nuestra conversación."
                ]},
                {"role": "model", "parts": [
                    "Saludos. Soy el Dr. Caleb, tu guía de salud. ¿En qué puedo ayudarte hoy?"
                ]}
            ]
            
            # El "system_instruction" se asegura de que el modelo siga el rol
            chat = model.start_chat(
                history=historial_inicial,
                system_instruction=INSTRUCCION_SISTEMA_SIN_SALUDO
            )
            chat_sessions[celular] = chat
        else:
            # Si el usuario ya tiene sesión, la recuperamos para mantener el contexto.
            chat = chat_sessions[celular]
            print(f"🧠 Sesión de chat recuperada para {celular}")

        # Enviamos el mensaje del usuario a la sesión de chat activa.
        response = chat.send_message(mensaje_usuario)
     
        # Limpieza de formato y retorno
        # Usar la función de reemplazo de cadenas es una buena práctica para Twilio
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        # Puedes añadir una lógica para borrar la sesión si falla
        if celular in chat_sessions:
            del chat_sessions[celular]
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Caleb está en una consulta crítica.
            Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Ajustes menores)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # 💡 CAMBIO CLAVE 4: Obtener el celular ANTES de la consulta.
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    # Aseguramos que el celular sea un identificador limpio, por ejemplo, sin "+"
    if celular.startswith('+'):
        celular = celular[1:]
        
    mensaje_in = request.values.get('Body', '') or (request.get_json(silent=True) or {}).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 💡 CAMBIO CLAVE 5: Pasar el celular a la función de consulta.
    respuesta = consultar_gemini(celular, mensaje_in)
    
    guardar_historial(celular, mensaje_in, respuesta)

    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO DIRECTO Y CON MEMORIA) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)