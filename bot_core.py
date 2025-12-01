import os
import psycopg2
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI (CEREBRO)
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") 

try:
    if not API_KEY:
        print("⚠️ Advertencia: Clave de Gemini no encontrada en el entorno.")
        
    genai.configure(api_key=API_KEY)
    # Se sigue usando flash por su rapidez para chat
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (JUICIO CLÍNICO, RIGOR PROFESIONAL Y TONO AMIGABLE)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el Guía de Salud Integral del Ministerio de Salud Adventista. Eres un Médico Especialista, Nutricionista y Naturista. **Tu objetivo primordial es la empatía: que el paciente se sienta cómodo, escuchado, seguro y tranquilo** de que la información es veraz y lo ayudará. Debes usar siempre el pronombre "TÚ" y un tono cálido, humano y alentador, como en una consulta personal.

MISIÓN: Proveer información de salud exacta, veraz, rápida e intuitiva, manteniendo una interacción profesional y humana, bajo el estándar terapéutico de la dieta VEGANA INTEGRAL y los 8 Remedios Naturales.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. DIETA: Las recomendaciones nutricionales son **estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS**. Prohíbe lácteos, carnes, huevos, azúcares refinados y alimentos procesados.
2. REMEDIOS: Aplica los 8 Remedios Naturales de forma precisa.

REGLAS DE RESPUESTA Y JUICIO EXPERTO (Flujo Conversacional Médico-Paciente):
1. **PRESENTACIÓN INICIAL (Una Sola Vez):** Solo en la primera respuesta al saludo, preséntate con calidez y seguridad (menciona tu nombre y título). **Crucial: Después de esta primera respuesta, NO repitas tu nombre ni tu título**. Simplemente actúa como un médico en un diálogo continuo, usando frases como: "¿Qué más te preocupa?", "Mi recomendación es...", o yendo directo al grano.
2. FORMATO: Utiliza *negritas*, saltos de línea amplios y emojis de forma EXTENSIVA para hacer la lectura cómoda e intuitiva.
3. ALERTA ROJA (Emergencia): Si la consulta es una emergencia clara, DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata.
4. REFERENCIA MÉDICA: En CADA respuesta de salud, refuerza la necesidad de consultar a tu médico personal.
5. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

# ==========================================
# 2. BASE DE DATOS Y MEMORIA (Sin cambios)
# ==========================================
def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Render usa 'sslmode=require' para conexiones seguras
            return psycopg2.connect(database_url, sslmode='require')
        # Configuración local de ejemplo
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception:
        # Devuelve None si la conexión falla (puede ocurrir si no se configura DB)
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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON FLUJO DIRECTO) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (ALERTA ROJA INMEDIATA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETENTE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describes es una **emergencia médica grave**. Por favor, deja de chatear AHORA y llama de inmediato a los servicios de urgencias (911/número local) o acude a la sala de emergencias más cercana. Tu vida es la prioridad.\n\n"
            "🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busca ayuda profesional sin demora.**"
        )

    # === 2. LÓGICA CONVERSACIONAL Y JUICIO ===
    try:
        # Check para activar la presentación de primer contacto
        # Si el mensaje es corto (menos de 4 palabras) Y es un saludo (Hola, Buenos, Saludo), 
        # forzamos la presentación completa (REGLA 1).
        is_initial_greeting = len(mensaje_usuario.split()) < 4 and any(word in mensaje_upper for word in ["HOLA", "BUENOS", "SALUDO"])
        
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"

        if is_initial_greeting:
            # Si es el primer saludo, forzamos la presentación completa de calidez
            presentacion_protocolo = "INSTRUCCIÓN EXTRA: Aplica la REGLA 1 de tu ROL y haz la presentación inicial con calidez, preguntando cómo puedes ayudar."
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{presentacion_protocolo}\n\nPregunta del paciente: {mensaje_usuario}"
        
        # Si no es un saludo inicial, la IA irá directo al diagnóstico sin repetir su nombre/título.
        
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP (Sin cambios)
# ==========================================
@app.route('/')
def home():
    # Renderizar index.html (donde está el FIX de usabilidad móvil)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Intenta obtener el celular o usar un valor por defecto
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    
    # Intenta obtener el cuerpo del mensaje
    mensaje_in = request.values.get('Body', '')
    if not mensaje_in:
        try:
            # Si no es un formulario, intenta parsear como JSON (para la app web)
            json_data = request.get_json(silent=True)
            if json_data:
                mensaje_in = json_data.get('mensaje', '')
        except Exception:
            pass # Si falla, mensaje_in será ""
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    if not mensaje_in:
        return jsonify({"respuesta": "Por favor, escribe un mensaje."})

    respuesta = consultar_gemini(mensaje_in)
    
    guardar_historial(celular, mensaje_in, respuesta)

    # Lógica de respuesta para Twilio (WhatsApp) vs. Web
    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (FLUJO EMPÁTICO) - ACTIVO")
    # Usa Gunicorn en producción
    app.run(port=os.environ.get('PORT', 5000), debug=True)