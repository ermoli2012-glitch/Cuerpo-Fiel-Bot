import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
# Lee la clave de forma SEGURA desde la variable de entorno de Render
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD ANTI-EVASIÓN)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un Médico Misionero y Educador de Salud de la Iglesia Adventista (Distrito Redención).
Tu conocimiento proviene de la Biblia, el Espíritu de Profecía y las prácticas comprobadas de los Centros de Vida Sana.

REGLAS OBLIGATORIAS:
1. No evites las preguntas directas. Tu función es ofrecer *sugerencias específicas* de remedios naturales (como ajo, papaya, hidroterapia) para la dolencia consultada.
2. Responde de forma concisa (máximo 120 palabras).
3. Si el usuario pregunta por un síntoma, diagnostica la deficiencia del NEWSTART y receta el remedio específico.
4. Finaliza SIEMPRE con un versículo bíblico de esperanza.
5. ADVERTENCIA LEGAL: Debes incluir el descargo de responsabilidad solo al final.
"""

# ==========================================
# 2. BASE DE DATOS Y MEMORIA
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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA) ---
def consultar_gemini(mensaje_usuario):
    try:
        chat = model.start_chat(history=[])
        # Incluimos la instrucción de forma segura en el prompt
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        response = model.generate_content(prompt_full)
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
    
    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 4. Responder
    if 'whatsapp' in request.values.get('From', '').lower():
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (ANTI-EVASIÓN) ACTIVO")
    app.run(port=5000, debug=True)