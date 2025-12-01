import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
import json # Necesario para manejar el JSONB de la BD
import re # Para limpieza de texto

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONSTANTES
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
TEST_LIMIT = 2 # Límite de consultas gratuitas antes del aviso promocional
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# DEFINICIÓN DE LOS PASOS DEL TEST BIOLÓGICO (El cerebro del flujo)
TEST_STEPS = {
    1: {"pregunta": "Primero, dime tu edad cronológica (solo el número en años):", "campo": "edad"},
    2: {"pregunta": "Ahora, tu altura en centímetros (ej: 175):", "campo": "altura"},
    3: {"pregunta": "Tu peso actual en kilogramos (kg):", "campo": "peso"},
    4: {"pregunta": "Tu glucosa en ayunas (solo el número en mg/dL, ej: 90):", "campo": "glucosa"},
    5: {"pregunta": "¿Fumas actualmente? (Responde 'Sí' o 'No'):", "campo": "fuma"},
    6: {"pregunta": "¿Cuántos días a la semana haces ejercicio (0 a 7)?", "campo": "ejercicio_dias"}
}

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception:
    pass

# INSTRUCCIÓN MAESTRA (La personalidad del Dr. Caleb)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Caleb, Médico Especialista, Nutricionista y Guía de Salud del Ministerio de Salud Adventista del Séptimo Día. Tu función es ser un consultor profesional, rápido y humano, **usando siempre el pronombre "TÚ"**.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. DIETA: Las recomendaciones nutricionales son estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS.
2. REMEDIOS: Aplica los 8 Remedios Naturales de forma precisa.

REGLAS DE RESPUESTA Y FLUJO DE CONVERSACIÓN:
1. **NO REPITAS TU CARGO NI TÍTULO después de la primera respuesta.**
2. Responde directamente al tema.
3. En CADA respuesta de salud, refuerza la necesidad de ver a tu médico personal.
4. Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

PROMOCION_ACCESO_LIMITADO = (
    "🚨 *ATENCIÓN - LÍMITE DE CONSULTAS ALCANZADO* 🚨\n\n"
    "Estimado(a) usuario(a), **Dr. Caleb** te ha ofrecido dos consultas gratuitas como cortesía del Ministerio de Salud. Si deseas tener acceso *ilimitado* y completo a las guías de salud y a la atención personalizada continua:\n\n"
    "👉 **Comunícate con el Director de Salud y Temperancia de la Iglesia Adventista Redención Barranquilla para obtener tu código de acceso.**\n\n"
    "¡Te esperamos para acompañarte en este camino de salud y vida plena! 💚"
)

# ==========================================
# 4. BASE DE DATOS Y GESTIÓN DE ESTADO
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
        except Exception as e:
            print(f"❌ Error al guardar en DB: {e}")
            pass

def contar_consultas(celular):
    """Cuenta el número total de interacciones del usuario."""
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
    """Obtiene o inicializa el estado de la conversación para el test biológico."""
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            # Asegura que haya una entrada de estado para este usuario.
            cursor.execute("INSERT INTO estado_conversacion (celular) VALUES (%s) ON CONFLICT (celular) DO UPDATE SET fecha_actualizacion = NOW() RETURNING paso, datos_recopilados", (celular,))
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            # El campo datos_recopilados es JSONB en la BD
            datos = json.loads(result[1]) if result[1] and result[1] != '{}' else {} 
            return {"paso": result[0], "datos": datos}
        except Exception as e:
            print(f"❌ Error al obtener estado: {e}")
            return {"paso": 0, "datos": {}}
    return {"paso": 0, "datos": {}}

