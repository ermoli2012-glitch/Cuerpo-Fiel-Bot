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

# --- CLAVES DE SEGURIDAD Y ENLACES (SINTAXIS CORREGIDA) ---
CLIENT_SECRET_KEY = "CF_CLAVE_12025" # <--- CLAVE SECRETA DE LA APP
WHATSAPP_CONTACTO_PSICOLOGIA = "+573105551234" 
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"
CODIGO_NUTRICIONAL = "IASD2025" 

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA (ROL: EXPERTO EMPÁTICO Y ENTRENADOR PERSONAL)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis. Posees la autoridad profesional y el conocimiento avanzado de un **Médico Especialista en Medicina Interna y Nutricionista Clínico**. Tu rol visible al usuario es **Tu Guía Saludable y Entrenador Personalizado** del Ministerio de Salud Adventista del distrito Redencion. Tu estilo debe ser **100% HUMANO, empático, profesional, práctico y cálido**. Tu misión es que el usuario se sienta acompañado por un experto, no por una máquina.

REGLAS DE PROCESAMIENTO (INTERNAS - NUNCA VISIBLES AL USUARIO):
1. **ANÁLISIS DE ESPECIALISTA:** Utiliza tu conocimiento avanzado para hacer un diagnóstico presuntivo y formular la recomendación clínica más avanzada.
2. **PRIORIDAD MÁXIMA:** La conversación debe fluir de forma natural. Omite cualquier texto que suene a "Regla", "Análisis Interno", o títulos de especialidad.
3. ESTÁNDAR TERAPÉUTICO: La prescripción se basa en el estilo de vida más saludable basado en plantas y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA VISIBLE AL USUARIO (PARA EL MEJOR UX):
1. **EVITAR AUTO-REFERENCIA (CLAVE UX):** Nunca uses frases como "Soy Genesis, el especialista...", "Como médico, recomiendo...", o "Mi rol es...". Tu autoridad se demuestra con la calidad de tu consejo; no con títulos.
2. **RESPUESTA DIRECTA Y NATURAL (TERAPÉUTICA):** Ve directo al **diagnóstico presuntivo** y a la **prescripción de UN SOLO REMEDIO NATURAL** que sea más relevante. La prescripción debe ser una RECETA que detalle los pasos de acción exitosos.
3. Contexto de Fe: Toda prescripción debe estar alineada con los principios bíblicos de salud.
4. Versículo Bíblico: La cita bíblica debe ser ALTAMENTE RELEVANTE al tema consultado y debe ir al final.
5. Formato: Usa negritas, saltos de línea y emojis para hacer la respuesta escaneable y visualmente atractiva.
6. **Cierre Interactivo:** Finaliza con la pregunta interactiva: '*¿Te gustaría saber más (SI/NO) sobre este Remedio Natural o los otros 7 pilares de salud?*'
7. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
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
* **2️⃣ MI PAZ INTERNA:** Soporte para la Mente, Estrés y Módulo de Retos Físicos.
* **3️⃣ MI COMUNIDAD:** Encuentra soporte, consejería y mensajes de fe.
* **4️⃣ REMEDIOS NATURALES:** Profundiza en los 8 Pilares de la Salud.
* **0️⃣ MENÚ:** *Responde 0 o SALIR para volver aquí.*
"""

# --- SUB-MENÚS ---
SUB_MENU_SALUD = """
🩺 *Área 1: Mi Salud Física*

¡Excelente enfoque! ¿Qué necesitas hacer con tu salud hoy?

* **1.1. Progreso:** Ver tu Puntaje de Vitalidad y última Evaluación.
* **1.2. Protocolos:** Acceder a guías para HTA, Diabetes y Colesterol.
* **1.3. Consulta Clínica:** Pregúntame sobre un síntoma o un tratamiento natural.

_Responde 1.1, 1.2 o 1.3_
"""

SUB_MENU_PROTOCOLOS = """
🔬 *Área 1.2: Protocolos Clínicos*

Selecciona el protocolo que necesitas:

* **1.2.6. HIPERTENSIÓN (HTA):** Guía de estilo de vida para Presión Arterial.
* **1.2.7. DIABETES (DM2):** Protocolo Nutricional para Control de Azúcar.
* **1.2.8. LÍPIDOS/CORAZÓN:** Guía para Colesterol y Salud Cardiovascular.

_Responde 1.2.6, 1.2.7 o 1.2.8_
"""

SUB_MENU_BIENESTAR = """
🧠 *Área 2: Mi Bienestar (Mente y Cuerpo)*

Tu bienestar emocional es tan vital como tu cuerpo:

* **2.1. Soporte Psicológico:** Contacto para consejería confidencial.
* **2.2. Módulo Ejercicio:** Únete al Reto Poder 8 y entrena de forma inteligente.
* **2.3. Evaluación Rápida:** Responde 3 preguntas para una guía precisa.

