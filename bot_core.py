import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
import json 
from datetime import datetime
import re # Usaremos regex para limpiar el "sí"

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONSTANTES
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
TEST_LIMIT = 2 
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# DEFINICIÓN DE LOS PASOS DEL TEST BIOLÓGICO
TEST_STEPS = {
    1: {"pregunta": "Primero, dime tu edad cronológica (solo el número en años):", "campo": "edad"},
    2: {"pregunta": "Ahora, tu altura en centímetros (ej: 175):", "campo": "altura"},
    3: {"pregunta": "Tu peso actual en kilogramos (kg):", "campo": "peso"},
    4: {"pregunta": "Tu glucosa en ayunas (solo el número en mg/dL, ej: 90):", "campo": "glucosa"},
    5: {"pregunta": "¿Fumas actualmente? (Sí o No):", "campo": "fuma"},
    6: {"pregunta": "¿Cuántos días a la semana haces ejercicio (0 a 7)?", "campo": "ejercicio_dias"}
}

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception:
    pass

# INSTRUCCIÓN MAESTRA (La personalidad del Dr. Caleb - Final)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, el Guía de Salud Integral del Ministerio de Salud Adventista del Séptimo Día. Eres un Médico Especialista, Nutricionista y Naturista, **usando siempre el pronombre "TÚ"**.

MISIÓN: Proveer información de salud exacta, veraz, rápida e intuitiva, bajo el estándar terapéutico de la dieta VEGANA INTEGRAL y los 8 Remedios Naturales.

REGLAS DE RESPUESTA Y JUICIO EXPERTO:
1. **PRESENTACIÓN ÚNICA:** En el primer mensaje de saludo, preséntate con tu título completo y pregunta el nombre del paciente. Después, omite el título.
2. **RESPUESTA DIRECTA:** Si la consulta es específica de salud, OMITE el saludo y ve directo al diagnóstico.
3. ALERTA ROJA (Emergencia): Si la consulta es una emergencia clara, DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata.
4. REFERENCIA MÉDICA: En CADA respuesta de salud, refuerza la necesidad de consultar a tu médico personal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

# ----------------------------------------------------
# 2. BASE DE DATOS Y GESTIÓN DE ESTADO (Funciones)
# ----------------------------------------------------

def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception:
        return None

def guardar_historial(celular, mensaje, respuesta):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)", (celular, mensaje, respuesta))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

def contar_consultas(celular):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM historial_consultas WHERE celular = %s", (celular,))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except Exception:
            return 0
    return 0

def obtener_estado(celular):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO estado_conversacion (celular) VALUES (%s) ON CONFLICT (celular) DO UPDATE SET fecha_actualizacion = NOW() RETURNING paso, datos_recopilados", (celular,))
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            datos = json.loads(result[1]) if result[1] and result[1] != '{}' else {} 
            return {"paso": result[0], "datos": datos}
        except Exception:
            return {"paso": 0, "datos": {}}
    return {"paso": 0, "datos": {}}

def actualizar_estado(celular, paso, datos):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE estado_conversacion SET paso = %s, datos_recopilados = %s, fecha_actualizacion = NOW() WHERE celular = %s", (paso, json.dumps(datos), celular))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

