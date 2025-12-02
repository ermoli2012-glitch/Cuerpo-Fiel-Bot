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

# --- DATOS DE CONTACTO Y ENLACES (Variables de uso interno) ---
# Usaremos este número para Orientación Psicológica temporalmente.
WHATSAPP_CONTACTO_PSICOLOGIA = "3122521843" 
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA (ROL: GENESIS)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL: Eres Genesis, la Guía de Salud del Ministerio de Salud Adventista del distrito Redencion. Tu estilo es **PROFESIONAL, PRÁCTICO, CÁLIDO y MUY HUMANO**. Tu única función es proveer información clínica **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico del **estilo de vida más saludable basado en plantas** y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA:
1. **CONTESTA DE INMEDIATO:** Omite cualquier saludo o introducción en la respuesta clínica. Ve directo al diagnóstico.
2. **RESPUESTA ORGÁNICA:** Cuando te saluden ("hola"), genera un saludo humano y cálido, y preséntate como Genesis. Inmediatamente después del saludo, presenta de forma muy conversacional el menú de servicios (Consulta, Psicología, Iglesias, Radio). Usa los enlaces de contacto en el menú.
3. Contexto Adventista: Toda prescripción debe estar alineada con los principios bíblicos de salud y la filosofía Adventista.
4. Versículo Bíblico: **La cita bíblica debe ser ALTAMENTE RELEVANTE** al tema consultado (ej: Estrés -> Reposo; Enfermedad -> Cuerpo Templo; Dieta -> Creación).
5. Formato: Usa negritas, saltos de línea amplios, emojis cálidos (ej: 👋, 🙏) y lenguaje profesional e inspirador.
6. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
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


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la respuesta del bot con lógica condicional para el menú.
    """
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_limpio for keyword in EMERGENCY_KEYWORDS):
        return """
🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴

El síntoma que describes es una **emergencia médica grave**.
Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
Tu vida es la prioridad.

🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**
"""

    # === 2. LÓGICA CONDICIONAL DE MENÚ/SALUDO (RESPUESTA HUMANA Y FORMATO IMPACTANTE) ===
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR"]:
        
        # PROMPT ESPECÍFICO CON INSTRUCCIONES DE FORMATO VIRAL
        prompt_menu = f"""
        {INSTRUCCION_SISTEMA}
        
        TAREA ESPECÍFICA: El usuario ha escrito '{mensaje_usuario}'. Eres Genesis. Genera una respuesta de bienvenida cálida, natural y humana. Preséntate brevemente como Genesis, tu guía saludable. Inmediatamente después del saludo, presenta el menú de servicios.
        
        INSTRUCCIONES DE FORMATO ADICIONALES (¡OBLIGATORIAS!):
        - El formato debe ser **VISUALMENTE IMPACTANTE, MODERNO Y VIRAL**. Usa emojis de bloques y líneas horizontales (como guiones o asteriscos) para separar las secciones.
        - Los enlaces deben ser **cliqueables** (ej: **[Texto del Link]({RADIO_LINK})**).
        - El menú debe ser PRÁCTICO.
        
        MENÚ REQUERIDO:
        1. **Consulta Clínica** (Pide la pregunta de salud).
        2. **Orientación Psicológica** (Contacto: {WHATSAPP_CONTACTO_PSICOLOGIA}).
        3. **Directorio de Iglesias** ([Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})).
        4. **Radio Adventista** ([AWR Colombia]({RADIO_LINK})).
        """
        
        try:
            response = model.generate_content(prompt_menu)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (MENÚ ORGÁNICO): {e}")
            return "👋 ¡Hola! Soy Genesis. Lo siento, tengo una pequeña dificultad técnica. Por favor, escribe tu pregunta de salud."

    # === 3. LÓGICA DE REGLA AUTOMATIZADA (Fuera de la IA para mayor fiabilidad) ===
    
    # Palabras clave para Orientación Psicológica
    keywords_psicologia = ["PSICOLOGIA", "ANSIEDAD", "DEPRESION", "ESTRES", "CONTACTO", "MENTAL"]
    if any(k in mensaje_limpio for k in keywords_psicologia):
        return (
            "🧠 *¡Tu bienestar mental es la prioridad!* Te asistiremos con **Orientación Psicológica**.\n\n"
            "Para iniciar la sesión de apoyo emocional, comunícate al:\n"
            f"📲 **Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}**\n\n"
            "«El descanso del cuerpo y la mente es vital para la salud espiritual.»"
        )
        
    # Palabras clave para la radio
    keywords_radio = ["RADIO", "AWR", "ESCUCHAR", "ESPERANZA"]
    if any(k in mensaje_limpio for k in keywords_radio):
        return (
            "📻 *¡El mensaje de la triple ángel!* Conéctate a nuestra **Voz de Esperanza**.\n\n"
            f"Escúchanos aquí: **[AWR Colombia]({RADIO_LINK})**\n\n"
            "«El que cree en mí, aunque esté muerto, vivirá» (Juan 11:25)."
        )
        
    # Palabras clave para iglesias/directorio
    keywords_iglesias = ["IGLESIA", "CENTROS", "DIRECTORIO", "VIDA SANA", "COMUNIDAD", "TEMPLO"]
    if any(k in mensaje_limpio for k in keywords_iglesias):
        return (
            "📍 *¡Encuentra una comunidad de fe y salud!* Para buscar tu iglesia o centro de vida sana más cercano, usa el directorio:\n\n"
            f"🔗 **[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})**\n\n"
            "«No dejando de congregarnos, como algunos tienen por costumbre...» (Hebreos 10:25)."
        )


    # === 4. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
    try:
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        response = model.generate_content(prompt_full)
     
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return """
⚠️ Lo siento, Genesis está en una consulta crítica.
Intenta de nuevo en un momento."
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
    print("🚀 GENESIS (FLUJO DIRECTO Y EFICIENTE) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)
