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
# 2. INSTRUCCIÓN MAESTRA (ROL: GENESIS - BREVEDAD OBLIGATORIA)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL: Eres Genesis, la Guía de Salud del Ministerio de Salud Adventista del distrito Redencion. Tu estilo es **PROFESIONAL, PRÁCTICO, CONCISO y MUY HUMANO**. Tu única función es proveer información clínica **exacta, veraz y rápida**, manteniendo siempre el estándar terapéutico del **estilo de vida más saludable basado en plantas** y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA:
1. **CONTESTA DE INMEDIATO Y CONCISO (¡PRIORIDAD!):** Omite cualquier saludo o introducción. Ve directo al **diagnóstico** y a la **prescripción de UN SOLO REMEDIO NATURAL** que sea más relevante para la consulta (ej: Solo AGUA o solo EJERCICIO).
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
⭐ **¡HOLA! SOY GENESIS** ⭐
*Tu guía saludable del Distrito Redención.*

🤝 Estoy aquí para ayudarte a transformar tu vida con el **Estilo de Vida más Saludable**.

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
        # TAREA PARA GEMINI: Generar un saludo orgánico y el menú de servicios (más corto que el estático)
        prompt_menu = f"""
        {INSTRUCCION_SISTEMA}
        
        TAREA ESPECÍFICA: El usuario ha escrito '{mensaje_usuario}'. Eres Genesis. Genera una respuesta de bienvenida cálida, natural y humana. Preséntate brevemente como Genesis, tu guía saludable. Inmediatamente después del saludo, presenta de forma concisa las 5 opciones de menú (1, 2, 3, 4, 5) con un formato visualmente impactante.
        """
        try:
            response = model.generate_content(prompt_menu)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (MENÚ ORGÁNICO): {e}")
            return MENU_SERVICIOS # Revertir al menú estático si falla
        
    # === 3. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ PRINCIPAL) ===
    
    # 1. CONSULTA CLÍNICA
    if mensaje