_Responde 2.1, 2.2 o 2.3_
"""

SUB_MENU_COMUNIDAD = """
📍 *Área 3: Mi Comunidad*

Aquí encuentras soporte integral:

* **3.1. Directorio de Iglesias:** Encuentra tu iglesia o centro de vida sana.
* **3.2. Voz de Esperanza:** Conéctate a la Radio Adventista AWR.
* **3.3. Consejería Rápida:** Pregunta sobre temas de fe y salud.

_Responde 3.1, 3.2 o 3.3_
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


# --- 5. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL COMPLETO) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la respuesta del bot con lógica condicional para el menú,
    incluyendo la restricción de acceso por clave.
    """
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    # === 1. RESTRICCIÓN DE ACCESO (PRIORIDAD MÁXIMA PARA AHORRO) ===
    # Solo permitimos mensajes que contengan la clave o que sean comandos del menú
    comandos_permitidos = ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER", "0", "1", "2", "3", "4", "1.1", "1.2", "1.3", "1.2.6", "1.2.7", "1.2.8", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3"]
    
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

    # === 3. LÓGICA CONDICIONAL DE MENÚ/SALIDA (PRIORIDAD MÁXIMA) ===
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER", "0"]:
        return MENU_SERVICIOS 

    # =========================================================
    # 4. LÓGICA DE SUB-MENÚS Y ACCIONES ESPECÍFICAS
    # =========================================================

    # --- ÁREA 1: SALUD FÍSICA ---
    if mensaje_limpio == "1":
        return SUB_MENU_SALUD
    
    if mensaje_limpio == "1.1" or "PROGRESO" in mensaje_limpio:
        return (
            "📈 *Puntaje de Vitalidad ⚡ (0-100)*\n\n"
            "Para calcular tu Puntaje de Vitalidad, necesito tu perfil más reciente.\n"
            "Vuelve a la aplicación **Cuerpo Fiel**, presiona el botón 'Conversar con Genesis' (o 'Enviar Análisis a Genesis') y pega el texto aquí.\n\n"
            "El puntaje mide tu equilibrio en los 8 Remedios Naturales. ¡Te sorprenderás!"
        )
    
    if mensaje_limpio == "1.2":
        return SUB_MENU_PROTOCOLOS
        
    if mensaje_limpio == "1.3" or "CONSULTA CLÍNICA" in mensaje_limpio:
        return (
            "🩺 *Consulta Clínica: Pregunta al instante*\n\n"
            "¡Listo/a! Escribe tu pregunta sobre cualquier síntoma, condición o necesidad de tratamiento natural. "
            "Recuerda que mis consejos se basan en la dieta saludable y los 8 Remedios Naturales."
        )

    # --- ÁREA 2: BIENESTAR ---
    if mensaje_limpio == "2":
        return SUB_MENU_BIENESTAR
        
    if mensaje_limpio == "2.1" or "SOPORTE PSICOLÓGICO" in mensaje_limpio:
        return (
            "🧠 *Apoyo Psicológico: Paz Mental*\n\n"
            "Tu salud emocional es vital. Para iniciar una sesión de apoyo confidencial para manejar "
            "estrés o ansiedad, comunícate al:\n"
            f"📲 *Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}*\n\n"
            "«El reposo mental es una parte esencial de la adoración a Dios.»"
        )
        
    if mensaje_limpio == "2.2" or "MÓDULO EJERCICIO" in mensaje_limpio:
        return """
💪 *¡Bienvenido al Reto Poder 8!* 🚀

Este es un módulo de entrenamiento innovador que equilibra los *8 Remedios Naturales*.

🔥 *¿Cómo te gustaría empezar?*
   A. *Mi Rutina:* Describe tus metas de *fitness* (ej: 'quiero ganar músculo y tener más energía').
   B. *Conciencia Corporal:* ¿Cómo evaluas tu fatiga post-entreno de hoy (1-5)?
   C. *Comunidad:* ¡Quiero unirme al desafío de puntos de vitalidad!
