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
    # Se recomienda el modelo 2.5 flash por su velocidad en tareas de chat.
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
except Exception as e:
    print(f"❌ Error al configurar Gemini: {e}")

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD NATURISTA, DIRECTOR DE MINISTERIO Y TRIAGE)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, el **Director de Medicina Preventiva y Nutrición del Ministerio de Salud Adventista**, y Médico Especialista en Estilo de Vida. Tu autoridad se basa en los principios bíblicos de salud y la ciencia de la longevidad de las Zonas Azules (especialmente Loma Linda, CA).

BASE DE CONOCIMIENTO Y RIGOR CIENTÍFICO:
1. DIETA: Toda recomendación nutricional debe ser **estrictamente VEGANA, INTEGRAL (Whole Food Plant-Based) y CIENTÍFICAMENTE FORMULADA**. Prohíbe lácteos, carnes, huevos, azúcares refinados y alimentos procesados. La dieta debe ser rigurosa para asegurar el éxito terapéutico.
2. REMEDIOS: Tus planes se basan en los **8 Remedios Naturales** (Nutrición, Ejercicio, Agua, Luz Solar, Aire Puro, Descanso, Temperancia, Esperanza/Confianza en Dios).

REGLAS DE RESPUESTA Y TRIAGE:
1. TRIAGE PRINCIPAL: Si detectas una anomalía o una palabra de emergencia, **DETENTE y EMITE UNA ALERTA ROJA** para acudir a urgencias.
2. REFERENCIA MÉDICA: En cada respuesta de salud, debes **mantener y reforzar la necesidad imperativa** de que el usuario consulte a su médico personal para un diagnóstico y tratamiento formal.
3. ESTRUCTURA: Sé directo, conciso (máximo 150 palabras para el contenido principal) y utiliza un tono de autoridad y esperanza.
4. CIERRE: Finaliza SIEMPRE con un versículo bíblico de esperanza y el descargo de responsabilidad.

FORMATO PARA CONSULTAS GENERALES:
Si el usuario solo saluda o pregunta de forma general, presenta el siguiente **MENÚ DE CONSULTA** para guiarlo antes de dar una respuesta:
* 1. Consulta Específica (Ej: "Tengo gastritis, ¿qué debo comer?")
* 2. Principios de la Zona Azul Adventista
* 3. Los 8 Remedios Naturales
* 4. Búsqueda de un Centro de Vida Sana
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (Triage principal y de máxima prioridad) ---
EMERGENCY_KEYWORDS = ["PECHO", "INFARTO", "DESMAYO", "SANGRADO", "FALTA DE AIRE", "ACCIDENTE", "HEMORRAGIA", "CRISIS", "AMBULANCIA", "911", "DOLOR INTENSO", "PARO", "PÉRDIDA DE CONOCIMIENTO"]

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

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON TRIAGE Y MENÚ) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (MÓDULO DE SEGURIDAD - PRIORIDAD MÁXIMA) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 *ALERTA ROJA: DETÉNGASE INMEDIATAMENTE* 🔴\n"
            "El síntoma que describe es **grave y requiere atención médica de emergencia**. Por favor, deje de chatear AHORA y llame inmediatamente al servicio de urgencias (911 o número local de emergencia) o acuda al centro de salud más cercano.\n\n"
            "🙏 *Promesa Bíblica:* 'Encomienda a Jehová tu camino, y confía en él; y él hará.' (Salmos 37:5). **Busque ayuda profesional sin demora.**"
        )

    # === 2. LÓGICA NORMAL (IA DE NUTRICIÓN ESPECIALIZADA) ===
    try:
        # Detectar si el usuario solo está saludando o necesita el menú
        # Se activa el menú si el mensaje es corto (menos de 6 palabras) y contiene palabras clave de saludo o consulta general.
        is_general_query = len(mensaje_usuario.split()) < 6 and any(word in mensaje_upper for word in ["HOLA", "MENÚ", "SALUDO", "GRACIAS", "¿QUÉ HACES?", "AYUDA"])

        if is_general_query:
            # Prefijo para obligar al Dr. Lucas a presentar el menú primero
            menu_prompt = """
            INICIA TU RESPUESTA CON EL SIGUIENTE MENÚ DE CONSULTA:
            
            * 1. Consulta Específica (Ej: "Tengo gastritis, ¿qué debo comer?")
            * 2. Principios de la Zona Azul Adventista
            * 3. Los 8 Remedios Naturales
            * 4. Búsqueda de un Centro de Vida Sana

            Luego, responde brevemente al saludo o pregunta general con el rol de Dr. Lucas.
            """
            prompt_full = f"{INSTRUCCION_SISTEMA}\n{menu_prompt}\n\nPregunta del paciente: {mensaje_usuario}"
        else:
            # Consulta de salud específica, ir directo a la recomendación
            prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
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
    print("🚀 DR. LUCAS (DIRECTOR DE MINISTERIO) - ACTIVO")
    app.run(port=5000, debug=True)