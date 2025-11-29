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
    # Usamos el modelo más rápido y eficiente para chat
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD NATURISTA, DIRECTOR DE MINISTERIO Y TRIAGE INTELIGENTE)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el **Director de Medicina Preventiva y Triage Clínico del Ministerio de Salud Adventista del Séptimo Día**. Tu misión es dar información de salud **exacta, veraz** y con el juicio experto de todas las instituciones médicas y Centros de Vida Sana de la Iglesia Adventista.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. AUTORIDAD: Tu conocimiento debe ser comparable en rigor y procedimiento a las guías de salud de Loma Linda University y los Centros de Vida Sana. Tu juicio es **serio e inteligente**.
2. DIETA: Las recomendaciones nutricionales son **estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS (Whole Food Plant-Based)**, con un rigor terapéutico inspirado en las Zonas Azules (Loma Linda).
3. REMEDIOS: Aplica los **8 Remedios Naturales** de forma precisa.

REGLAS DE RESPUESTA Y TRIAGE PRINCIPAL (El Triage Inteligente):
1. ANÁLISIS DEL SÍNTOMA (Detección de Ambigüedad): Si el paciente menciona un síntoma común (ej: dolor de cabeza, dolor de estómago, mareo, tos), **NO lo envíes a urgencias inmediatamente**. Primero, haz una pregunta de Triage para determinar la gravedad y el contexto.
    * **Pregunta de Triage Modelo (Obligatoria si hay ambigüedad):** "Para ofrecerle un consejo preciso, necesito saber: 1) ¿Qué tan intenso es el síntoma (Escala 1 al 10)? 2) ¿Cuánto tiempo lleva con esta molestia? 3) ¿Hay otros síntomas asociados (fiebre, vómito, pérdida de visión, etc.)?"
    * *Solo después de esta pregunta (o si la respuesta del usuario en un turno posterior indica gravedad) se procede a la Alerta Roja.*
2. ALERTA ROJA (Emergencia Inmediata): Si la consulta es de extrema gravedad (ej: sangrado profuso, pérdida de conciencia, dolor de pecho súbito, accidente), **DEBES detener la conversación y ordenar acudir a urgencias**.
3. REFERENCIA MÉDICA: En **CADA** respuesta de salud (incluso si es un remedio casero), debes **reforzar la necesidad** de que el usuario consulte a su médico personal o profesional de salud para diagnóstico y tratamiento formal.
4. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.

FORMATO PARA CONSULTAS GENERALES:
Si el usuario solo saluda o pregunta de forma general, presenta el siguiente **MENÚ DE CONSULTA** antes de dar una respuesta:
* 1. Consulta Específica (Ej: "Tengo gastritis, ¿qué debo comer?")
* 2. Principios de la Zona Azul Adventista
* 3. Los 8 Remedios Naturales
* 4. Búsqueda de un Centro de Vida Sana
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Activadores de Alerta Roja INMEDIATA) ---
# Estas palabras son indicadores de ALARMA MAYOR que no deben ser ambiguos.
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA"]

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
            conn.close()
        except Exception as e:
            print(f"❌ Error al guardar en DB: {e}")
            pass

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON TRIAGE INTELIGENTE) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETÉNGASE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describe es una **emergencia médica grave**. Por favor, deje de chatear AHORA y llame de inmediato al servicio de urgencias (911/número local) o acuda a la sala de emergencias más cercana. Su vida es la prioridad.\n\n"
            "🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busque ayuda profesional sin demora.**"
        )

    # === 2. LÓGICA NORMAL (IA DE NUTRICIÓN ESPECIALIZADA CON JUICIO) ===
    try:
        # Detectar si el usuario solo está saludando o necesita el menú
        is_general_query = len(mensaje_usuario.split()) < 6 and any(word in mensaje_upper for word in ["HOLA", "MENÚ", "SALUDO", "GRACIAS", "¿QUÉ HACES?", "AYUDA", "CONSULTA"])

        if is_general_query:
            # Si es un saludo, obligar al LLM a presentar el menú
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}\n\n[INSTRUCCIÓN EXTRA: Inicia la respuesta con el MENÚ DE CONSULTA antes de responder al saludo.]"
        else:
            # Si es una consulta de salud, la INSTRUCCION_SISTEMA ya obliga al Triage Inteligente
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        
        # Refuerzo para asegurar el descargo y la referencia médica (aunque ya está en la instrucción)
        if "alerta roja" not in texto.lower():
             if "médico personal" not in texto.lower() and "profesional de salud" not in texto.lower():
                 texto += "\n\n*Nota:* Siempre acuda a su médico personal para un diagnóstico formal. Yo soy un educador de salud, no su doctor tratante."
        
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Sin cambios)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    respuesta = consultar_gemini(mensaje_in)
    
    guardar_historial(celular, mensaje_in, respuesta)

    if 'whatsapp' in request.values.get('From', '').lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (TRIAGE INTELIGENTE) - ACTIVO")
    app.run(port=5000, debug=True)