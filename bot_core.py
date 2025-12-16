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
CLIENT_SECRET_KEY = "CF_CLAVE_12025" // <--- CLAVE SECRETA DE LA APP
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

# --- MENÚ DE SERVICIOS ---
MENU_SERVICIOS = f"""
⭐ *¡HOLA! SOY GENESIS* ⭐
*Tu guía saludable del Distrito Redención.*

🤝 Estoy aquí para ayudarte a transformar tu vida con el **Estilo de Vida más Saludable**.

----------------------------------------
* Selecciona una opción para empezar:*
----------------------------------------

* **0️⃣ EVALUACIÓN:** ¡Descubre tu punto de partida! (Preguntas rápidas sobre tus 8 Remedios).
* **1️⃣ CONSULTA CLÍNICA:** Pregúntame sobre cualquier síntoma o tratamiento natural.
* **2️⃣ APOYO PSICOLÓGICO:** ¿Necesitas ayuda con estrés, ansiedad o depresión?
* **3️⃣ COMUNIDAD DE FE:** Encuentra tu iglesia o centro de vida sana.
* **4️⃣ VOZ DE ESPERANZA:** Conéctate a la Radio Adventista AWR.
* **5️⃣ MÓDULO EJERCICIO:** ¡Únete al *Reto Poder 8* y entrena de forma inteligente!
* **6️⃣ HIPERTENSIÓN (HTA):** Protocolo de Estilo de Vida para Presión Arterial.
* **7️⃣ DIABETES (DM2):** Protocolo Nutricional para Control de Azúcar.
* **8️⃣ LÍPIDOS/CORAZÓN:** Protocolo para Colesterol y Salud Cardiovascular.
* **9️⃣ PROGRESO:** Muestra tu Puntaje de Vitalidad y compáralo con tu última evaluación.

*Responde solo con el número (ej: 0, 1, 6 o SALIR) para volver aquí.*
"""
# ==========================================
# 3. BASE DE DATOS Y FUNCIONES ADICIONALES
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