def calcular_salud_avanzada(data):
    # [Función de cálculo BMI/riesgo]
    edad_cronologica = int(data.get('edad', 30))
    peso = float(data.get('peso', 70))
    altura = float(data.get('altura', 170)) / 100 
    glucosa = float(data.get('glucosa', 90))
    fuma = data.get('fuma', 'no').lower()
    ejercicio_dias = float(data.get('ejercicio_dias', 1))
    
    edad_biologica = edad_cronologica
    
    # MODIFICADORES DE RIESGO
    try:
        imc = round(peso / (altura ** 2), 2)
    except ZeroDivisionError:
        imc = 0
        
    if imc >= 30: edad_biologica += 3 
    if fuma == 'si': edad_biologica += 5 
    if glucosa >= 126: edad_biologica += 4 
    if ejercicio_dias < 3: edad_biologica += 3 

    diferencia = edad_biologica - edad_cronologica
    
    if diferencia <= 0:
        diagnostico = "¡Felicidades! Tu estilo de vida te está dando años extra. Eres un ejemplo de la Zona Azul Adventista."
    elif diferencia <= 5:
        diagnostico = "Tu estado de salud es bueno, pero tienes áreas de oportunidad. Con pequeños cambios puedes mejorar tu longevidad."
    else:
        diagnostico = f"Tu Edad Biológica es significativamente mayor. Urge iniciar un plan de Reforma Pro-Salud."

    return {
        "edad_cronologica": edad_cronologica,
        "edad_biologica": edad_biologica,
        "resumen": diagnostico
    }

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA DE GEMINI) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**. Por favor, deja de chatear AHORA y llama de inmediato al servicio de urgencias (911/número local) o acude a la sala de emergencias más cercana. Tu vida es la prioridad."
        )

    # === 2. LÓGICA CONVERSACIONAL Y JUICIO ===
    try:
        # La IA va directo a la respuesta con la personalidad simplificada (REGLA 2)
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Caleb está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Añadiendo la restricción)
# ==========================================
PROMOCION_ACCESO_LIMITADO = (
    "🚨 *ATENCIÓN - LÍMITE DE CONSULTAS ALCANZADO* 🚨\n\n"
    "Estimado(a) usuario(a), **Dr. Caleb** te ha ofrecido dos consultas gratuitas como cortesía del Ministerio de Salud. Si deseas tener acceso *ilimitado* y completo a las guías de salud:\n\n"
    "👉 **Comunícate con el Director de Salud y Temperancia de la Iglesia Adventista Redención Barranquilla para obtener tu código de acceso.**"
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Obtener el identificador del usuario
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    mensaje_upper = mensaje_in.upper().strip()
    
    # 1. Contar interacciones previas (sin contar los mensajes de flujo, solo las consultas)
    consultas_realizadas = contar_consultas(celular)

    # 2. Obtener estado actual (Memoria)
    estado = obtener_estado(celular)
    paso_actual = estado['paso']
    datos_recopilados = estado['datos']
    
    # === LÓGICA DE RESTRICCIÓN Y FLUJO DE ESTADOS ===

    # A. BLOQUEO DE LÍMITE
    if consultas_realizadas >= TEST_LIMIT and paso_actual == 0:
        respuesta = PROMOCION_ACCESO_LIMITADO
        guardar_historial(celular, mensaje_in, respuesta)
        return jsonify({"respuesta": respuesta})

    # B. FLUJO DE PREGUNTA-RESPUESTA SERIAL (paso_actual > 0)
    if paso_actual > 0:
        # A. Guardar la respuesta del paso anterior
        campo_anterior = TEST_STEPS[paso_actual]['campo']
        datos_recopilados[campo_anterior] = mensaje_in
        
        # B. Chequear si es la última pregunta (PASO FINAL)
        if paso_actual == len(TEST_STEPS):
            # 1. Calcular la edad biológica
            resultado = calcular_salud_avanzada(datos_recopilados)
            # 2. Formatear reporte final
            reporte_final = f"🎉 *ANÁLISIS DE EDAD BIOLÓGICA FINALIZADO* 🎉\n\n*RESULTADOS:*\n- Edad Cronológica: {resultado['edad_cronologica']} años\n- Edad Biológica: {resultado['edad_biologica']} años\n\n*DIAGNÓSTICO DEL DR. CALEB:*\n{resultado['resumen']}\n\nSu historial ha sido guardado. ¿Cómo te puedo ayudar hoy con una consulta específica?"
            
            # 3. Resetear el estado
            actualizar_estado(celular, 0, {}) 
            respuesta_final = reporte_final
        else:
            # Continuar a la siguiente pregunta
            paso_siguiente = paso_actual + 1
            pregunta_siguiente = TEST_STEPS[paso_actual + 1]['pregunta']
            respuesta_final = f"✅ Dato Guardado.\n\n*PREGUNTA {paso_siguiente} de {len(TEST_STEPS)}:*\n{pregunta_siguiente}"
            actualizar_estado(celular, paso_siguiente, datos_recopilados)
            
        guardar_historial(celular, mensaje_in, respuesta_final)
        return jsonify({"respuesta": respuesta_final})

    # C. FLUJO DE INICIO Y CONSULTA NORMAL (paso_actual == 0)
    else:
        # 3. TRIAGE DE EMERGENCIA (ALERTA ROJA)
        if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
            respuesta = consultar_gemini(mensaje_in) 
        
        # 4. OFERTA DEL TEST BIOLÓGICO (Si la persona saluda o pide ayuda)
        elif "TEST" in mensaje_upper or "EDAD BIOLOGICA" in mensaje_upper or mensaje_upper == "SÍ":
             # Si dice SÍ, iniciar el test inmediatamente
            actualizar_estado(celular, 1, {})
            pregunta_inicial = TEST_STEPS[1]['pregunta']
            respuesta = (
                "🎉 ¡Bienvenido! Soy el Dr. Caleb, tu guía. ¿Quieres realizar nuestro **TEST DE EDAD BIOLÓGICA**?\n"
                "Con solo 6 preguntas, calcularemos tu edad biológica versus la cronológica (inspirado en la Zona Azul Adventista).\n\n"
                "*Para empezar, responde con:* **SÍ** *o ignora y haz una consulta de salud normal.*"
            )
        
        # 5. CONSULTA NORMAL (Llamada a Gemini)
        else:
            respuesta = consultar_gemini(mensaje_in)
        
        guardar_historial(celular, mensaje_in, respuesta)
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (FLUJO CONVERSACIONAL Y MÁQUINA DE ESTADOS) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)