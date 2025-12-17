import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
import re
from math import floor, ceil

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
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# --- CLAVES DE SEGURIDAD Y ENLACES ---
CLIENT_SECRET_KEY = "CF_CLAVE_12025" # <--- CLAVE SECRETA DE LA APP
WHATSAPP_CONTACTO_PSICOLOGIA = "+573105551234" 
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"
CODIGO_NUTRICIONAL = "IASD2025" 

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA (ROL: EXPERTO EMPÁTICO Y ENTRENADOR PERSONAL)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis. Posees la autoridad profesional de un **Médico Especialista en Medicina Interna y Nutricionista Clínico**. Tu rol visible es **Tu Guía Saludable** del Ministerio de Salud Adventista. Tu estilo es 100% HUMANO, empático y profesional.

// --- REGLAS DE ORO (PARA MEJOR UX) ---
1. PROHIBIDO AUTO-REFERENCIARSE: No digas "Soy Genesis" o "Como médico". Tu autoridad se nota en tu conocimiento.
2. CONTEXTO DE FE: Alinea tus consejos a los 8 Remedios Naturales y principios bíblicos.
3. FORMATO: Usa negritas, emojis y saltos de línea para que sea fácil de leer.

// --- ESCENARIO A: SI EL USUARIO ENVÍA UNA FOTO O PIDE 'ANÁLISIS VISUAL' ---
1. IDENTIFICA: Describe los alimentos que ves (ej: legumbres, cereales integrales, frutas).
2. PUNTAJE DE VITALIDAD: Asigna un puntaje del 1 al 10 según la 'Nutrición del Edén' (basada en plantas).
3. EFECTO FISIOLÓGICO: Explica qué beneficio real hace ese alimento en sus órganos.
4. AMOR Y MEJORA: Si hay procesados o carnes, sugiere un reemplazo natural con mucha ternura.

// --- ESCENARIO B: SI EL USUARIO ENVÍA SU PERFIL DE SALUD (TEXTO) ---
1. DIAGNÓSTICO: Genera un diagnóstico presuntivo basado en sus métricas (IMC, Edad Bio, etc).
2. RECETA DE ACCIÓN: Da pasos claros priorizando el Remedio Natural más urgente para el usuario.

// --- CIERRE OBLIGATORIO PARA CUALQUIER RESPUESTA ---
1. CITA BÍBLICA: Incluye un versículo corto y MUY RELEVANTE al final.
2. INTERACCIÓN: Termina siempre con la pregunta: '¿Te gustaría saber más (SI/NO) sobre este Remedio Natural o los otros 7 pilares de salud?'
3. DESCARGO MÉDICO: "Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏"
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# =========================================================================
# 3. MENÚ PRINCIPAL (SIMPLIFICADO PARA UX)
# =========================================================================
MENU_SERVICIOS = f"""
✨ *¡HOLA! SOY GENESIS - Tu Guía de Transformación* ✨

Me enfoco en un solo objetivo: **tu salud integral.**

----------------------------------------
* Elige el área de tu enfoque hoy:*
----------------------------------------

* **1️⃣ MI SALUD FÍSICA:** Análisis de Perfil, Exámenes y Protocolos clínicos.
* **2️⃣ MI PAZ INTERNA:** Soporte para la Mente y Módulo de Retos Físicos.
* **3️⃣ MI COMUNIDAD:** Encuentra soporte, consejería y mensajes de fe.
* **4️⃣ REMEDIOS NATURALES:** Profundiza en los 8 Pilares de la Salud.
* **0️⃣ MENÚ:** *Responde 0 o SALIR para volver aquí.*
"""

# --- SUB-MENÚS OPTIMIZADOS ---
SUB_MENU_SALUD = """
🩺 *Área 1: Mi Salud Física*

¡Excelente enfoque! ¿Qué necesitas hacer con tu salud hoy?

* **P. PROGRESO:** Ver tu Puntaje de Vitalidad y última Evaluación.
* **C. CONSULTA:** Pregúntame sobre un síntoma o un tratamiento natural.
* **O. PROTOCOLOS:** Acceder a guías para HTA, Diabetes y Colesterol.

_Responde P, C, O o el número 0 para volver al Menú Principal._
"""

