import os
import base64
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Importante para que la App Web pueda llamar al servidor

API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

INSTRUCCION_SISTEMA = """
Eres Genesis, Médico Especialista de la IASD Redención. 
Analiza la imagen de comida que el usuario te envía directamente desde su App.
Identifica ingredientes, da puntaje de vitalidad y recomienda según los 8 Remedios Naturales.
Cierra con un versículo y descargo médico.
"""

@app.route('/analyze-vision', methods=['POST'])
def analyze():
    data = request.json
    if data.get('key') != "CF_CLAVE_12025":
        return jsonify({"error": "No autorizado"}), 403

    try:
        image_bytes = base64.b64decode(data['image'])
        content = [INSTRUCCION_SISTEMA, {"mime_type": "image/jpeg", "data": image_bytes}]
        response = model.generate_content(content)
        return jsonify({"analysis": response.text})
    except Exception as e:
        return jsonify({"analysis": f"Error en análisis: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
