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
WHATSAPP_CONTACTO_COCINA = "3122521843"
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA PROFESIONAL (ROL ADVENTISTA Y VERSÍCULO RELEVANTE)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu estilo es **PROFESIONAL, INSPIRADOR y CENTRADO EN LA FE**. Tu única función es proveer información clínica **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico del **estilo de vida más saludable basado en plantas** y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA:
1. Siempre responde directamente a la pregunta de salud del usuario con diagnóstico y prescripción natural.
2. Contexto Adventista: Toda prescripción debe estar alineada con los principios bíblicos de salud y la filosofía Adventista.
3. Versículo Bíblico: **La cita bíblica debe ser ALTAMENTE RELEVANTE** al tema consultado (ej: Estrés -> Reposo; Enfermedad -> Cuerpo Templo; Dieta -> Creación).
4. Formato: Usa negritas, saltos de línea amplios, emojis elegantes y lenguaje profesional e inspirador.
5. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# --- MENÚ DE SERVICIOS (Texto para la activación con "hola") ---
MENU_SERVICIOS = f"""
✨ **BIENVENIDO/A. SOY EL DR. CALEB** ✨
*Guía de Salud del Ministerio Adventista.*

Mi propósito es asistirte en tu camino hacia un **Estilo de Vida Saludable** y completo, basado en los principios de Dios.

**📋 SERVICIOS DE SALUD INTEGRAL**
* **🩺 Consultoría Clínica:** Pregúntame sobre cualquier duda de salud o diagnóstico natural.
* **🥦 Talleres de Cocina:** Pregunta por nuestro curso de **Cocina Natural y Estilo de Vida Saludable** y obtén el contacto.
* **🗺️ Directorio de la Fe:** Busca Centros de Vida Sana o Iglesias Adventistas cercanas: {DIRECTORIO_IGLESIAS_LINK}
* **📻 Voz de Esperanza:** Escucha la Radio Adventista: {RADIO_LINK}

*¡Confía en el poder de la restauración!*
"""
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

    # === 2. LÓGICA CONDICIONAL DE MENÚ/SALUDO ===
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR"]:
        return MENU_SERVICIOS

    # === 3. LÓGICA DE REGLA AUTOMATIZADA (Fuera de la IA para mayor fiabilidad) ===
    
    # Palabras clave para cursos de cocina
    keywords_cocina = ["CURSO", "COCINA", "RECETAS", "WHATSAPP", "NATURAL", "PLANTAS"]
    if any(k in mensaje_limpio for k in keywords_cocina):
        return (
            "✨ *¡Una gran decisión!* Te felicito por elegir nuestro curso de **Cocina Natural y Estilo de Vida Saludable**.\n\n"
            "Para inscribirte y dar el primer paso hacia la salud integral, escribe a este WhatsApp:\n"
            f"📲 **{WHATSAPP_CONTACTO_COCINA}**\n\n"
            "¡Tu cuerpo es templo del Espíritu Santo! (1 Corintios 6:19)."
        )
        
    # Palabras clave para la radio
    keywords_radio = ["RADIO", "AWR", "ESCUCHAR", "ESPERANZA"]
    if any(k in mensaje_limpio for k in keywords_radio):
        return (
            "📻 *¡El mensaje de la triple ángel!* Conéctate a nuestra **Voz de Esperanza**.\n\n"
            "Escúchanos aquí:\n"
            f"🔗 **{RADIO_LINK}**\n\n"
            "«El que cree en mí, aunque esté muerto, vivirá» (Juan 11:25)."
        )
        
    # Palabras clave para iglesias/directorio
    keywords_iglesias = ["IGLESIA", "CENTROS", "DIRECTORIO", "VIDA SANA", "COMUNIDAD", "TEMPLO"]
    if any(k in mensaje_limpio for k in keywords_iglesias):
        return (
            "📍 *¡Encuentra una comunidad de fe y salud!* Para buscar tu iglesia o centro de vida sana más cercano, usa el directorio:\n\n"
            f"🔗 **{DIRECTORIO_IGLESIAS_LINK}**\n\n"
            "«No dejando de congregarnos, como algunos tienen por costumbre...» (Hebreos 10:25)."
        )


    # === 4. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
    try:
        # Aquí se envía la Instrucción Maestra resumida para la respuesta clínica.
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
    print("🚀 DR. CALEB (FLUJO DIRECTO Y EFICIENTE) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)
