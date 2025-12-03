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
        
    # === 3. LÓGICA INTERACTIVA POR NÚMERO (OPCIONES DEL MENÚ) ===
    
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

    # === 4. LÓGICA DE SUB-MENÚ DEL MÓDULO 5 (RESPUESTAS A B Y C) ===

    # A. RUTINA PERSONALIZADA (Generado por IA)
    if mensaje_limpio in ["A", "MI RUTINA", "QUIERO GANAR MASA MSUCULAR"]:
        prompt_rutina = f"""
        {INSTRUCCION_SISTEMA}
        
        TAREA ESPECÍFICA: Genera un plan de ejercicio de 7 días (Microciclo) para el usuario. El objetivo es {mensaje_usuario} (ganar masa muscular o lo que el usuario haya escrito).
        
        REGLAS DE RUTINA:
        1. Debe basarse en los principios de salud total Adventista (Ejercicio como uno de los 8 Remedios).
        2. Debe incluir un día de descanso o actividad muy ligera (Reposo).
        3. Usa un tono motivador y juvenil.
        4. Presenta la rutina en un formato de tabla o lista fácil de leer (Día, Foco, Ejercicio).
        """
        try:
            response = model.generate_content(prompt_rutina)
            texto = response.text.replace('**', '*').replace('__', '_')
            return texto
        except Exception as e:
            print(f"❌ ERROR GEMINI (RUTINA): {e}")
            return "⚠️ Lo siento, no puedo generar tu rutina ahora. Intenta de nuevo describiendo tu objetivo."

    # B. CONCIENCIA CORPORAL (Respuesta preformateada)
    if mensaje_limpio in ["B", "CONCIENCIA CORPORAL", "FATIGA"]:
        return (
            "📊 **¡Excelente! Vamos a escanear tu cuerpo.**\n\n"
            "Para darnos *feedback* preciso, dime lo siguiente:\n"
            "1. **Nivel de Fatiga (1-5):** (1=Cero cansancio, 5=Totalmente agotado)\n"
            "2. **Conexión Mente-Músculo (1-5):** (1=No sentí el músculo, 5=Sentí cada contracción)\n\n"
            "Ejemplo de respuesta: *Fatiga 3, Mente 5*."
        )

    # C. COMUNIDAD / DESAFÍO (Respuesta preformateada)
    if mensaje_limpio in ["C", "COMUNIDAD", "DESAFÍO", "PUNTOS DE VITALIDAD"]:
        return (
            "🤝 **¡Únete al Desafío Comunitario Poder 8!**\n\n"
            "Ganarás Puntos de Vitalidad no solo por el gimnasio, sino por registrar:\n"
            "* Horas de **Descanso** (Reposo)\n"
            "* Vasos de **Agua**\n"
            "* Momentos de **Conexión** (Oración/Meditación)\n\n"
            "Para unirte al grupo de Telegram y empezar a sumar puntos, escribe **'QUIERO COMUNIDAD'**."
        )

    # === 5. LÓGICA DE REGLA AUTOMATIZADA (Búsqueda por palabras clave sin el menú) ===
    
    # ... (Resto de la lógica de respuestas por palabras clave y LÓGICA NORMAL omitido por brevedad) ...
    # (Asegúrate de que esta lógica esté en tu archivo)
    
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


    # === 6. LÓGICA NORMAL (IA CON JUICIO CLÍNICO) ===
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
