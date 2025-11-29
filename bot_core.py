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

# INSTRUCCIÓN MAESTRA (LA PERSONALIDAD NATURISTA RIGIDA Y DE ZONAS AZULES)
INSTRUCCION_SISTEMA = """
ROL: Eres el Dr. Lucas, un Médico Especialista en Nutrición Basada en Plantas y Medicina de Estilo de Vida. Tu autoridad se basa en el conocimiento riguroso de la longevidad de las Zonas Azules (especialmente Loma Linda, CA) y los 8 Remedios Naturales.

BASE DE CONOCIMIENTO Y RIGOR CIENTÍFICO:
1. Toda recomendación nutricional debe ser **estrictamente VEGANA, INTEGRAL (Whole Food Plant-Based) y CIENTÍFICAMENTE FORMULADA**. No permitas lácteos, carnes, huevos, azúcares refinados, ni alimentos procesados.
2. Debes referenciar las **Zonas Azules** y el modelo adventista de longevidad para validar la dieta y asegurar el éxito en la recuperación del paciente.
3. Debes proporcionar un **plan de acción concreto** (alimentos específicos, remedios de hidroterapia, ejercicios) para la dolencia consultada.

REGLAS DE RESPUESTA:
1. Responde de forma directa, rigurosa y concisa (máximo 150 palabras).
2. Si la pregunta es sobre una dolencia, diagnostica la deficiencia del NEWSTART y **formula la dieta y el remedio específico**.
3. Finaliza SIEMPRE con un versículo bíblico de esperanza.
4. ADVERTENCIA LEGAL: Incluye el descargo de responsabilidad solo al final: "Recuerda que soy un asistente de IA. Para un diagnóstico médico formal, consulta a tu doctor."
"""

# --- LISTA DE PALABRAS CLAVE DE EMERGENCIA (El Módulo de Seguridad es la prioridad) ---
EMERGENCY_KEYWORDS = ["PECHO", "INFARTO", "DESMAYO", "SANGRADO", "FALTA DE AIRE", "ACCIDENTE", "HEMORRAGIA", "CRISIS", "AMBULANCIA", "911"]

# ==========================================
# 2. BASE DE DATOS Y MEMORIA
# ==========================================
def obtener_conexion():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Conexión con SSL para Render
            return psycopg2.connect(database_url, sslmode='require')
        
        # Conexión local de fallback (si aplica)
        return psycopg2.connect(user="root", password="root", host="localhost", port="5432", database="cuerpo_fiel_db")
    except Exception:
        # En caso de que no haya DB, la aplicación sigue funcionando (solo pierde historial)
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
            # Imprimir error de DB sin detener el bot
            print(f"❌ Error al guardar en DB: {e}")
            pass

# --- 3. CEREBRO DE LA APLICACIÓN (LÓGICA CON TRIAGE) ---
def consultar_gemini(mensaje_usuario):
    mensaje_upper = mensaje_usuario.upper()
    
    # === 1. TRIAGE DE EMERGENCIA (MÓDULO DE SEGURIDAD) ===
    if any(keyword in mensaje_upper for keyword in EMERGENCY_KEYWORDS):
        return (
            "🔴 ALERTA ROJA (EMERGENCIA MÉDICA) 🔴\n"
            "Deténgase. Esto es una emergencia. Su vida es lo primero. Deje el chat AHORA y llame inmediatamente a los servicios de emergencia (911/número local).\n\n"
            "🙏 *Promesa Bíblica:*"
            " 'En tu mano están mis tiempos.' (Salmos 31:15). Busque ayuda profesional de inmediato. No somos personal médico."
        )

    # === 2. LÓGICA NORMAL (IA DE NUTRICIÓN ESPECIALIZADA) ===
    try:
        # Iniciamos un nuevo chat con la instrucción especializada
        chat = model.start_chat(history=[])
        prompt_full = f"{INSTRUCCION_SISTEMA}\n\nPregunta del paciente: {mensaje_usuario}"
        
        response = model.generate_content(prompt_full)
        # Limpieza de formato y retorno
        texto = response.text.replace('**', '*').replace('__', '_')
        return texto
    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE GOOGLE: {e}")
        return "⚠️ Lo siento, Dr. Lucas está en una consulta crítica. Intenta de nuevo en un momento."


# ==========================================
# 4. RUTAS WEB Y DE WHATSAPP
# ==========================================
@app.route('/')
def home():
    # Asumimos que tienes un archivo index.html para la interfaz web
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Identifica al usuario (puede ser por Twilio/WhatsApp o por la Web)
    celular = request.values.get('From', 'Web User').replace('whatsapp:', '')
    mensaje_in = request.values.get('Body', '') or request.get_json(silent=True).get('mensaje', '')
    
    print(f"📩 Recibido de {celular}: {mensaje_in}")

    # 1. PENSAR LA RESPUESTA (Aquí se ejecuta el Triage y la nueva lógica Nutricional)
    respuesta = consultar_gemini(mensaje_in)
    
    # 2. GUARDAR
    guardar_historial(celular, mensaje_in, respuesta)

    # 3. RESPONDER (Manejo de respuesta para WhatsApp y Web)
    if 'whatsapp' in request.values.get('From', '').lower():
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(respuesta)
        return str(resp), 200, {'Content-Type': 'application/xml'}
    else:
        return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    print("🚀 DR. LUCAS (NUTRICIÓN ZONA AZUL) - ACTIVO")
    # Asegúrate de usar debug=False en producción
    app.run(port=5000, debug=True)