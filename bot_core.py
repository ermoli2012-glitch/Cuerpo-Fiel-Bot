import os
import psycopg2
import google.generativeai as genai
# Importamos render_template para poder cargar el HTML
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- 1. CONFIGURACIÓN API KEY ---
# ¡REEMPLAZA ESTO CON TU CLAVE REAL DE GEMINI!
API_KEY = "AIzaSyCxroN9mO-IqOv15dV2xQJ29paNZtyzILE" 

try:
    genai.configure(api_key=API_KEY)
    # Usamos el modelo más rápido y accesible
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
except Exception as e:
    print(f"⚠️ Error Gemini: {e}")

# --- 2. CONFIGURACIÓN BD ---
# Esta función ahora usa 'Web User' en lugar del número de celular
def guardar_historial(mensaje, respuesta):
    try:
        # Usamos la variable de Render para la conexión a la nube
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url, sslmode='require')
        else:
            # Opción local por si quieres probarlo en tu máquina
            conn = psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
            
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial_consultas (celular, mensaje_recibido, respuesta_dada) VALUES (%s, %s, %s)", ("Web User", mensaje, respuesta))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error BD: {e}")

# --- 3. CEREBRO IA ---
INSTRUCCION = """
Eres 'Cuerpo Fiel', asistente de salud adventista.
Responde corto, empático y usa emojis.
Receta remedios naturales (NEWSTART) y citas bíblicas.
"""

def consultar_gemini(mensaje):
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{INSTRUCCION}\n\nUsuario: {mensaje}")
        return response.text
    except:
        return "⚠️ El sistema se está reiniciando. Intenta en 1 minuto."

# --- 4. RUTAS WEB ---

# RUTA 1: Muestra la interfaz de chat al entrar al link de Render
@app.route('/')
def home():
    # Render_template busca el archivo index.html en la carpeta 'templates'
    return render_template('index.html')

# RUTA 2: Recibe el mensaje desde el chat y devuelve la respuesta
@app.route('/chat', methods=['POST'])
def chat():
    # Obtiene el mensaje del JSON que envía el JavaScript
    datos = request.get_json()
    mensaje = datos.get('mensaje', '')
    
    print(f"📩 Web Recibido: {mensaje}")
    respuesta = consultar_gemini(mensaje)
    
    guardar_historial(mensaje, respuesta)
    
    # Devuelve la respuesta en formato JSON para que JavaScript la lea
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    app.run(port=5000, debug=True)