# --- 4. CEREBRO DE LA APLICACIÓN (FLUJO CONDICIONAL COMPLETO) ---
def consultar_gemini(celular, mensaje_usuario):
    """
    Gestiona la respuesta del bot con lógica condicional para el menú,
    incluyendo la restricción de acceso por clave.
    """
    mensaje_limpio = mensaje_usuario.strip().upper()
    
    # === 1. RESTRICCIÓN DE ACCESO (PRIORIDAD MÁXIMA PARA AHORRO) ===
    # Si el mensaje NO contiene la clave, ni es un comando de bienvenida, lo rechazamos.
    if CLIENT_SECRET_KEY not in mensaje_limpio and mensaje_limpio not in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER"]:
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
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR", "SALIR", "VOLVER"]:
        return MENU_SERVICIOS 

    # === 4. LÓGICA DE ANÁLISIS DE PERFIL INTEGRAL (INCLUYE PUNTAJE DE VITALIDAD) ===
    
    if "PERFIL DE SALUD INTEGRAL" in mensaje_limpio:
        
        telefono_extraido = extraer_telefono(mensaje_usuario)
        vitality = calcular_vitalidad(mensaje_usuario) 
        
        if not telefono_extraido or "NO PROPORCIONADO" in mensaje_limpio:
            return """
⚠️ *ATENCIÓN - PERFIL INCOMPLETO* ⚠️

Para que el doctor pueda buscar tu perfil y darte una recomendación en el evento, es crucial el **número de teléfono**.

Por favor, vuelve a la App de Cuerpo Fiel, ingresa tu número en la sección de Exámenes y envía el perfil completo. 🙏
"""
        
        prompt_perfil = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE LA TAREA: El usuario ha pegado su perfil de salud integral generado por la aplicación Cuerpo Fiel. El identificador es: {telefono_extraido}.
        
        TAREA CRÍTICA:
        1. NO repitas el menú de servicios.
        2. NO repitas el texto del perfil.
        3. Genera inmediatamente el **DIAGNÓSTICO PRESUNTIVO** (basado en IMC, PA y PHQ-9).
        4. Formula una **RECETA DE ACCIÓN** que priorice y explique **UN SOLO REMEDIO NATURAL** que aborde el problema más débil.
        5. **Comienza la respuesta reconociendo y comentando el PUNTAJE DE VITALIDAD.**
        6. Cierra con la pregunta interactiva y la referencia médica estándar.
        
        PUNTAJE DE VITALIDAD GENERADO: {vitality}/100.
        
        PERFIL INTEGRAL DEL PACIENTE:
        ---
        {mensaje_usuario}
        ---
        """
        
        try:
            response = model.generate_content(prompt_perfil)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (ANÁLISIS DE PERFIL): {e}")
            return "⚠️ Lo siento, no pude generar el análisis de perfil ahora. Intenta de nuevo."
        
    # === 4.1. LÓGICA DE PLAN NUTRICIONAL (PROTECCIÓN DE CÓDIGO) ===
    
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
        
        PERFIL DE SALUD:
        ---
        {mensaje_usuario}
        ---
        """
        try:
            response = model.generate_content(prompt_nutricional)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (PLAN NUTRICIONAL): {e}")
            return "⚠️ Lo siento, no pude generar el Plan Nutricional. Revisa que hayas pegado el Perfil de Salud completo."


    # === 5. LÓGICA DE PROFUNDIZACIÓN: SÍ/NO Y LISTA DE REMEDIOS ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES", "SI"] 
    keywords_no_info = ["NO", "NO GRACIAS", "YA NO", "BASTA"] 
    
    if any(k in mensaje_limpio for k in keywords_no_info):
        return "¡Entendido! Siempre estoy aquí para cuando me necesites. No olvides que la salud es un viaje. 👋"

    if any(k in mensaje_limpio for k in keywords_mas_info):
        return """
✨ *Los 8 Pilares de la Salud* ✨

¡Me encanta tu interés por la *restauración completa*! Estos son los *8 Remedios Naturales* que promueven la sanidad integral, tal como los enseñan las Escrituras:

1.  *🌿 Nutrición (Alimentos sanos)*
2.  *💧 Agua*
3.  *☀️ Luz Solar*
4.  *🏃 Ejercicio*
5.  *🌬️ Aire Puro*
6.  *😴 Descanso*
7.  *🧘 Templanza* (Moderación y Equilibrio)
8.  *🙏 Esperanza en Dios* (Confianza en el poder divino)

*¿Sobre cuál de estos 8 te gustaría recibir un consejo práctico y bíblico? Responde con el nombre del pilar.*
"""
        
    # === 6. LÓGICA DE DETALLE DE LOS 8 REMEDIOS NATURALES ===

    keywords_pilares = ["NUTRICIÓN", "AGUA", "LUZ SOLAR", "EJERCICIO", "AIRE PURO", "DESCANSO", "TEMPLANZA", "ESPERANZA EN DIOS"]
    
    if any(k in mensaje_limpio for k in keywords_pilares):
        
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


    # === 7. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ PRINCIPAL) ===
    
    if mensaje_limpio == "0" or "EVALUACIÓN" in mensaje_limpio:
        return ("✅ *Evaluación Rápida de Hábitos*\n\n" "Responde a las siguientes 3 preguntas para una guía más precisa:\n" "1. ¿En promedio, cuántos vasos de agua simple consumes al día?\n" "2. ¿Cuántas veces a la semana realizas ejercicio moderado a intenso (mínimo 30 min)?\n" "3. ¿Qué tan satisfecho/a estás con tu descanso nocturno (1-5)?\n\n" "*(Responde con los 3 números: ej. 8, 3, 4)*")
    if mensaje_limpio == "1":
        return ("🩺 *Consulta Clínica: Pregunta al instante*\n\n" "¡Listo/a! Escribe tu pregunta sobre cualquier síntoma, condición o necesidad de tratamiento natural. " "Recuerda que mis consejos se basan en la dieta saludable y los 8 Remedios Naturales.")
    if mensaje_limpio == "2":
        return ("🧠 *Apoyo Psicológico: Paz Mental*\n\n" "Tu salud emocional es vital. Para iniciar una sesión de apoyo confidencial para manejar " "estrés o ansiedad, comunícate al:\n" f"📲 *Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}*\n\n" "«El reposo mental es una parte esencial de la adoración a Dios.»")
    if mensaje_limpio == "3":
        return ("📍 *Comunidad de Fe: Encuentra tu Hogar*\n\n" "Para un crecimiento integral, es vital congregarse. Usa el siguiente enlace para buscar " "tu iglesia Adventista o Centro de Vida Sana más cercano:\n" f"🔗 *[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})*")
    if mensaje_limpio == "4":
        return ("📻 *Voz de Esperanza: Inspiración Diaria*\n\n" "Conéctate a mensajes que transforman tu vida y fortalecen tu fe. Escucha nuestra programación:\n" f"🔗 *[AWR Colombia]({RADIO_LINK})*")
    if mensaje_limpio == "5":
        return ("💪 *¡Bienvenido al Reto Poder 8!* 🚀\n\n" "Este es un módulo de entrenamiento innovador que equilibra los *8 Remedios Naturales*.\n\n" "🧠 *Inteligencia Viral:* Ajustamos tu rutina según tu *conexión mental-músculo* y tu *ritmo de reposo sabático*.\n\n" "🔥 *¿Cómo te gustaría empezar?*\n   A. *Mi Rutina:* Describe tus metas de *fitness* (ej: 'quiero ganar músculo y tener más energía').\n   B. *Conciencia Corporal:* ¿Cómo evaluas tu fatiga post-entreno de hoy (1-5)?\n   C. *Comunidad:* ¡Quiero unirme al desafío de puntos de vitalidad!")
    
    # === 8. LÓGICA NORMAL (Cualquier otra pregunta NO identificada) ===
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
# 9. RUTAS WEB Y DE WHATSAPP
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
