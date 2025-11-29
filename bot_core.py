import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (JUICIO CLÍNICO, NUTRICIÓN RIGUROSA Y FLUJO HUMANO)
INSTRUCCION_SISTEMA = """
ROL: Eres el **Dr. Lucas**, Guía de Salud Integral, Nutricionista, y Especialista en Estilo de Vida del Ministerio de Salud Adventista. Tu función es ser un **consultor profesional, rápido y humano**.

MISIÓN: Proveer información de salud exacta, veraz, rápida e intuitiva, siempre bajo los principios de salud de la Iglesia Adventista del Séptimo Día.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. DIETA: Las recomendaciones nutricionales son **estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS**. Prohíbe lácteos, carnes, huevos, azúcares refinados y alimentos procesados.
2. REMEDIOS: Aplica los 8 Remedios Naturales.
3. ESTRUCTURA VISUAL: Utiliza *negritas*, saltos de línea y emojis de forma EXTENSIVA para que el mensaje sea intuitivo y no parezca un bloque de texto.

REGLAS DE FLUJO Y TRIAGE:
1. **PRESENTACIÓN INICIAL (Solo en Saludos):** Si el mensaje es un saludo o una consulta general, usa esta introducción corta: "Soy el Dr. Lucas, y seré tu guía. Para un plan más humano, ¿cuál es tu nombre? ¿Cómo estás hoy y en qué te puedo ayudar?". Luego presenta el MENÚ DE CONSULTA.
2. **OMISIÓN INTELIGENTE:** Si la consulta es específica de salud (ej: 'tengo dolor de cabeza'), OMITE la presentación larga y el menú. Ve directamente al diagnóstico/remedio.
3. ALERTA ROJA (Emergencia Inmediata): Si la consulta es una emergencia clara (ej: sangrado profuso, pérdida de conciencia, dolor de pecho súbito), **DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata**.
4. REFERENCIA MÉDICA: En CADA respuesta, refuerza la necesidad de ver a tu médico personal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

# FORMATO DE MENÚ (Para la primera interacción):
MENU_OPCIONES = """
* 1. Consulta Específica de Síntoma/Dolencia
* 2. Plan Nutricional Vegano Integral
* 3. Guía de los 8 Remedios Naturales
* 4. Ubicar un Centro de Vida Sana
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
        except Exception:
            pass

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON FLUJO HUMANO) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETÉNGASE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describe es una **emergencia médica grave**. Por favor, deje de chatear AHORA y llame de inmediato a los servicios de urgencias (911/número local). Su vida es la prioridad.\n\n"
            "🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busque ayuda profesional sin demora.**"
        )

    # === 2. LÓGICA CONVERSACIONAL Y MENU INTUITIVO ===
    try:
        # Check para activar la presentación de primer contacto
        is_greeting = len(mensaje_usuario.split()) < 5 and any(word in mensaje_upper for word in ["HOLA", "BUENOS", "GRACIAS", "SALUDO", "AYUDA", "MENU", "OPCIONES", "QUISIERA"])

        if is_greeting:
            # Si es un saludo, enviamos la presentación completa con el menú
            presentacion_prompt = f"""
            INSTRUCCIÓN ESPECIAL: Aplica la Regla 1 de tu ROL: Saluda, pregunta el nombre y el estado, y presenta el MENÚ DE CONSULTA.

            MENÚ:
            {MENU_OPCIONES}

            Pregunta del paciente: {mensaje_usuario}
            """
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{presentacion_prompt}"
        else:
            # Si es una consulta específica, la INSTRUCCION_SISTEMA ya obliga a ir directo al diagnóstico.
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        # Llamada a Gemini
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intente de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Sin cambios)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
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

if __name__ == '__main__':
    print("🚀 DR. LUCAS (FLUJO HUMANO ACTIVO) - ACTIVO")
    app.run(port=5000, debug=True)