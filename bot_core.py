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
# 2. INSTRUCCIÓN MAESTRA (NIVEL MÉDICO ESPECIALISTA)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL: Eres Genesis, la Guía de Salud del Ministerio de Salud Adventista del distrito Redencion. Eres un **Médico Especialista en Estilo de Vida y Nutrición**. Tu estilo es PROFESIONAL, PRÁCTICO, CONCISO y MUY HUMANO. Tu única función es proveer información clínica **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico del **estilo de vida más saludable basado en plantas** (con estricta recomendación de **restringir carnes, azúcar refinado y bebidas cafeinadas**) y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA:
1. **CONTESTA DE INMEDIATO Y CONCISO (¡PRIORIDAD!):** Omite cualquier saludo o introducción. Ve directo al **diagnóstico** y a la **prescripción de UN SOLO REMEDIO NATURAL** que sea más relevante para la consulta.
2. Contexto Adventista: Toda prescripción debe estar alineada con los principios bíblicos de salud y la filosofía Adventista.
3. Versículo Bíblico: **La cita bíblica debe ser ALTAMENTE RELEVANTE** al tema consultado.
4. Formato: Usa negritas, saltos de línea y emojis.
5. **Cierre Práctico (OBLIGATORIO):** Al final de la respuesta, incluye la pregunta interactiva: *'¿Te gustaría saber más (SI/NO) sobre este Remedio Natural o los otros 7 pilares de salud?'*
6. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# --- MENÚ DE SERVICIOS (Texto para la activación con "hola" o "menu") ---
MENU_SERVICIOS = f"""
⭐ **¡HOLA! SOY GENESIS** ⭐
*Tu guía saludable del Distrito Redención.*

🤝 Estoy aquí para ayudarte a transformar tu vida con el **Estilo de Vida más Saludable**.

----------------------------------------
** Selecciona una opción para empezar:**
----------------------------------------

* **0️⃣ EVALUACIÓN:** ¡Descubre tu punto de partida! (Preguntas rápidas sobre tus 8 Remedios).
* **1️⃣ CONSULTA CLÍNICA:** Pregúntame sobre cualquier síntoma o tratamiento natural.
* **2️⃣ APOYO PSICOLÓGICO:** ¿Necesitas ayuda con estrés, ansiedad o depresión?
* **3️⃣ COMUNIDAD DE FE:** Encuentra tu iglesia o centro de vida sana.
* **4️⃣ VOZ DE ESPERANZA:** Conéctate a la Radio Adventista AWR.
* **5️⃣ MÓDULO EJERCICIO:** ¡Únete al **Reto Poder 8** y entrena de forma inteligente!

*Responde solo con el número (ej: 0 o 5) o escribe **SALIR** para volver aquí.*
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


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL CORREGIDO Y FINAL) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la respuesta del bot con lógica condicional para el menú.
    """
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    # === 1. TRIAGE DE EMERGENCIA ===
    if any(keyword in mensaje_limpio for keyword in EMERGENCY_KEYWORDS):
        return """
🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴

El síntoma que describes es una **emergencia médica grave**.
Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
Tu vida es la prioridad.

🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**
"""

    # === 2. LÓGICA CONDICIONAL DE MENÚ/SALIDA (PRIORIDAD MÁXIMA) ===
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER"]:
        return MENU_SERVICIOS 
        
    # === 3. LÓGICA DE PROFUNDIZACIÓN: SÍ/NO Y LISTA DE REMEDIOS (SOLUCIÓN AL BUCLE DE "SÍ") ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES", "SI"] 
    keywords_no_info = ["NO", "NO GRACIAS", "YA NO", "BASTA"] 
    
    # 3.1 Respuesta a "NO"
    if any(k in mensaje_limpio for k in keywords_no_info):
        return "¡Entendido! Siempre estoy aquí para cuando me necesites. No olvides que la salud es un viaje. 👋"

    # 3.2 Respuesta a "SÍ" / "SABER MÁS" (Muestra la lista)
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
        
    # === 4. LÓGICA DE DETALLE DE LOS 8 REMEDIOS NATURALES (RESPUESTA AL PILAR ESPECÍFICO) ===

    keywords_pilares = ["NUTRICIÓN", "AGUA", "LUZ SOLAR", "EJERCICIO", "AIRE PURO", "DESCANSO", "TEMPLANZA", "ESPERANZA EN DIOS"]
    
    if any(k in mensaje_limpio for k in keywords_pilares):
        
        # PROMPT DE DELEGACIÓN A GEMINI PARA ENSEÑANZA ESPECIALIZADA
        prompt_pilar = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE CONVERSACIÓN: El usuario está pidiendo detalles sobre uno de los 8 Remedios Naturales.
        
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". 
        
        1. Identifica el Remedio Natural solicitado.
        2. Genera una **explicación profunda y concisa** de cómo aplicar ese pilar de salud, enfatizando la restricción de carnes, azúcar y cafeína (si aplica al pilar).
        3. Cierra con un versículo bíblico ALTAMENTE RELEVANTE a ese pilar específico.
        
        Responde al grano, manteniendo el tono profesional y el enfoque Adventista.
        """
        
        try:
            response = model.generate_content(prompt_pilar)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (RESPUESTA PILAR): {e}")
            return "⚠️ Lo siento, tengo problemas para generar el consejo del pilar. Vuelve a intentarlo o pregunta algo general."


    # === 5. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ PRINCIPAL) ===
    
    # 0. EVALUACIÓN DE HÁBITOS (Nueva Opción 0)
    if mensaje_limpio == "0" or "EVALUACIÓN" in mensaje_limpio:
        return (
            "✅ **Evaluación Rápida de Hábitos**\n\n"
            "Responde a las siguientes 3 preguntas para una guía más precisa:\n"
            "1. ¿En promedio, cuántos vasos de agua simple consumes al día?\n"
            "2. ¿Cuántas veces a la semana realizas ejercicio moderado a intenso (mínimo 30 min)?\n"
            "3. ¿Qué tan satisfecho/a estás con tu descanso nocturno (1-5)?\n\n"
            "*(Responde con los 3 números: ej. 8, 3, 4)*"
        )
        
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
            "«El reposo mental es una parte