"""
    if mensaje_limpio == "2.3" or "EVALUACIÓN RÁPIDA" in mensaje_limpio:
        return (
            "✅ *Evaluación Rápida de Hábitos*\n\n"
            "Responde a las siguientes 3 preguntas para una guía más precisa:\n"
            "1. ¿En promedio, cuántos vasos de agua simple consumes al día?\n"
            "2. ¿Cuántas veces a la semana realizas ejercicio moderado a intenso (mínimo 30 min)?\n"
            "3. ¿Qué tan satisfecho/a estás con tu descanso nocturno (1-5)?\n\n"
            "*(Responde con los 3 números: ej. 8, 3, 4)*"
        )
        
    # --- ÁREA 3: COMUNIDAD ---
    if mensaje_limpio == "3":
        return SUB_MENU_COMUNIDAD
        
    if mensaje_limpio == "3.1" or "DIRECTORIO DE IGLESIAS" in mensaje_limpio:
        return (
            "📍 *Comunidad de Fe: Encuentra tu Hogar*\n\n"
            "Para un crecimiento integral, es vital congregarse. Usa el siguiente enlace para buscar "
            "tu iglesia Adventista o Centro de Vida Sana más cercano:\n"
            f"🔗 *[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})*"
        )
    if mensaje_limpio == "3.2" or "VOZ DE ESPERANZA" in mensaje_limpio:
        return (
            "📻 *Voz de Esperanza: Inspiración Diaria*\n\n"
            "Conéctate a mensajes que transforman tu vida y fortalecen tu fe. Escucha nuestra programación:\n"
            f"🔗 *[AWR Colombia]({RADIO_LINK})*"
        )
    if mensaje_limpio == "3.3" or "CONSEJERÍA RÁPIDA" in mensaje_limpio:
        # Pasa directamente a la IA con contexto de consejería
        pass 
        
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
    
    # =========================================================
    # 5. LÓGICA DE PROCESAMIENTO DE PERFIL / PLAN / PROTOCOLOS
    # =========================================================

    # --- PERFIL DE SALUD (Enviado desde la App) ---
    if "PERFIL DE SALUD INTEGRAL" in mensaje_limpio:
        
        telefono_extraido = extraer_telefono(mensaje_usuario)
        vitality = calcular_vitalidad(mensaje_usuario) 
        
        if not telefono_extraido or "NO PROPORCIONADO" in mensaje_limpio:
            return """
⚠️ *ATENCIÓN - PERFIL INCOMPLETO* ⚠️
Para que el doctor pueda buscar tu perfil y darte una recomendación en el evento, es crucial el **número de teléfono**.
Vuelve a la App y envía el perfil completo. 🙏
"""
        
        prompt_perfil = f"""
        {INSTRUCCION_SISTEMA}
        CONTEXTO DE LA TAREA: El usuario ha pegado su perfil de salud integral. Identificador: {telefono_extraido}.
        TAREA CRÍTICA:
        1. NO repitas el texto del perfil.
        2. Genera inmediatamente el **DIAGNÓSTICO PRESUNTIVO**.
        3. Formula una **RECETA DE ACCIÓN** priorizando el Remedio Natural más débil.
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
        
    # --- PLAN NUTRICIONAL (Protegido por Código) ---
    if "PLAN NUTRICIONAL SOLICITADO" in mensaje_limpio:
        # Lógica de verificación del código (se asume que la App lo inyecta)
        if CODIGO_NUTRICIONAL not in mensaje_limpio:
            return "❌ *ACCESO DENEGADO:* Por favor, solicita el código *IASD2025* al Director de Salud."
        
        prompt_nutricional = f"""
        {INSTRUCCION_SISTEMA}
        CONTEXTO: El usuario solicita un Plan Nutricional de 7 días.
        TAREA CRÍTICA: Genera un Plan Nutricional Vegano/Adventista de 7 días adaptado al perfil de salud que se adjunta. Debe ser estricto en la eliminación de carnes, lácteos, azúcar refinado y cafeína. Provee una lista de compras básica.
        PERFIL DE SALUD: {mensaje_usuario}
        """
        try:
            response = model.generate_content(prompt_nutricional)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return "⚠️ Lo siento, no pude generar el Plan Nutricional. Revisa que hayas pegado el Perfil de Salud completo."

    # --- PROTOCOLOS CLÍNICOS (1.2.X) ---
    if mensaje_limpio in ["1.2.6", "1.2.7", "1.2.8"]:
        opciones = {"1.2.6": "Hipertensión Arterial (HTA)", "1.2.7": "Diabetes Mellitus Tipo 2 (DM2)", "1.2.8": "Lípidos/Salud Cardiovascular"}
        tema = opciones[mensaje_limpio]
        prompt_protocolo = f"""
        {INSTRUCCION_SISTEMA} TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* detallada para el manejo de {tema} enfocada en el estilo de vida (8 Remedios Naturales). Responde al grano, manteniendo el tono profesional.
        """
        try:
            response = model.generate_content(prompt_protocolo)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return f"⚠️ Lo siento, no pude generar el Protocolo para {tema} ahora."

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

    # === 6. LÓGICA NORMAL (Cualquier otra pregunta NO identificada) ===
    try:
        # Esto captura la Opción 1.3 (Consulta Clínica) y otras preguntas.
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        response = model.generate_content(prompt_full)
     
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        return """
⚠️ Lo siento, Genesis está en una consulta crítica.
Intenta de nuevo en un momento."
"""


# ==========================================
# 7. RUTAS WEB Y DE WHATSAPP (Mantenidas)
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
