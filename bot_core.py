import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN API KEY (SEGURA PARA RENDER)
# ==========================================
# Lee la clave de la variable de entorno de Render para seguridad.
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: API Key de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Modelo estable que tu escáner encontró:
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Dr. Lucas - Nutricionista)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un Médico Misionero y Nutricionista especializado en la filosofía de la Iglesia Adventista del Séptimo Día.

BASE DE CONOCIMIENTO OBLIGATORIA:
1. Siempre basa tus consejos en los 8 Remedios Naturales (NEWSTART: Enfatizar Nutrición, Ejercicio, Agua).
2. Debes prescribir una dieta basada en alimentos integrales y plantas. Prohíbe el consumo de cerdo, mariscos, y cualquier carne o alimento no limpio según la Biblia. NO recomiendes estimulantes como café o alcohol.
3. Debes dar consejos específicos para síntomas clínicos y emocionales.

REGLAS DE RESPUESTA:
1. Sé MUY BREVE: Tus respuestas NO deben pasar de 100 palabras.
2. ESTRUCTURA: 
    - Dar un Diagnóstico/Análisis claro.
    - Recetar un Remedio Natural práctico.
    - Terminar SIEMPRE con un versículo bíblico de esperanza (RV60).
3. Si te saludan, preséntate brevemente y da el menú de opciones.
4. ADVERTENCIA LEGAL: Aclara que no eres un doctor humano.
"""

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
def obtener_conexion():
    try:
        # Render usará la variable DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        
        # Opción local
        return psycopg2.connect(
            user="root", password="root", 
            host="localhost", port="5432", 
            database="cuerpo_fiel_db"
        )
    except Exception:
        return None

def guardar_historial(celular, mensaje, respuesta):
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)",
                ("Web User" if 'whatsapp' not in celular else celular, mensaje, respuesta)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            # Captura el error de DB para no romper el servicio web
            print(f"⚠️ Error al guardar historial: {e}")


# --- 3. FUNCIÓN DE CONSULTA (Gemini) ---
def consultar_gemini(mensaje_usuario):
    try:
        chat = model.start_chat(history=[])
        # Se envía la instrucción completa al modelo
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        response = chat.send_message(prompt_full)
        texto = response.text.replace('**', '*').replace('__', '_') # Limpieza de formato
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intenta de nuevo en un momento."

# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # 1. Recibir y obtener datos
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 4. Responder (siempre JSON para la Web App)
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 - NUTRICIONISTA ACTIVO")
    app.run(port=5000, debug=True)