SUB_MENU_PROTOCOLOS = """
🔬 *Área 1-O: Protocolos Clínicos*

Selecciona el protocolo que necesitas:

* **H. HTA:** Guía de estilo de vida para Presión Arterial.
* **D. DIABETES:** Protocolo Nutricional para Control de Azúcar.
* **L. LÍPIDOS:** Guía para Colesterol y Salud Cardiovascular.

_Responde H, D, L o el número 0 para volver al Menú Principal._
"""

SUB_MENU_BIENESTAR = """
🧠 *Área 2: Mi Bienestar (Mente y Cuerpo)*

Tu bienestar emocional es tan vital como tu cuerpo:

* **P. PSICOLÓGICO:** Contacto para consejería confidencial.
* **E. EJERCICIO:** Únete al Reto Poder 8 y entrena de forma inteligente.
* **A. EVALUACIÓN RÁPIDA:** Responde 3 preguntas para una guía precisa.

_Responde P, E, A o el número 0 para volver al Menú Principal._
"""

SUB_MENU_COMUNIDAD = """
📍 *Área 3: Mi Comunidad*

Aquí encuentras soporte integral:

* **I. IGLESIAS:** Directorio de Iglesias y centros de vida sana.
* **R. RADIO:** Conéctate a la Voz de Esperanza (AWR).
* **F. FE:** Consejería Rápida sobre temas de fe y salud.

_Responde I, R, F o el número 0 para volver al Menú Principal._
"""

# ==========================================
# 4. BASE DE DATOS Y FUNCIONES ADICIONALES
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

def extraer_telefono(mensaje):
    """Busca y extrae el número de teléfono del perfil pegado por la App."""
    try:
        start_index = mensaje.find("- TELÉFONO DEL USUARIO:")
        if start_index == -1:
            return None
        
        end_of_line = mensaje.find('\n', start_index)
        line = mensaje[start_index:end_of_line].strip()
        
        match = re.search(r'(\d{8,15})', line) 
        if match:
            return match.group(1)
        return None
    except:
        return None

def calcular_vitalidad(perfil_texto):
    """Calcula un Puntaje de Vitalidad del 0 al 100 basado en el perfil."""
    
    vitality_score = 0
    age = 0
    bio_age = 0
    imc = 0.0
    phq9_score = 0
    
    # --- 1. Extracción de Datos ---
    match_age = re.search(r'Edad Real: (\d+)', perfil_texto)
    if match_age: age = int(match_age.group(1))
    
    match_bio = re.search(r'Edad Biológica Estimada: (\d+)', perfil_texto)
    if match_bio: bio_age = int(match_bio.group(1))

    match_imc = re.search(r'IMC: ([\d.]+)', perfil_texto)
    if match_imc: imc = float(match_imc.group(1))

    match_phq9 = re.search(r'Puntuación Total: (\d+)/27', perfil_texto)
    if match_phq9: phq9_score = int(match_phq9.group(1))

    # --- 2. CÁLCULO DE PUNTOS ---
    
    # I. EDAD BIOLÓGICA (Máx 30 pts)
    age_diff = age - bio_age
    if age_diff >= 3: vitality_score += 30
    elif age_diff > 0: vitality_score += 20
    elif age_diff == 0: vitality_score += 15
    elif age_diff <= -5: vitality_score += 5
    else: vitality_score += 10
        
    # II. BIENESTAR MENTAL (Máx 30 pts)
    if phq9_score <= 4: vitality_score += 30
    elif phq9_score <= 9: vitality_score += 20
    elif phq9_score <= 14: vitality_score += 10
    else: vitality_score += 5
        
    # III. RIESGOS CLÍNICOS (Máx 20 pts)
    risk_points = 20
    if "ALTO" in perfil_texto.upper() or "HPT" in perfil_texto.upper() or "HIPOGLUCEMIA" in perfil_texto.upper() or "BAJA" in perfil_texto.upper():
        risk_points -= 10 
    if "LÍMITE" in perfil_texto.upper() or "NORMAL-ALTA" in perfil_texto.upper() or "PRE-DIABETES" in perfil_texto.upper():
        risk_points -= 5 
        
    vitality_score += risk_points
    
    # IV. FITNESS / IMC (Máx 20 pts)
    if imc >= 18.5 and imc <= 24.9: vitality_score += 20
    elif (imc >= 25.0 and imc <= 29.9) or imc < 18.5: vitality_score += 10
    else: vitality_score += 5
        
    return min(100, max(0, vitality_score))

