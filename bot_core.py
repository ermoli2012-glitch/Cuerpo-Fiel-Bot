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
WHATSAPP_CONTACTO_PSICOLOGIA = "proximamente"
RADIO_LINK = "https://www.awrcolombia.org/"
DIRECTORIO_IGLESIAS_LINK = "https://asoatlantico.org.co/es/distritos"

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA (ROL: MÉDICO INTERNISTA Y NUTRICIONISTA)
# =========================================================================
INSTRUCCION_SISTEMA = """
ROL INTERNO: Eres Genesis, con la autoridad profesional de un **Médico Especialista en Medicina Interna y Nutricionista Clínico**. Tu rol visible al usuario es **Tu Guía Saludable** del Ministerio de Salud Adventista del distrito Redencion. Tu estilo debe ser **100% HUMANO, empático, profesional, práctico y cálido**.

REGLAS DE PROCESAMIENTO (INTERNAS - NUNCA VISIBLES AL USUARIO):
1. **ANÁLISIS DE ESPECIALISTA:** Utiliza tu conocimiento de Medicina Interna y Nutrición para hacer un diagnóstico presuntivo y formular la recomendación clínica más avanzada.
2. **PRIORIDAD MÁXIMA:** La conversación debe fluir de forma natural. Omite cualquier texto que suene a "Regla", "Análisis Interno", o títulos de especialidad.
3. ESTÁNDAR TERAPÉUTICO: La prescripción se basa en el **estilo de vida más saludable basado en plantas** (con estricta recomendación de **restringir carnes, azúcar refinado y bebidas cafeinadas**) y los **8 Remedios Naturales**.

REGLAS DE RESPUESTA VISIBLE AL USUARIO:
1. **RESPUESTA DIRECTA Y NATURAL (TERAPÉUTICA):** Ve directo al **diagnóstico presuntivo** (sin ser extenso) y a la **prescripción de UN SOLO REMEDIO NATURAL** que sea más relevante. La prescripción debe ser una **RECETA** que detalle los procedimientos y pasos de acción exitosos.
2. Contexto de Fe: Toda prescripción debe estar alineada con los principios bíblicos de salud.
3. Versículo Bíblico: **La cita bíblica debe ser ALTAMENTE RELEVANTE** al tema consultado.
4. Formato: Usa negritas, saltos de línea y emojis.
5. **Cierre Interactivo:** Finaliza con la pregunta interactiva: *'¿Te gustaría saber más (SI/NO) sobre este Remedio Natural o los otros 7 pilares de salud?'*
6. Referencia Médica: En CADA respuesta, refuerza la necesidad de consultar al médico personal ("Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏").
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Para el Triage) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# --- MENÚ DE SERVICIOS (Texto para la activación con "hola" o "menu") ---
MENU_SERVICIOS = f"""
⭐ *¡HOLA! SOY GENESIS* ⭐
*Tu guía saludable del Distrito Redención Barranquilla.*

🤝 Estoy aquí para ayudarte a transformar tu vida con el **Estilo de Vida más Saludable**.

# =========================================================================
# 2. INSTRUCCIÓN MAESTRA Y MENÚS
# =========================================================================

