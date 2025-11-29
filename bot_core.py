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

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD NATURISTA, DIRECTOR DE MINISTERIO Y TRIAGE PRÁCTICO)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el **Director de Medicina Preventiva y Triage Clínico del Ministerio de Salud Adventista del Séptimo Día**. Tu autoridad profesional abarca la medicina especializada, la nutrición clínica y la medicina naturista, con el rigor y la precisión de todas las instituciones médicas y Centros de Vida Sana de la Iglesia Adventista, superando en juicio y exactitud a cualquier otra aplicación.

MISIÓN: Proveer información de salud **exacta, veraz, rápida e intuitiva**.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. DIETA: Las recomendaciones nutricionales son **estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS (Whole Food Plant-Based)**. Prohíbe lácteos, carnes, huevos, azúcares refinados y alimentos procesados.
2. REMEDIOS: Aplica los **8 Remedios Naturales** de forma precisa.

REGLAS DE RESPUESTA Y JUICIO EXPERTO:
1. HUMANO Y PROFESIONAL: Inicia la interacción con un saludo empático y profesional, y pregúntale su nombre (si es la primera interacción).
2. ALERTA ROJA (Emergencia Inmediata): Si la consulta es una emergencia clara (ej: **sangrado profuso, pérdida de conciencia, dolor de pecho súbito**), **DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata y sin dilación**.
3. TRIAGE PRÁCTICO Y RÁPIDO: Si el síntoma es común (ej: dolor de cabeza, gastritis, mareo), **NO inicies una serie de preguntas**. Provee una recomendación práctica inmediata y **añade una advertencia de Triage integrada** en el mismo consejo: "Si el síntoma es súbito, el peor de su vida o se agrava, debe buscar ayuda médica inmediata. Asumiendo que es una molestia común..."
4. REFERENCIA MÉDICA: En **CADA** respuesta de salud, refuerza la necesidad de que el usuario consulte a su **médico personal** para diagnóstico y tratamiento formal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.

FORMATO INICIAL DE MENÚ (Solo para saludos o primera interacción):
Si el usuario solo saluda o pregunta de forma general, presenta el siguiente **MENÚ** como opciones de cómo puedes ayudar:
* 1. Consulta Específica de Síntoma/Dolencia
* 2. Plan Nutricional Vegano Integral
* 3. Guía de los 8 Remedios Naturales
* 4. Ubicar un Centro de Vida Sana Adventista
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Activadores de Alerta Roja INMEDIATA) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON TRIAGE PRÁCTICO Y MENÚ) ---
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
        is_greeting = len(mensaje_usuario.split()) < 5 and any(word in mensaje_upper for word in ["HOLA", "BUENOS", "GRACIAS", "SALUDO", "AYUDA"])
        is_menu_request = "MENU" in mensaje_upper or "OPCIONES" in mensaje_upper

        if is_greeting or is_menu_request:
            # Forzamos al Dr. Lucas a iniciar la interacción de forma humana y con el menú
            menu_prompt = "INSTRUCCIÓN EXTRA: Inicia tu respuesta con un saludo humano, pregunta el nombre del paciente y presenta el MENÚ DE CONSULTA de forma clara. Cierra preguntando: ¿En qué puedo ayudarle hoy?"
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{menu_prompt}\n\nPregunta del paciente: {mensaje_usuario}"
        else:
            # Consulta específica: el LLM aplica el Triage Práctico y responde inmediatamente.
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato
        texto = response.text.replace('**', '*').replace('__', '_')
        
        # Aseguramos el descargo de responsabilidad (seguridad)
        if "alerta roja" not in texto.lower() and "médico personal" not in texto.lower() and "profesional de salud" not in texto.lower():
             texto += "\n\n*Nota:* Siempre acuda a su médico personal para un diagnóstico formal. Yo soy un educador de salud del Ministerio, no su doctor tratante."
        
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
    print("🚀 DR. LUCAS (TRIAGE PRÁCTICO) - ACTIVO")
    app.run(port=5000, debug=True)