def validar_datos_criticos(perfil_texto):
    """Busca N/A o 0.0 en campos críticos del perfil y devuelve el error."""
    
    if "IMC: 0.0" in perfil_texto:
        return "Faltan los datos **Altura** o **Peso** en la pestaña **CUERPO**."

    if "Presión Arterial (S/D): N/A/N/A" in perfil_texto:
        return "Faltan los valores de **Presión Arterial** en la pestaña **EXÁMENES**."

    if "Glucosa: N/A" in perfil_texto or "Colesterol Total: N/A" in perfil_texto or "Triglicéridos: N/A" in perfil_texto:
        return "Faltan los valores de **Glucosa**, **Colesterol** o **Triglicéridos** en la pestaña **EXÁMENES**."

    match_phq9 = re.search(r'Puntuación Total: (\d+)/27', perfil_texto)
    if match_phq9 and int(match_phq9.group(1)) == 0 and "EDAD BIOLÓGICA" in perfil_texto:
        return "El cuestionario **SER INTERNO (PHQ-9)** en la pestaña de Bienestar no está completo."
    
    return None # No hay errores críticos


# --- 5. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL COMPLETO) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la respuesta del bot con lógica condicional para el menú,
    incluyendo la restricción de acceso por clave y la navegación por letra/comando.
    """
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    # === 1. RESTRICCIÓN DE ACCESO Y COMANDOS PERMITIDOS ===
    comandos_permitidos = ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER", "0", "1", "2", "3", "4", "P", "C", "O", "H", "D", "L", "E", "A", "I", "R", "F"]
    
    # Restricción general para cualquier mensaje que no sea un comando o no contenga la clave
    if CLIENT_SECRET_KEY not in mensaje_limpio and not any(cmd in mensaje_limpio for cmd in comandos_permitidos):
        return """
🚫 *Acceso Restringido - Fuente No Autorizada* 🚫
        
Para garantizar la calidad del servicio y proteger la API, Genesis solo procesa consultas enviadas *directamente desde la aplicación oficial Cuerpo Fiel*.
        
Por favor, descarga nuestra aplicación y usa el botón **'Preguntar a Genesis'** para iniciar la consulta.
"""
    
    # === 2. TRIAGE DE EMERGENCIA ===
    if any(keyword in mensaje_limpio for keyword in EMERGENCY_KEYWORDS):
        return """
🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴

El síntoma que describes es una **emergencia médica grave**.
Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana.
Tu vida es la prioridad.

🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**
"""
    
    # === 3. PROCESAMIENTO DE PERFIL DE SALUD (MÁXIMA PRIORIDAD) ===
    # Se busca la clave de inicio del perfil.
    if "PERFIL DE SALUD INTEGRAL INICIO" in mensaje_limpio:
        
        # --- VALIDACIÓN DE DATOS ANTES DE LLAMAR A GEMINI (GUÍA ACTIVA) ---
        error_validacion = validar_datos_criticos(mensaje_usuario)
        
        if error_validacion:
            return f"""
⚠️ *DATOS INCOMPLETOS - GUÍA ACTIVA* ⚠️