# Asegúrate de usar las tres comillas al principio y al final
MENU_SERVICIOS = """
✨ *CENTRO DE BIENESTAR GÉNESIS* ✨
*Tu camino a la restauración integral*

Selecciona una de nuestras áreas especializadas:

🏥 **ÁREA CLÍNICA**
1️⃣ *Consulta:* Síntomas y tratamientos naturales.
6️⃣ *HTA:* Protocolo de Presión Arterial.
7️⃣ *Diabetes:* Control de azúcar.
8️⃣ *Corazón:* Salud Cardiovascular.

🌱 **ESTILO DE VIDA (8 REMEDIOS)**
0️⃣ *Evaluación:* Test rápido de vitalidad.
5️⃣ *Reto Poder 8:* Entrenamiento inteligente.

🙏 **APOYO Y COMUNIDAD**
2️⃣ *Psicología:* Estrés y Ansiedad.
3️⃣ *Iglesias:* Encuentra tu comunidad.
4️⃣ *Radio:* Inspiración 24/7.

*Responde con el número de la opción.*
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

    # === 3. LÓGICA DE ANÁLISIS DE PERFIL INTEGRAL (NUEVA PRIORIDAD) ===
    # Busca la palabra clave que colocamos en el frontend para activar el análisis completo.
    if "PERFIL DE SALUD INTEGRAL" in mensaje_limpio or "ANALIZA PERFIL INTEGRAL" in mensaje_limpio:
        prompt_perfil = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE LA TAREA: El usuario ha pegado su perfil de salud integral generado por la aplicación Cuerpo Fiel.
        
        TAREA CRÍTICA:
        1. **NO** repitas el menú de servicios.
        2. **NO** repitas el texto del perfil.
        3. Genera inmediatamente el **DIAGNÓSTICO PRESUNTIVO** (basado en IMC, PA y PHQ-9).
        4. Formula una **RECETA DE ACCIÓN** que priorice y explique **UN SOLO REMEDIO NATURAL** que aborde el problema más débil (ej., si el PHQ-9 es Severo, prioriza Esperanza en Dios o Descanso).
        5. Cierra con la pregunta interactiva y la referencia médica estándar.
        
        PERFIL INTEGRAL DEL PACIENTE:
        ---
        {mensaje_usuario}
        ---
        """
        
        try:
            response = model.generate_content(prompt_perfil)
            # Limpiamos el texto de Gemini
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (ANÁLISIS DE PERFIL): {e}")
            return "⚠️ Lo siento, no pude generar el análisis de perfil ahora. Intenta de nuevo."
        
    # === 4. LÓGICA DE PROFUNDIZACIÓN: SÍ/NO Y LISTA DE REMEDIOS (SOLUCIÓN AL BUCLÉ DE "SÍ") ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES", "SI"] 
    keywords_no_info = ["NO", "NO GRACIAS", "YA NO", "BASTA"] 
    
    # 4.1 Respuesta a "NO"
    if any(k in mensaje_limpio for k in keywords_no_info):
        return "¡Entendido! Siempre estoy aquí para cuando me necesites. No olvides que la salud es un viaje. 👋"

    # 4.2 Respuesta a "SÍ" / "SABER MÁS" (Muestra la lista)
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
        
    # === 5. LÓGICA DE DETALLE DE LOS 8 REMEDIOS NATURALES (RESPUESTA AL PILAR ESPECÍFICO) ===

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


    # === 6. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ PRINCIPAL) ===
    
    # 0. EVALUACIÓN DE HÁBITOS (Nueva Opción 0)
    if mensaje_limpio == "0" or "EVALUACIÓN" in mensaje_limpio:
        return (
            "✅ *Evaluación Rápida de Hábitos*\n\n"
            "Responde a las siguientes 3 preguntas para una guía más precisa:\n"
            "1. ¿En promedio, cuántos vasos de agua simple consumes al día?\n"
            "2. ¿Cuántas veces a la semana realizas ejercicio moderado a intenso (mínimo 30 min)?\n"
            "3. ¿Qué tan satisfecho/a estás con tu descanso nocturno (1-5)?\n\n"
            "*(Responde con los 3 números: ej. 8, 3, 4)*"
        )
        
    # 1. CONSULTA CLÍNICA
    if mensaje_limpio == "1":
        return (
            "🩺 *Consulta Clínica: Pregunta al instante*\n\n"
            "¡Listo/a! Escribe tu pregunta sobre cualquier síntoma, condición o necesidad de tratamiento natural. "
            "Recuerda que mis consejos se basan en la dieta saludable y los 8 Remedios Naturales."
        )

    # 2. APOYO PSICOLÓGICO
    if mensaje_limpio == "2":
        return (
            "🧠 *Apoyo Psicológico: Paz Mental*\n\n"
            "Tu salud emocional es vital. Para iniciar una sesión de apoyo confidencial para manejar "
            "estrés o ansiedad, comunícate al:\n"
            f"📲 *Teléfono: {WHATSAPP_CONTACTO_PSICOLOGIA}*\n\n"
            "«El reposo mental es una parte esencial de la adoración a Dios.»"
        )
        
    # 3. COMUNIDAD DE FE
    if mensaje_limpio == "3":
        return (
            "📍 *Comunidad de Fe: Encuentra tu Hogar*\n\n"
            "Para un crecimiento integral, es vital congregarse. Usa el siguiente enlace para buscar "
            "tu iglesia Adventista o Centro de Vida Sana más cercano:\n"
            f"🔗 *[Directorio de Iglesias]({DIRECTORIO_IGLESIAS_LINK})*"
        )
        
    # 4. RADIO ADVENTISTA
    if mensaje_limpio == "4":
        return (
            "📻 *Voz de Esperanza: Inspiración Diaria*\n\n"
            "Conéctate a mensajes que transforman tu vida y fortalecen tu fe. Escucha nuestra programación:\n"
            f"🔗 *[AWR Colombia]({RADIO_LINK})*"
        )
        
    # 5. MÓDULO EJERCICIO: PODER 8 (Entrada)
    if mensaje_limpio == "5":
        return """
💪 *¡Bienvenido al Reto Poder 8!* 🚀

Este es un módulo de entrenamiento innovador que equilibra los *8 Remedios Naturales*.

🧠 *Inteligencia Viral:* Ajustamos tu rutina según tu *conexión mental-músculo* y tu *ritmo de reposo sabático*.

🔥 *¿Cómo te gustaría empezar?*
   A. *Mi Rutina:* Describe tus metas de *fitness* (ej: 'quiero ganar músculo y tener más energía').
   B. *Conciencia Corporal:* ¿Cómo evaluas tu fatiga post-entreno de hoy (1-5)?
   C. *Comunidad:* ¡Quiero unirme al desafío de puntos de vitalidad!
"""
    # 6, 7, 8: MÓDULOS DE ENFERMEDADES PREVALENTES (ESPECIALIZACIÓN CLÍNICA)
    
    # 6. HIPERTENSIÓN (HTA)
    if mensaje_limpio == "6":
        prompt_hta = f"""
        {INSTRUCCION_SISTEMA}
        TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* para el manejo de la Hipertensión Arterial (HTA). 
        1. Explica brevemente la relación de la HTA con el estilo de vida.
        2. Provee un protocolo de acción concentrado en los Remedios Naturales (principalmente Dieta, Ejercicio, Agua). 
        3. El consejo debe incluir la meta de reducción de sodio y la importancia de alimentos integrales.
        4. Cierra con versículo bíblico relevante.
        Responde al grano.
        """
        try:
            response = model.generate_content(prompt_hta)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return "⚠️ Lo siento, no pude generar el Protocolo HTA ahora."
            
    # 7. DIABETES (DM2)
    if mensaje_limpio == "7":
        prompt_dm2 = f"""
        {INSTRUCCION_SISTEMA}
        TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* para el manejo de la Diabetes Mellitus Tipo 2 (DM2). 
        1. Explica brevemente el rol de la resistencia a la insulina.
        2. Provee un protocolo de acción concentrado en los Remedios Naturales (principalmente Nutrición y Ejercicio). 
        3. El consejo debe incluir la gestión del índice glucémico y la importancia de la fibra dietética.
        4. Cierra con versículo bíblico relevante.
        Responde al grano.
        """
        try:
            response = model.generate_content(prompt_dm2)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return "⚠️ Lo siento, no pude generar el Protocolo DM2 ahora."
            
    # 8. LÍPIDOS/CORAZÓN
    if mensaje_limpio == "8":
        prompt_corazon = f"""
        {INSTRUCCION_SISTEMA}
        TAREA ESPECÍFICA: Eres Médico Internista y Nutricionista. Genera una *RECETA* para el manejo de la Dislipidemia (Colesterol/Triglicéridos) y la Salud Cardiovascular. 
        1. Explica la importancia de la salud endotelial.
        2. Provee un protocolo de acción concentrado en los Remedios Naturales (principalmente Nutrición para lípidos y Ejercicio). 
        3. El consejo debe incluir la eliminación de grasas saturadas y el aumento de fibra soluble (avena, legumbres).
        4. Cierra con versículo bíblico relevante.
        Responde al grano.
        """
        try:
            response = model.generate_content(prompt_corazon)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            return "⚠️ Lo siento, no pude generar el Protocolo Cardiovascular ahora."


    # === 7. LÓGICA DE SUB-MENÚ DEL MÓDULO 5 (RESPUESTAS A B Y C) ===
    
    # Palabras clave que indican una interacción continua con el Módulo 5 (Reto Poder 8)
    keywords_modulo_5 = ["MI RUTINA", "CONCIENCIA CORPORAL", "COMUNIDAD", "FATIGA", "MENTE", "MÚSCULO", "FUERZA", "EJERCICIO"]
    
    # Si el mensaje es una de las letras de la opción, o una pregunta detallada DENTRO del contexto del Reto Poder 8
    if mensaje_limpio in ["A", "B", "C"] or any(k in mensaje_limpio for k in keywords_modulo_5):
        
        # PROMPT DE DELEGACIÓN A GEMINI PARA RESPUESTA CONTEXTUAL
        prompt_sub_menu = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE CONVERSACIÓN: El usuario está dentro del *Módulo de Ejercicio Reto Poder 8*. 
        
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". 
        
        * Si el usuario pide *Rutina (A)* o metas (ej: 'ganar masa muscular'), genera un plan de 7 días con un enfoque Adventista (incluyendo el Reposo).
        * Si el usuario pide *Conciencia Corporal (B)* o da su *feedback* (ej: 'Fatiga 3'), analiza su estado y sugiere un ajuste simple para la siguiente sesión, reforzando la salud integral.
        * Si el usuario pide *Comunidad (C)*, dale la respuesta de unirse al grupo de Telegram (o el canal de comunicación que decidas).
        
        Responde al grano, manteniendo el tono profesional y el enfoque Poder 8.
        """
        
        try:
            response = model.generate_content(prompt_sub_menu)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (RESPUESTA MÓDULO 5): {e}")
            return "⚠️ Lo siento, no puedo generar esa respuesta ahora. Intenta de nuevo describiendo tu objetivo."

    # === 8. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
    try:
        # Si el mensaje pasa todas las lógicas anteriores, es una pregunta de salud
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
# 9. RUTAS WEB Y DE WHATSAPP (Sin cambios)
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
