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
WHATSAPP_CONTACTO_PSICOLOGIA = "3122521843"
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA (RESPUESTA CORTA Y PRECISA)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL: Eres Genesis, la Guía de Salud del Ministerio de Salud Adventista del distrito Redencion. Tu estilo es **PROFESIONAL, PRÁCTICO, CONCISO y MUY HUMANO**. Tu única función es proveer información clínica **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico del **estilo de vida más saludable basado en plantas** y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA:
1. **CONTESTA DE INMEDIATO Y CONCISO (¡PRIORIDAD!):** Omite cualquier saludo o introducción. Ve directo al **diagnóstico** y a la **prescripción de UN SOLO REMEDIO NATURAL** que sea más relevante para la consulta.
2. Contexto Adventista: Toda prescripción debe estar alineada con los principios bíblicos de salud y la filosofía Adventista.
3. Versículo Bíblico: **La cita bíblica debe ser ALTAMENTE RELEVANTE** al tema consultado.
4. Formato: Usa negritas, saltos de línea y emojis.
5. **Cierre Práctico (OBLIGATORIO):** Al final de la respuesta, incluye una frase invitando al usuario a la interacción, como: *'¿Te gustaría saber más sobre este Remedio Natural o los otros 7 pilares de salud?'*
6. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# --- MENÚ DE SERVICIOS (Texto para la activación con "hola" o "menu") ---
MENU_SERVICIOS = f"""
👋 **¡HOLA! SOY GENESIS.**
*Tu guía saludable del Ministerio de Salud Adventista.*

**¡Bienvenido!** Estoy aquí para asistirte con tu **Estilo de Vida Saludable**.

----------------------------------------
** Selecciona una opción para empezar:**
----------------------------------------

* **1️⃣ CONSULTA CLÍNICA:** Pregúntame sobre cualquier síntoma o tratamiento natural.
* **2️⃣ APOYO PSICOLÓGICO:** ¿Necesitas ayuda con estrés, ansiedad o depresión?
* **3️⃣ COMUNIDAD DE FE:** Encuentra tu iglesia o centro de vida sana.
* **4️⃣ VOZ DE ESPERANZA:** Conéctate a la Radio Adventista AWR.
* **5️⃣ MÓDULO EJERCICIO:** ¡Únete al **Reto Poder 8** y entrena de forma inteligente!

*Responde solo con el número (ej: 1 o 5)*
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


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL COMPLETO) ---
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
        # Se revierte a la respuesta estática para evitar el SyntaxError
        return MENU_SERVICIOS 
        
    # === 3. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ PRINCIPAL) ===
    
    # 1. CONSULTA CLÍNICA
    if mensaje_limpio == "1":
        return (
            "🩺 **Consulta Clínica: Pregunta al instante**\n\n"
            "¡Listo/a! Escribe tu pregunta sobre cualquier síntoma, condición o necesidad de tratamiento natural. "
            "Recuerda que mis consejos se basan en la dieta saludable y los 8 Remedios Naturales."
        )

    # 2. APOYO PSICOLÓGICO
    if mensaje_limpio == "2":
        return (
            "🧠 **Apoyo Psicológico: Paz Mental**\n\n"
            "Tu salud emocional es vital. Para iniciar una sesión de apoyo confidencial para manejar "
            "estrés o ansiedad, comunícate al:\n"
            f"📲 **Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}**\n\n"
            "«El reposo mental es una parte esencial de la adoración a Dios.»"
        )
        
    # 3. COMUNIDAD DE FE
    if mensaje_limpio == "3":
        return (
            "📍 **Comunidad de Fe: Encuentra tu Hogar**\n\n"
            "Para un crecimiento integral, es vital congregarse. Usa el siguiente enlace para buscar "
            "tu iglesia Adventista o Centro de Vida Sana más cercano:\n"
            f"🔗 **[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})**"
        )
        
    # 4. RADIO ADVENTISTA
    if mensaje_limpio == "4":
        return (
            "📻 **Voz de Esperanza: Inspiración Diaria**\n\n"
            "Conéctate a mensajes que transforman tu vida y fortalecen tu fe. Escucha nuestra programación:\n"
            f"🔗 **[AWR Colombia]({RADIO_LINK})**"
        )
        
    # 5. MÓDULO EJERCICIO: PODER 8 (Entrada)
    if mensaje_limpio == "5":
        return """
💪 **¡Bienvenido al Reto Poder 8!** 🚀

Este es un módulo de entrenamiento innovador que equilibra los **8 Remedios Naturales**.

🧠 *Inteligencia Viral:* Ajustamos tu rutina según tu **conexión mental-músculo** y tu **ritmo de reposo sabático**.

🔥 *¿Cómo te gustaría empezar?*
   A. **Mi Rutina:** Describe tus metas de *fitness* (ej: 'quiero ganar músculo y tener más energía').
   B. **Conciencia Corporal:** ¿Cómo evaluas tu fatiga post-entreno de hoy (1-5)?
   C. **Comunidad:** ¡Quiero unirme al desafío de puntos de vitalidad!
