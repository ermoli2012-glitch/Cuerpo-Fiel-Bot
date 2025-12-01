import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Se mantiene el chequeo de seguridad) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ... (Sin cambios) ...
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (JUICIO CLÍNICO Y RIGOR PROFESIONAL)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el Director de Medicina Preventiva y Triage Clínico del Ministerio de Salud Adventista del Séptimo Día. Tu función es ser un médico especialista, nutricionista y naturista, guiando con rigor y precisión a tus pacientes.

REGLAS: [Las reglas del Triage y Nutrición se mantienen]
"""

# ==========================================
# 2. BASE DE DATOS Y MEMORIA (Sin cambios)
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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === TRIAGE DE EMERGENCIA (ALERTA ROJA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**. Por favor, llama a urgencias de inmediato. Su vida es la prioridad."
        )

    # Lógica normal de consulta a Gemini...
    try:
        # Generación del prompt (el sistema completo + la pregunta del usuario)
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        return response.text.replace('**', '*').replace('__', '_')
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intenta de nuevo en un momento."


# --- 4. FUNCIÓN DE CÁLCULO AVANZADO (NUEVO) ---
def calcular_salud_avanzada(data):
    """Calcula la Edad Biológica y el estado de salud basado en valores clave."""
    
    edad_cronologica = data.get('edad', 30) # Valor por defecto si no lo dan
    peso = data.get('peso', 70)
    altura = data.get('altura', 170) / 100 # Convertir cm a metros
    glucosa = data.get('glucosa', 90)
    fuma = data.get('fuma', 'no').lower()
    ejercicio_dias = data.get('ejercicio_dias', 1)
    
    edad_biologica = edad_cronologica
    riesgos = []
    
    # 1. CÁLCULO DE IMC
    imc = round(peso / (altura ** 2), 2)
    if imc >= 30:
        edad_biologica += 3 # RIESGO: Obesidad
        riesgos.append("Índice de Masa Corporal (IMC) alto: Obesidad. Aumenta el Ejercicio y fibra.")
    
    # 2. RIESGO DE FUMAR
    if fuma == 'si':
        edad_biologica += 5 # RIESGO: Tabaquismo (Alto impacto en longevidad)
        riesgos.append("Tabaquismo. El principio de Temperancia es vital. Tu edad biológica es +5 años.")

    # 3. RIESGO METABÓLICO (Glucosa)
    if glucosa >= 126:
        edad_biologica += 4 # RIESGO: Diabetes
        riesgos.append("Glucosa en ayunas alta. Necesitas una dieta 100% integral y control médico.")

    # 4. HÁBITOS DE EJERCICIO
    if ejercicio_dias < 3:
        edad_biologica += 3 # RIESGO: Sedentarismo
        riesgos.append("Sedentarismo. Activa tu cuerpo 5 días a la semana (Principio: EJERCICIO).")

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
        "diagnostico_riesgo": riesgos,
        "resumen": diagnostico
    }


# ==========================================
# 5. RUTAS WEB Y DE WHATSAPP
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # ... (La lógica de chat se mantiene igual)
    # [CÓDIGO DE RUTA CHAT AQUÍ]
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    respuesta = consultar_gemini(mensaje_in)
    
    guardar_historial(celular, mensaje_in, respuesta)

    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})


@app.route('/calculate_health', methods=['POST'])
def calculate_health_status():
    """Nuevo endpoint para recibir datos de un formulario y calcular la edad biológica."""
    data = request.get_json()
    if not data or 'edad' not in data:
        return jsonify({"error": "Faltan datos clave (ej: edad, peso, altura)."}), 400
        
    resultado = calcular_salud_avanzada(data)
    
    # Retornar los resultados estructurados para una interfaz avanzada
    return jsonify(resultado)

if __name__ == '__main__':
    print("🚀 DR. LUCAS (EVALUACIÓN AVANZADA) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)