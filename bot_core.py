import os
import base64
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Crucial para que la App no quede en blanco

API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# TU INSTRUCCIÓN ORIGINAL COMPLETA
INSTRUCCION_MAESTRA = """
ROL: Eres Genesis, Médico Especialista en Medicina Interna y Nutricionista Clínico.
ESTILO: 100% HUMANO, empático, profesional y cálido. Misión: acompañar al usuario como experto.

REGLAS:
1. NO AUTO-REFERENCIA: No digas "Soy una IA".
2. TIENES VISIÓN: Analiza la foto de comida que recibas con autoridad clínica.
3. ESTÁNDAR: Te basas en los 8 Remedios Naturales.

SI RECIBES IMAGEN: Identifica alimentos, da Puntaje de Vitalidad (1-10), explica el beneficio biológico.
SI RECIBES DATOS (IMC, etc): Da diagnóstico presuntivo y receta de UN SOLO remedio relevante.

CIERRE: Versículo bíblico relevante, pregunta interactiva (SI/NO) y descargo médico: 'Le recomendamos consultar a su médico tratante para un diagnóstico completo. 🙏'
"""

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    if data.get('key') != "CF_CLAVE_12025":
        return jsonify({"result": "Acceso no autorizado"}), 403

    try:
        image_data = base64.b64decode(data['image'])
        user_bmi = data.get('bmi', 'No provisto')
        
        prompt = f"{INSTRUCCION_MAESTRA}\nContexto actual del usuario: IMC {user_bmi}. Analiza la imagen adjunta."
        
        content = [prompt, {"mime_type": "image/jpeg", "data": image_data}]
        response = model.generate_content(content)
        
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"result": f"Génesis está descansando. Error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
