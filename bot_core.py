import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse
import json 
import re
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONSTANTES
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
TEST_LIMIT = 2 
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# DEFINICIÓN DE LOS PASOS DEL TEST BIOLÓGICO (El cerebro del flujo)
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
ROL: Eres el Dr. Caleb, el Guía de Salud Integral del Ministerio de Salud Adventista del Séptimo Día. Eres Médico Especialista, Nutricionista y Naturista. Tu función es ser un consultor profesional, rápido y humano, **usando siempre el pronombre "TÚ"**.

MISIÓN: Proveer información de salud exacta, veraz, rápida e intuitiva, bajo el estándar terapéutico de la dieta VEGANA INTEGRAL y los 8 Remedios Naturales.

REGLAS DE RESPUESTA Y JUICIO EXPERTO (Flujo Conversacional):
1. **PRESENTACIÓN ÚNICA:** En el primer mensaje de saludo, debes presentarte con tu título completo y preguntar el nombre del paciente. Después, **omite por completo el título y solo responde a la consulta**.
2. ALERTA ROJA (Emergencia): Si la consulta es una emergencia clara, DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata.
3. REFERENCIA MÉDICA: En CADA respuesta de salud, refuerza la necesidad de consultar a tu médico personal.
4. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

PROMOCION_ACCESO_LIMITADO = (
    "🚨 *ATENCIÓN - LÍMITE DE CONSULTAS ALCANZADO* 🚨\n\n"
    "Estimado(a) usuario(a), **Dr. Caleb** te ha ofrecido dos consultas gratuitas como cortesía del Ministerio de Salud. Si deseas tener acceso *ilimitado* y completo a las guías de salud:\n\n"
    "👉 **Comunícate con el Director de Salud y Temperancia de la Iglesia Adventista Redención Barranquilla para obtener tu código de acceso.**"
)


# ==========================================
# 4. BASE DE DATOS Y GESTIÓN DE ESTADO (Funciones)
# ==========================================
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
        except Exception as e:
            print(f"❌ Error al obtener estado: {e}")
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
        except Exception as e:
            print(f"❌ Error al actualizar estado: {e}")

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
    imc = round(peso / (altura ** 2), 2)
    
    if imc >= 30: edad_biologica += 3 
    if fuma == 'si': edad_biologica += 5 
    if glucosa >= 126: edad_biologica += 4 
    if ejercicio_dias < 3: edad_biologica += 3 

    diferencia = edad_biologica - edad_cronologica
    
    if diferencia <= 0:
        diagnostico = "¡Felicidades! Tu estilo de vida te está dando años extra. Eres un ejemplo de la Zona Azul Adventista."
    elif diferencia <= 5:
        diagnostico = "Tu estado de salud es bueno, pero tienes áreas de oportunidad. Sigue mejorando la Temperancia."
    else:
        diagnostico = f"Tu Edad Biológica es significativamente mayor. Urge iniciar un plan de Reforma Pro-Salud."

    return {
        "edad_cronologica": edad_cronologica,
        "edad_biologica": edad_biologica,
        "diferencia": diferencia,
        "imc": imc,
        "resumen": diagnostico
    }