Para poder generar un análisis profesional, necesitamos que completes los siguientes datos críticos:

❌ *ERROR:* {error_validacion}
👉 *ACCIÓN:* Por favor, regresa a la aplicación **Cuerpo Fiel** y completa la información requerida en la pestaña indicada.

Cuando termines, vuelve a pegar y enviar el perfil aquí.
"""
        
        # Si la validación es exitosa, se procede al análisis con Gemini
        telefono_extraido = extraer_telefono(mensaje_usuario)
        vitality = calcular_vitalidad(mensaje_usuario) 
        
        if not telefono_extraido or "NO PROPORCIONADO" in mensaje_limpio:
            return "⚠️ *ATENCIÓN - PERFIL INCOMPLETO* ⚠️\nPara que el doctor pueda buscar tu perfil y darte una recomendación en el evento, es crucial el **número de teléfono**. Vuelve a la App y envía el perfil completo. 🙏"
        
        prompt_perfil = f"""
        {INSTRUCCION_SISTEMA}
        
        // --- INSTRUCCIÓN ESPECÍFICA DE TAREA ---
        
        CONTEXTO DE LA TAREA: El usuario ha pegado su perfil de salud integral generado por la aplicación Cuerpo Fiel. El identificador es: {telefono_extraido}.
        
        TAREA CRÍTICA:
        1. NO repitas el texto del perfil.
        2. Genera inmediatamente el **DIAGNÓSTICO PRESUNTIVO**.
        3. Formula una **RECETA DE ACCIÓN** que priorice el Remedio Natural más débil.
        4. Comienza la respuesta reconociendo y comentando el PUNTAJE DE VITALIDAD.
        5. Cierra con la pregunta interactiva y la referencia médica estándar.
        
        PUNTAJE DE VITALIDAD GENERADO: {vitality}/100.
        PERFIL INTEGRAL DEL PACIENTE: {mensaje_usuario}
        """
        
        try:
            response = model.generate_content(prompt_perfil)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (ANÁLISIS DE PERFIL): {e}")
            return "⚠️ Lo siento, no pude generar el análisis de perfil ahora. Intenta de nuevo."
        
    # === 4. LÓGICA CONDICIONAL DE MENÚ/SALIDA (CORREGIDA) ===
    # Se coloca aquí para que solo se active si NO es un perfil.
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER", "0"]:
        return MENU_SERVICIOS 

    # =========================================================
    # 5. PROCESAMIENTO DE COMANDOS DE MENÚ (MENOR PRIORIDAD)
    # =========================================================

    # --- NAVEGACIÓN PRINCIPAL ---
    if mensaje_limpio == "1": return SUB_MENU_SALUD
    if mensaje_limpio == "2": return SUB_MENU_BIENESTAR
    if mensaje_limpio == "3": return SUB_MENU_COMUNIDAD
    
    # --- ÁREA 1: SALUD FÍSICA (P, C, O) ---
    if mensaje_limpio == "P" or mensaje_limpio == "PROGRESO":
        return ("📈 *Puntaje de Vitalidad ⚡ (0-100)*\n\n" "Para calcular tu Puntaje de Vitalidad, necesito tu perfil más reciente.\n" "Vuelve a la aplicación **Cuerpo Fiel**, presiona el botón 'Conversar con Genesis' (o 'Enviar Análisis a Genesis') y pega el texto aquí.\n\n" "El puntaje mide tu equilibrio en los 8 Remedios Naturales. ¡Te sorprenderás!")
    if mensaje_limpio == "O" or mensaje_limpio == "PROTOCOLOS":
        return SUB_MENU_PROTOCOLOS
    if mensaje_limpio == "C" or mensaje_limpio == "CONSULTA":
        return ("🩺 *Consulta Clínica: Pregunta al instante*\n\n" "¡Listo/a! Escribe tu pregunta sobre cualquier síntoma, condición o necesidad de tratamiento natural. " "Recuerda que mis consejos se basan en la dieta saludable y los 8 Remedios Naturales.")

    # --- ÁREA 1.O: PROTOCOLOS CLÍNICOS (H, D, L) ---
    if mensaje_limpio == "H" or mensaje_limpio == "HTA":
        tema = "Hipertensión Arterial (HTA)"
        prompt_protocolo = f"{INSTRUCCION_SISTEMA} TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* detallada para el manejo de {tema} enfocada en el estilo de vida (8 Remedios Naturales). Responde al grano, manteniendo el tono profesional."
        try:
            response = model.generate_content(prompt_protocolo)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return f"⚠️ Lo siento, no pude generar el Protocolo para {tema} ahora."
            
    if mensaje_limpio == "D" or mensaje_limpio == "DIABETES":
        tema = "Diabetes Mellitus Tipo 2 (DM2)"
        prompt_protocolo = f"{INSTRUCCION_SISTEMA} TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* detallada para el manejo de {tema} enfocada en el estilo de vida (8 Remedios Naturales). Responde al grano, manteniendo el tono profesional."
        try:
            response = model.generate_content(prompt_protocolo)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return f"⚠️ Lo siento, no pude generar el Protocolo para {tema} ahora."

    if mensaje_limpio == "L" or mensaje_limpio == "LIPIDOS":
        tema = "Dislipidemia (Colesterol/Triglicéridos) y la Salud Cardiovascular"
        prompt_protocolo = f"{INSTRUCCION_SISTEMA} TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* detallada para el manejo de {tema} enfocada en el estilo de vida (8 Remedios Naturales). Responde al grano, manteniendo el tono profesional."
        try:
            response = model.generate_content(prompt_protocolo)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return f"⚠️ Lo siento, no pude generar el Protocolo para {tema} ahora."

    # --- ÁREA 2: BIENESTAR (P, E, A) ---
    if mensaje_limpio == "P" or mensaje_limpio == "PSICOLÓGICO":
        return ("🧠 *Apoyo Psicológico: Paz Mental*\n\n" "Tu salud emocional es vital. Para iniciar una sesión de apoyo confidencial para manejar " "estrés o ansiedad, comunícate al:\n" f"📲 *Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}*\n\n" "«El reposo mental es una parte esencial de la adoración a Dios.»")
    if mensaje_limpio == "E" or mensaje_limpio == "EJERCICIO":
        return """
