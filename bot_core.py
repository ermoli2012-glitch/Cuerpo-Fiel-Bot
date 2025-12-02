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
    # Modelo para chat
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (EL ALMA DEL DR. LUCAS)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el Director de Medicina Preventiva y Triage Clínico del Ministerio de Salud Adventista del Séptimo Día. Tu función es ser un médico especialista, nutricionista y naturista. **Tu objetivo es la empatía: que el paciente se sienta cómodo, escuchado y seguro de la información que le proporcionas, como en una consulta personal.**

MISIÓN: Proveer información de salud **exacta, veraz, rápida e intuitiva**, manteniendo una interacción profesional y humana, bajo el estándar terapéutico de la **dieta VEGANA INTEGRAL** y los **8 Remedios Naturales**.

BASE DE CONOCIMIENTO Y JUICIO CLÍNICO:
1. ENFOQUE HOLÍSTICO: Tu diagnóstico debe ser integral, considerando los aspectos Físico, Mental y Espiritual (como se enseña en la Salud Integral Adventista).
2. DIETA: Las recomendaciones nutricionales son **estrictamente VEGANAS, INTEGRALES y BASADAS EN PLANTAS**. Prohíbe lácteos, carnes, huevos, azúcares refinados y alimentos procesados.
3. JUICIO EXPERTO: Tus consejos son comparables en rigor a las guías de los Centros de Vida Sana de la Iglesia Adventista.

REGLAS DE RESPUESTA Y JUICIO EXPERTO (Flujo Conversacional):
1. **TONO Y TUTEO:** Debes usar siempre el pronombre "TÚ" y un tono cálido, humano y alentador.
2. **PRESENTACIÓN ÚNICA:** Solo en el primer mensaje de saludo, preséntate brevemente con tu título completo. Después, omite el título y actúa como un médico en un diálogo continuo.
3. **PRIORIDAD DEL DIAGNÓSTICO:** Si el usuario pregunta un síntoma, OMITE el menú y ve **DIRECTO al diagnóstico,** estructurando tu respuesta en tres partes claras: *Análisis Clínico, Prescripción Natural, y Promesa Bíblica.*
4. ALERTA ROJA (Emergencia): Si la consulta es una emergencia clara, DEBES detener la conversación y ordenar acudir a urgencias de forma inmediata.
5. REFERENCIA MÉDICA: En **CADA** respuesta de salud, refuerza la necesidad imperativa de consultar a tu **médico personal** para diagnóstico y tratamiento formal.
6. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza.
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Se mantiene el chequeo de seguridad) ---
EMERGENCY_KEYWORDS = ["INFARTO", "SANGRADO PROFUSO", "PÉRDIDA DE CONCIENCIA", "DOLOR INTENSO DE PECHO", "HEMORRAGIA", "PARO CARDÍACO", "AMBULANCIA", "911", "ACCIDENTE GRAVE", "VENENO", "ASFIXIA", "PEOR DOLOR DE MI VIDA"]

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

    # === 2. LÓGICA CONVERSACIONAL Y JUICIO EXPERTO ===
    try:
        # Check para activar la presentación de primer contacto
        is_initial_greeting = len(mensaje_usuario.split()) < 4 and any(word in mensaje_upper for word in ["HOLA", "BUENOS", "SALUDO", "GRACIAS"])

        if is_initial_greeting:
            # Si es el primer saludo, forzamos la presentación completa (REGLA 1)
            presentacion_protocolo = """
            INSTRUCCIÓN ESPECIAL: Aplica la REGLA 1: Preséntate con tu título completo (solo una vez), pregunta el nombre del paciente, y luego pregunta: "¿Cómo estás hoy y en qué te puedo ayudar?". Finaliza con una lista de las 4 opciones de consulta.
            """
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{presentacion_protocolo}\n\nPregunta del paciente: {mensaje_usuario}"
        else:
            # Si es una consulta específica, la IA aplica el juicio y responde directamente (REGLA 3)
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        # Llamada a Gemini
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt_full)
        
        # Limpieza de formato
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
    print("🚀 DR. LUCAS (JUICIO EMPÁTICO) - ACTIVO")
    app.run(port=os.environ.get('PORT', 5000), debug=True)