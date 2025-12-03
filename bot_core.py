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
        return MENU_SERVICIOS 
        
    # === 3. LÓGICA DE PROFUNDIZACIÓN: 8 REMEDIOS NATURALES (NUEVA PRIORIDAD) ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES", "SI"] # Añadimos "SI"
    
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
        
        # PROMPT DELEGACIÓN A GEMINI PARA ENSEÑANZA ESPECÍFICA
        prompt_pilar = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE CONVERSACIÓN: El usuario está pidiendo detalles sobre uno de los 8 Remedios Naturales.
        
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". 
        
        1. Identifica el Remedio Natural solicitado (Nutrición, Agua, etc.).
        2. Genera un consejo práctico y una explicación concisa y motivadora sobre cómo aplicar ese pilar de salud.
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
    # ... (Resto de la lógica de sub-menús y palabras clave de contacto sigue aquí) ...
    # === 6. LÓGICA DE SUB-MENÚ DEL MÓDULO 5 (RESPUESTAS A B Y C) ===
    
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

    # === 7. LÓGICA DE REGLA AUTOMATIZADA (Búsqueda por palabras clave sin el menú) ===
    
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


    # === 8. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
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