"""

    # === 4. LÓGICA DE PROFUNDIZACIÓN: 8 REMEDIOS NATURALES ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES"]
    
    if any(k in mensaje_limpio for k in keywords_mas_info):
        return """
✨ **Los 8 Pilares de la Salud** ✨

¡Me encanta tu interés por la **restauración completa**! Estos son los **8 Remedios Naturales** que promueven la sanidad integral, tal como los enseñan las Escrituras:

1.  **🌿 Nutrición (Alimentos sanos)**
2.  **💧 Agua**
3.  **☀️ Luz Solar**
4.  **🏃 Ejercicio**
5.  **🌬️ Aire Puro**
6.  **😴 Descanso**
7.  **🧘 Templanza** (Moderación y Equilibrio)
8.  **🙏 Esperanza en Dios** (Confianza en el poder divino)

*¿Sobre cuál de estos 8 te gustaría recibir un consejo práctico y bíblico? Responde con el nombre del pilar.*
"""
        
    # === 5. LÓGICA DE SUB-MENÚ DEL MÓDULO 5 (RESPUESTAS A B Y C) ===
    
    # Palabras clave que indican una interacción continua con el Módulo 5 (Reto Poder 8)
    keywords_modulo_5 = ["MI RUTINA", "CONCIENCIA CORPORAL", "COMUNIDAD", "FATIGA", "MENTE", "MÚSCULO", "FUERZA", "EJERCICIO"]
    
    # Si el mensaje es una de las letras de la opción, o una pregunta detallada DENTRO del contexto del Reto Poder 8
    if mensaje_limpio in ["A", "B", "C"] or any(k in mensaje_limpio for k in keywords_modulo_5):
        
        # PROMPT DE DELEGACIÓN A GEMINI PARA RESPUESTA CONTEXTUAL
        prompt_sub_menu = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE CONVERSACIÓN: El usuario está dentro del **Módulo de Ejercicio Reto Poder 8**. 
        
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". 
        
        * Si el usuario pide **Rutina (A)** o metas (ej: 'ganar masa muscular'), genera un plan de 7 días con un enfoque Adventista (incluyendo el Reposo).
        * Si el usuario pide **Conciencia Corporal (B)** o da su *feedback* (ej: 'Fatiga 3'), analiza su estado y sugiere un ajuste simple para la siguiente sesión, reforzando la salud integral.
        * Si el usuario pide **Comunidad (C)**, dale la respuesta de unirse al grupo de Telegram (o el canal de comunicación que decidas).
        
        Responde al grano, manteniendo el tono profesional y el enfoque Poder 8.
        """
        
        try:
            response = model.generate_content(prompt_sub_menu)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (RESPUESTA MÓDULO 5): {e}")
            return "⚠️ Lo siento, no puedo generar esa respuesta ahora. Intenta de nuevo describiendo tu objetivo."

    # === 6. LÓGICA DE REGLA AUTOMATIZADA (Búsqueda por palabras clave sin el menú) ===
    
    # Palabras clave para Orientación Psicológica (directa)
    keywords_psicologia = ["PSICOLOGIA", "ANSIEDAD", "DEPRESION", "ESTRES", "CONTACTO", "MENTAL"]
    if any(k in mensaje_limpio for k in keywords_psicologia):
        return (
            "🧠 *¡Tu bienestar mental es la prioridad!* Te asistiremos con **Orientación Psicológica**.\n\n"
            "Para iniciar la sesión de apoyo emocional, comunícate al:\n"
            f"📲 **Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}**\n\n"
            "«El reposo mental es una parte esencial de la adoración a Dios.»"
        )
        
    # Palabras clave para la radio (directa)
    keywords_radio = ["RADIO", "AWR", "ESCUCHAR", "ESPERANZA"]
    if any(k in mensaje_limpio for k in keywords_radio):
        return (
            "📻 *¡El mensaje de la triple ángel!* Conéctate a nuestra **Voz de Esperanza**.\n\n"
            f"Escúchanos aquí: **[AWR Colombia]({RADIO_LINK})**\n\n"
            "«El que cree en mí, aunque esté muerto, vivirá» (Juan 11:25)."
        )
        
    # Palabras clave para iglesias/directorio (directa)
    keywords_iglesias = ["IGLESIA", "CENTROS", "DIRECTORIO", "VIDA SANA", "COMUNIDAD", "TEMPLO"]
    if any(k in mensaje_limpio for k in keywords_iglesias):
        return (
            "📍 *¡Encuentra una comunidad de fe y salud!* Para buscar tu iglesia o centro de vida sana más cercano, usa el directorio:\n\n"
            f"🔗 **[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})**\n\n"
            "«No dejando de congregarnos, como algunos tienen por costumbre...» (Hebreos 10:25)."
        )

    # Palabras clave para ejercicio (directa)
    keywords_ejercicio = ["EJERCICIO", "GIMNASIO", "ENTRENAMIENTO", "RUTINA", "MÚSCULO", "PODER 8"]
    if any(k in mensaje_limpio for k in keywords_ejercicio):
        # Redirigimos a la opción 5
        return consultar_gemini(celular, "5") 


    # === 7. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
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
# 8. RUTAS WEB Y DE WHATSAPP (Sin cambios