def actualizar_estado(celular, paso, datos):
    """Actualiza el estado y los datos recopilados."""
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
    """Calcula la Edad Biológica simplificada basada en la lógica de riesgo."""
    
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

    # 5. DIAGNÓSTICO FINAL
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
        # La IA ya no repite el cargo, gracias al prompt
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
# 6. RUTAS WEB Y DE WHATSAPP (Añadiendo la restricción y el flujo de estados)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Obtener el identificador del usuario
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    # --- 1. CHEQUEO DE LÍMITE DE CONSULTAS ---
    if contar_consultas(celular) >= TEST_LIMIT:
        return jsonify({"respuesta": PROMOCION_ACCESO_LIMITADO})
    
    # 2. OBTENER ESTADO ACTUAL (Memoria)
    estado = obtener_estado(celular)
    paso_actual = estado['paso']
    datos_recopilados = estado['datos']
    
    # --- FLUJO DE PREGUNTA-RESPUESTA SERIAL (paso_actual > 0 significa que el test está activo) ---
    if paso_actual > 0:
        
        # Lógica de confirmación de inicio
        if paso_actual == 1 and mensaje_in.upper().strip() != 'SÍ':
             # No ha dicho 'SÍ' en el primer paso, pero ya está en el flujo. Asumimos que sigue la conversación normal.
             actualizar_estado(celular, 0, {})
             respuesta = consultar_gemini(mensaje_in)
             guardar_historial(celular, mensaje_in, respuesta)
             return jsonify({"respuesta": respuesta})

        # A. Guardar la respuesta del paso anterior (si no es el inicio)
        if paso_actual > 1:
            campo_anterior = TEST_STEPS[paso_actual - 1]['campo']
            datos_recopilados[campo_anterior] = mensaje_in
        
        # B. Chequear si es la última pregunta (PASO FINAL)
        if paso_actual == len(TEST_STEPS):
            # Procesar la última respuesta
            campo_final = TEST_STEPS[paso_actual]['campo']
            datos_recopilados[campo_final] = mensaje_in
            
            # 1. Calcular la edad biológica
            resultado = calcular_salud_avanzada(datos_recopilados)
            
            # 2. Formatear reporte final
            reporte_final = f"🎉 *ANÁLISIS DE EDAD BIOLÓGICA FINALIZADO* 🎉\n\n*RESULTADOS:*\n- Edad Cronológica: {resultado['edad_cronologica']} años\n- Edad Biológica: {resultado['edad_biologica']} años\n\n*DIAGNÓSTICO DEL DR. CALEB:*\n{resultado['resumen']}\n\nGracias por completar el test. Su historial ha sido guardado."
            
            # 3. Resetear el estado
            actualizar_estado(celular, 0, {}) 
            
            return jsonify({"respuesta": reporte_final})
        
        # C. CONTINUAR A LA SIGUIENTE PREGUNTA
        else:
            paso_siguiente = paso_actual + 1
            pregunta_siguiente = TEST_STEPS[paso_actual + 1]['pregunta']
            respuesta_flujo = f"✅ Dato Guardado.\n\n*PREGUNTA {paso_siguiente} de {len(TEST_STEPS)}:*\n{pregunta_siguiente}"
            actualizar_estado(celular, paso_siguiente, datos_recopilados)
            
            return jsonify({"respuesta": respuesta_flujo})

    # --- FLUJO DE INICIO Y CONSULTA NORMAL ---
    else:
        mensaje_upper = mensaje_in.upper()
        
        # 3. TRIAGE DE EMERGENCIA (ALERTA ROJA)
        if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
            respuesta = consultar_gemini(mensaje_in) # Manda el mensaje a Gemini para la alerta roja
        
        # 4. OFERTA DEL TEST BIOLÓGICO (Primer Contacto)
        elif any(word in mensaje_upper for word in ["HOLA", "BUENOS", "SALUDO", "TEST", "EDAD BIOLOGICA"]):
            # Respuesta inicial con oferta
            respuesta = (
                "👋 Saludos. Soy el Dr. Caleb, tu guía de salud. ¿Quieres realizar nuestro **TEST DE EDAD BIOLÓGICA**?\n"
                "Con solo 6 preguntas, calcularemos tu edad biológica versus la cronológica.\n\n"
                "*Para empezar, responde con:* **SÍ** *o ignora y haz una consulta de salud normal.*"
            )
            return jsonify({"respuesta": respuesta})

        # 5. CONSULTA NORMAL (Llamada a Gemini)
        else:
            respuesta = consultar_gemini(mensaje_in)
        
        guardar_historial(celular, mensaje_in, respuesta)
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. CALEB (MÁQUINA DE ESTADOS) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)