💪 *¡Bienvenido al Reto Poder 8!* 🚀

Este es un módulo de entrenamiento innovador que equilibra los *8 Remedios Naturales*.

🔥 *¿Cómo te gustaría empezar?*
   A. *Mi Rutina:* Describe tus metas de *fitness* (ej: 'quiero ganar músculo y tener más energía').
   B. *Conciencia Corporal:* ¿Cómo evaluas tu fatiga post-entreno de hoy (1-5)?
   C. *Comunidad:* ¡Quiero unirme al desafío de puntos de vitalidad!
"""
    if mensaje_limpio == "A" or mensaje_limpio == "EVALUACIÓN RÁPIDA":
        return ("✅ *Evaluación Rápida de Hábitos*\n\n" "Responde a las siguientes 3 preguntas para una guía más precisa:\n" "1. ¿En promedio, cuántos vasos de agua simple consumes al día?\n" "2. ¿Cuántas veces a la semana realizas ejercicio moderado a intenso (mínimo 30 min)?\n" "3. ¿Qué tan satisfecho/a estás con tu descanso nocturno (1-5)?\n\n" "*(Responde con los 3 números: ej. 8, 3, 4)*")

    # --- ÁREA 3: COMUNIDAD (I, R, F) ---
    if mensaje_limpio == "I" or mensaje_limpio == "IGLESIAS":
        return ("📍 *Comunidad de Fe: Encuentra tu Hogar*\n\n" "Para un crecimiento integral, es vital congregarse. Usa el siguiente enlace para buscar " "tu iglesia Adventista o Centro de Vida Sana más cercano:\n" f"🔗 *[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})*")
    if mensaje_limpio == "R" or mensaje_limpio == "RADIO":
        return ("📻 *Voz de Esperanza: Inspiración Diaria*\n\n" "Conéctate a mensajes que transforman tu vida y fortalecen tu fe. Escucha nuestra programación:\n" f"🔗 *[AWR Colombia]({RADIO_LINK})*")
    if mensaje_limpio == "F" or mensaje_limpio == "FE":
        pass # Continúa al try/except para el procesamiento (Consejería Rápida)
        
    # --- ÁREA 4: REMEDIOS NATURALES ---
    if mensaje_limpio == "4" or "REMEDIOS NATURALES" in mensaje_limpio:
        return """
