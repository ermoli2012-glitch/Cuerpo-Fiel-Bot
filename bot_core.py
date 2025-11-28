import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN API KEY (SEGURA)
# ==========================================
# El código busca la clave en la variable de entorno de Render (la forma segura).
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Usamos el modelo estable que tu cuenta sí tiene acceso
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"❌ Error configurando Gemini: {e}")

# INSTRUCCIÓN MAESTRA (La personalidad del Bot)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un asistente de salud médico-misionero de la Iglesia Adventista (Distrito Redención).
Tu base son los 8 Remedios Naturales (ADELANTE): Agua, Descanso, Ejercicio, Luz Solar, Aire Puro, Nutrición, Temperancia, Esperanza en Dios.

REGLAS OBLIGATORIAS:
1. SÉ MUY BREVE: Tus respuestas NO deben pasar de 100 palabras.
2. Si detectas un síntoma, receta un remedio natural y una promesa bíblica.
3. ADVERTENCIA LEGAL: Aclara que no eres un doctor humano.
"""

# ==========================================
# 2. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
def obtener_conexion():
    try:
        # Render usará la variable DATABASE_URL y forzará SSL
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, sslmode='require')
        
        # Opción local (si no estamos en la nube)
        return psycopg2.connect(
            user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db"
        )
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
            print(f"💾 Historial guardado.")
        except Exception:
            pass

# --- 3. CEREBRO DE LA APLICACIÓN (EL FIX FINAL) ---
def consultar_gemini(mensaje_usuario):
    try:
        # FIX: Se envía la instrucción como parte del prompt, evitando el conflicto de parámetros.
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
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 2. Pensar
    respuesta = consultar_gemini(mensaje_in)
    
    # 3. Guardar
    guardar_historial(celular, mensaje_in, respuesta)

    # 4. Responder (Formato XML para Twilio)
    resp = MessagingResponse()
    resp.message(respuesta)
    
    # Devolvemos respuesta con el header correcto
    if 'whatsapp' in request.values.get('From', '').lower():
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 CUERPO FIEL 4.0 (CLOUD READY - FINAL) - ACTIVO")
    app.run(port=5000, debug=True)