import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- 1. CONFIGURACIÓN API KEY (SEGURA) ---
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception:
    pass

# --- 2. EL CEREBRO DIAGNÓSTICO (INSTRUCCIÓN MAESTRA) ---
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un Médico Misionero Digital. Tu objetivo es hacer diagnósticos y dar consejos de salud exclusivos, basados ÚNICAMENTE en la FILOSOFÍA ADVENTISTA y los 8 Remedios Naturales (NEWSTART: Nutrición, Ejercicio, Agua, Sol, Temperancia, Aire, Reposo, Confianza en Dios).

FORMATO OBLIGATORIO: Tu respuesta debe ser concisa (máximo 120 palabras) y seguir este formato para todo tipo de consulta:

1. ANÁLISIS MÉDICO: Resumen de los síntomas o valores (ej: 'Su glucosa está en prediabetes').
2. PRINCIPIO VIOLADO: Identificar cuál de los 8 Remedios se está ignorando.
3. PRESCRIPCIÓN NATURAL: Dar el remedio práctico (ej: 'Beber 8 vasos de agua al día').
4. PROMESA BÍBLICA: Cita un texto de la Biblia RV60 que dé esperanza (ej: 'Filipenses 4:13').

Si el usuario escribe 'MENU', 'HOLA', o 'INICIO', preséntate usando el formato siguiente:
***
¡Bienvenido, Hermano! Soy el Dr. Lucas, su asistente de Cuerpo Fiel.
Por favor, dígame sus síntomas o envíe el valor de su último examen (ej: 'Presión 140' o 'Me siento muy estresado').
***
"""
# --- 3. FUNCIONES DE CONEXIÓN Y GUARDADO ---

def guardar_historial(celular, mensaje, respuesta):
    # [Mantener la función guardar_historial, ya incluida en el código]
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            import psycopg2
            conn = psycopg2.connect(database_url, sslmode='require')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)", ("Web User" if 'whatsapp' not in celular else celular, mensaje, respuesta))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error al guardar historial: {e}")


def consultar_gemini(mensaje_usuario):
    try:
        # La IA no necesita el historial para esta consulta, solo la instrucción y la pregunta
        response = model.generate_content(
            f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}",
            system_instruction=INSTRUCCION_SISTEMA
        )
        return response.text
    except Exception as e:
        print(f"❌ ERROR GEMINI: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intente en un momento."

# --- 4. RUTAS WEB ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje = datos.get('mensaje', '')
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    
    # 1. CONSULTAR IA
    respuesta = consultar_gemini(mensaje)
    
    # 2. GUARDAR HISTORIAL
    guardar_historial(celular, mensaje, respuesta)
    
    # 3. RESPONDER
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (MODO EXPERTO) ACTIVO")
    app.run(port=5000, debug=True)