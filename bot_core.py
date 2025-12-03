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
... (Triage omitido) ...
"""

    # === 2. LÓGICA CONDICIONAL DE MENÚ/SALUDO ===
    if mensaje_limpio in ["HOLA", "HOLA.", "HOLA!", "MENU", "INICIO", "COMIENZO", "EMPEZAR"]:
        return MENU_SERVICIOS 
        
    # === 3. LÓGICA DE PROFUNDIZACIÓN: 8 REMEDIOS NATURALES (ALTA PRIORIDAD) ===

    keywords_mas_info = ["SABER MAS", "DIME MAS", "OTROS 7", "REMEDIOS NATURALES", "8 PILARES", "SI"] 
    
    if any(k in mensaje_limpio for k in keywords_mas_info):
        return """
✨ **Los 8 Pilares de la Salud** ✨

¡Me encanta tu interés por la **restauración completa**! Estos son los **8 Remedios Naturales** que promueven la sanidad integral, tal como los enseñan las Escrituras:
... (Lista de Remedios omitida) ...

*¿Sobre cuál de estos 8 te gustaría recibir un consejo práctico y bíblico? Responde con el nombre del pilar.*
"""
        
    # === 4. LÓGICA DE DETALLE DE LOS 8 REMEDIOS NATURALES (RESPUESTA AL PILAR ESPECÍFICO) ===

    keywords_pilares = ["NUTRICIÓN", "AGUA", "LUZ SOLAR", "EJERCICIO", "AIRE PURO", "DESCANSO", "TEMPLANZA", "ESPERANZA EN DIOS"]
    
    if any(k in mensaje_limpio for k in keywords_pilares):
        
        # PROMPT DE DELEGACIÓN A GEMINI PARA ENSEÑANZA ESPECÍFICA
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

    # ... (Opciones 2, 3, 4 omitidas por brevedad) ...
    
    # 5. MÓDULO EJERCICIO: PODER 8 (Entrada)
    if mensaje_limpio == "5":
        return """
💪 **¡Bienvenido al Reto Poder 8!** 🚀
... (Menú de Módulo 5 omitido) ...
"""

    # === 6. LÓGICA DE SUB-MENÚ DEL MÓDULO 5 (RESPUESTAS A B Y C) ===
    
    # ... (Lógica de Módulo 5 omitida por brevedad) ...
    keywords_modulo_5 = ["MI RUTINA", "CONCIENCIA CORPORAL", "COMUNIDAD", "FATIGA", "MENTE", "MÚSCULO", "FUERZA", "EJERCICIO"]
    
    # Si el mensaje es una de las letras de la opción, o una pregunta detallada DENTRO del contexto del Reto Poder 8
    if mensaje_limpio in ["A", "B", "C"] or any(k in mensaje_limpio for k in keywords_modulo_5):
        
        # PROMPT DE DELEGACIÓN A GEMINI PARA RESPUESTA CONTEXTUAL
        prompt_sub_menu = f"""
        {INSTRUCCION_SISTEMA}
        
        CONTEXTO DE CONVERSACIÓN: El usuario está dentro del **Módulo de Ejercicio Reto Poder 8**. 
        
        TAREA ESPECÍFICA: El usuario ha escrito: "{mensaje_usuario}". 
        ... (Instrucciones de generación de rutina omitidas) ...
        
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
    
    # ... (Lógica de contacto directo omitida por brevedad) ...

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
