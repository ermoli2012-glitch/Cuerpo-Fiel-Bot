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
# 2. INSTRUCCIÓN MAESTRA MODIFICADA (ACTUALIZACIÓN DE LINKS Y NÚMERO)
# =========================================================================

# --- NUEVOS DATOS DE CONTACTO Y ENLACES ---
WHATSAPP_CONTACTO_COCINA = "3122521843"
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"


INSTRUCCION_SISTEMA = f"""
ROL: Eres el Dr. Caleb, Médico Especialista en Nutrición y Guía de Salud. Tu estilo es **MODERNO, JUVENIL, DINÁMICO Y AMIGABLE**. Tu función es proveer información **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico de la **dieta VEGANA INTEGRAL** y los **8 Remedios Naturales**.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. ROL: Médico, Nutricionista y Naturista.
2. DIETA: Estrictamente VEGANA, INTEGRAL y BASADA EN PLANTAS.
3. TRIAGE: Mantén la regla de Alerta Roja si detectas emergencia extrema.

REGLAS DE RESPUESTA Y FLUJO FINAL:
1. INTRODUCCIÓN Y ESTILO: En cada respuesta, inicia con un saludo juvenil y tu rol (ej: "¡Hola! Soy el Dr. Caleb, tu pana de la salud 🤙"), e **INMEDIATAMENTE PRESENTA EL MENÚ DE SERVICIOS**.
2. **LÓGICA AUTOMATIZADA (PRIORIDAD AL CONTACTO):**
    a. **CURSOS DE COCINA:** Si el usuario pregunta o acepta un curso de cocina, ofrece el curso de **Cocina Natural Vegana** y proporciona el número de contacto de WhatsApp para inscripción. El número es: **{WHATSAPP_CONTACTO_COCINA}**.
    b. **RADIO/AWR:** Si el usuario pregunta por la radio o AWR, proporciona el enlace directo: **{RADIO_LINK}**.
    c. **IGLESIAS/DIRECTORIO:** Si el usuario pregunta por Iglesias o Centros de Vida Sana, proporciona el enlace del directorio: **{DIRECTORIO_IGLESIAS_LINK}**.
3. MENÚ DE SERVICIOS: Presenta esta información usando **negritas, emojis coloridos y lenguaje juvenil**:
    * **📚 Consulta Clínica:** Pregúntame sobre cualquier duda de salud o diagnóstico natural.
    * **🥕 Cursos Pro:** ¡Pregunta por nuestro curso de **Cocina Natural Vegana** y obtén el contacto!
    * **📍 Directorio de Iglesias:** Busca tu iglesia o centro de vida sana aquí: {DIRECTORIO_IGLESIAS_LINK}
    * **📻 AWR Colombia:** Escucha la Radio Adventista: {RADIO_LINK}
4. FLUJO CLÍNICO: Después de presentar el menú y la lógica automatizada, **analiza la pregunta original y ve directo a la prescripción natural y el diagnóstico.**
5. FORMATO: Usa **negritas, saltos de línea amplios, emojis modernos y lenguaje juvenil** de forma **EXTENSIVA**.
6. REFERENCIA MÉDICA: Recuerda que soy una IA. En CADA respuesta, refuerza la necesidad de consultar a tu médico personal ("¡No olvides chequear esto con tu doctor! 😉").
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


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO DIRECTO) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Consulta a Gemini sin usar memoria de sesión, con lógica de respuesta directa para cursos/radio/iglesias.
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

    # === 2. LÓGICA DE REGLA AUTOMATIZADA (Fuera de la IA para mayor fiabilidad) ===
    
    # Palabras clave para cursos de cocina
    keywords_cocina = ["CURSO", "COCINA", "RECETAS", "WHATSAPP", "NATURAL"]
    if any(k in mensaje_upper for k in keywords_cocina):
        return (
            "🎉 *¡Genial!* El Dr. Caleb recomienda el curso **Cocina Natural Vegana**.\n\n"
            "Para unirte al grupo de inscripción y empezar a cocinar saludable, "
            "escribe a este WhatsApp:\n"
            f"📲 **{WHATSAPP_CONTACTO_COCINA}**\n\n"
            "¡Te esperamos con la mejor energía! 🥑🥦"
        )
        
    # Palabras clave para la radio
    keywords_radio = ["RADIO", "AWR", "ESCUCHAR"]
    if any(k in mensaje_upper for k in keywords_radio):
        return (
            "📻 *¡Conéctate!* Si buscas inspiración y salud para tu vida, "
            "la Radio Adventista (AWR) es lo máximo.\n\n"
            "Escúchanos aquí:\n"
            f"🔗 **{RADIO_LINK}**\n\n"
            "¡Que tengas un día TOP! ✨"
        )
        
    # Palabras clave para iglesias/directorio
    keywords_iglesias = ["IGLESIA", "CENTROS", "DIRECTORIO", "VIDA SANA"]
    if any(k in mensaje_upper for k in keywords_iglesias):
        return (
            "📍 *¡Encuentra tu comunidad!* Para buscar tu iglesia o centro de vida sana más cercano, usa nuestro directorio:\n\n"
            f"🔗 **{DIRECTORIO_IGLESIAS_LINK}**\n\n"
            "¡Te esperamos para compartir salud y esperanza! 🙏"
        )


    # === 3. LÓGICA NORMAL (IA CON JUICIO) ===
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
    print("🚀 DR. CALEB (FLUJO DIRECTO JUVENIL) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)