✨ *Los 8 Pilares de la Salud* ✨

¡Me encanta tu interés por la *restauración completa*! Estos son los *8 Remedios Naturales* que promueven la sanidad integral:

1.  *🌿 Nutrición*
2.  *💧 Agua*
3.  *☀️ Luz Solar*
4.  *🏃 Ejercicio*
5.  *🌬️ Aire Puro*
6.  *😴 Descanso*
7.  *🧘 Templanza*
8.  *🙏 Esperanza en Dios*

*¿Sobre cuál de estos 8 te gustaría recibir un consejo práctico y bíblico? Responde con el nombre del pilar.*
"""
    
    # --- LÓGICA DE DETALLE DE LOS 8 REMEDIOS NATURALES (OPCIÓN 4) ---
    keywords_pilares = ["NUTRICIÓN", "AGUA", "LUZ SOLAR", "EJERCICIO", "AIRE PURO", "DESCANSO", "TEMPLANZA", "ESPERANZA EN DIOS"]
    if any(k in mensaje_limpio for k in keywords_pilares):
        prompt_pilar = f"""
        {INSTRUCCION_SISTEMA} CONTEXTO: El usuario pide detalles sobre uno de los 8 Remedios Naturales.
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". Genera una explicación profunda y concisa de cómo aplicar ese pilar de salud. Cierra con un versículo bíblico ALTAMENTE RELEVANTE a ese pilar. Responde al grano.
        """
        try:
            response = model.generate_content(prompt_pilar)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return "⚠️ Lo siento, tengo problemas para generar el consejo del pilar. Vuelve a intentarlo o pregunta algo general."

    # === 6. LÓGICA DE PLAN NUTRICIONAL (Protegido por Código) ===
    if "PLAN NUTRICIONAL SOLICITADO" in mensaje_limpio:
        
        match_code = re.search(r'(IASD2025|IASD\s*2025)', mensaje_limpio) 
        
        if not match_code:
            return "❌ *ACCESO DENEGADO:* Por favor, solicita el código *IASD2025* al Director de Salud."
        
        prompt_nutricional = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO: El usuario está solicitando un Plan Nutricional de 7 días. El perfil de salud completo está adjunto al mensaje.
        
        TAREA CRÍTICA:
        1. Genera un Plan Nutricional Vegano/Adventista de 7 días adaptado al perfil de salud que se adjunta. 
        2. El plan debe ser estricto en la eliminación de carnes, lácteos, azúcar refinado y cafeína.
        3. Debe ser fácil de seguir y resaltar alimentos que ayuden a la condición más débil del usuario.
        4. Provee una lista de compras básica.
        5. Cierra con un versículo y la referencia médica.
        
        PERFIL DE SALUD: {mensaje_usuario}
        """
        try:
            response = model.generate_content(prompt_nutricional)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (PLAN NUTRICIONAL): {e}")
            return "⚠️ Lo siento, no pude generar el Plan Nutricional. Revisa que hayas pegado el Perfil de Salud completo."

    # === 7. LÓGICA FINAL (PREGUNTA ABIERTA O ERROR) ===
    try:
        # Cualquier pregunta que no haya caído en los comandos específicos
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
# 8. RUTAS WEB Y DE WHATSAPP (Mantenidas)
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