# --- 5. LÓGICA CONVERSACIONAL Y RUTAS ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    mensaje_upper = mensaje_in.upper().strip()
    
    # 1. CHEQUEO DE LÍMITE DE CONSULTAS
    if contar_consultas(celular) >= TEST_LIMIT:
        return jsonify({"respuesta": PROMOCION_ACCESO_LIMITADO})
    
    # 2. OBTENER ESTADO ACTUAL (Memoria)
    estado = obtener_estado(celular)
    paso_actual = estado['paso']
    datos_recopilados = estado['datos']
    
    # --- FLUJO DE PREGUNTA-RESPUESTA SERIAL (paso_actual > 0 significa que el test está activo) ---
    if paso_actual > 0:
        # Lógica para guardar la respuesta anterior y pasar a la siguiente pregunta
        
        # A. Guardar la respuesta del paso anterior
        if paso_actual == 1 and mensaje_upper not in ["SÍ", "SI"]:
            # Si el usuario no ha iniciado el test correctamente, permite reintentar el comando o salirse
            actualizar_estado(celular, 0, {})
            return jsonify({"respuesta": "Entiendo. El Test Biológico fue cancelado. ¿En qué puedo ayudarte hoy?"})

        if paso_actual >= 1 and paso_actual <= len(TEST_STEPS):
            # Guardar la respuesta del paso anterior (si no es la aceptación inicial)
            campo_anterior = TEST_STEPS[paso_actual]['campo']
            datos_recopilados[campo_anterior] = mensaje_in
        
        # B. Chequear si es la última pregunta (PASO FINAL)
        if paso_actual == len(TEST_STEPS):
            # 1. Calcular la edad biológica
            resultado = calcular_salud_avanzada(datos_recopilados)
            # 2. Formatear reporte final
            reporte_final = f"🎉 *ANÁLISIS DE EDAD BIOLÓGICA FINALIZADO* 🎉\n\n*RESULTADOS:*\n- Edad Cronológica: {resultado['edad_cronologica']} años\n- Edad Biológica: {resultado['edad_biologica']} años\n\n*DIAGNÓSTICO DEL DR. CALEB:*\n{resultado['resumen']}\n\nGracias por completar el test. Su historial ha sido guardado."
            
            # 3. Resetear el estado
            actualizar_estado(celular, 0, {}) 
            respuesta_final = reporte_final
        
        # C. CONTINUAR A LA SIGUIENTE PREGUNTA
        else:
            paso_siguiente = paso_actual + 1
            if paso_siguiente > len(TEST_STEPS):
                 # Si el paso siguiente es el último, regresamos el mensaje final
                 return jsonify({"respuesta": "El Test está completo. Procesando resultados..."}) # Debería ser capturado por el paso anterior, pero es un safety net
            
            pregunta_siguiente = TEST_STEPS[paso_siguiente]['pregunta']
            
            # Si es el primer paso (aceptación), no decimos "Dato guardado"
            if paso_actual == 0:
                respuesta_flujo = f"¡Excelente! Vamos a empezar.\n\n*PREGUNTA 1 de {len(TEST_STEPS)}:*\n{pregunta_siguiente}"
            else:
                respuesta_flujo = f"✅ Dato Guardado.\n\n*PREGUNTA {paso_siguiente} de {len(TEST_STEPS)}:*\n{pregunta_siguiente}"
                
            actualizar_estado(celular, paso_siguiente, datos_recopilados)
            respuesta_final = respuesta_flujo
            
        guardar_historial(celular, mensaje_in, respuesta_final)
        return jsonify({"respuesta": respuesta_final})


    # --- FLUJO DE INICIO Y CONSULTA NORMAL ---
    else:
        # Lógica para detectar el inicio del test
        if mensaje_upper == "SÍ" or mensaje_upper == "SI":
            # Iniciar el Test
            actualizar_estado(celular, 1, {})
            pregunta_inicial = TEST_STEPS[1]['pregunta']
            respuesta = (
                "🎉 ¡Excelente! Vamos a empezar.\n"
                "*PREGUNTA 1 de {}:*\n{}".format(len(TEST_STEPS), pregunta_inicial)
            )
        
        # Lógica de saludo y oferta del test
        elif any(word in mensaje_upper for word in ["HOLA", "BUENOS", "SALUDO", "TEST", "EDAD BIOLOGICA"]):
            respuesta = (
                "👋 Saludos cordiales. Soy el Dr. Caleb, tu guía de salud. ¿Quieres realizar nuestro **TEST DE EDAD BIOLÓGICA**?\n"
                "Con solo 6 preguntas, calcularemos tu edad biológica versus la cronológica.\n\n"
                "*Para empezar, responde con:* **SÍ** *o ignora y haz una consulta de salud normal.*"
            )

        # 5. CONSULTA NORMAL (Llamada a Gemini)
        else:
            respuesta = consultar_gemini(mensaje_in)
        
        guardar_historial(celular, mensaje_in, respuesta)
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (MÁQUINA DE ESTADOS) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)