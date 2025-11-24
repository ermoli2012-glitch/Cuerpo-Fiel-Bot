import google.generativeai as genai

# --- PEGA TU CLAVE AQUÍ ---
API_KEY = "AIzaSyAeKvHeSo9RRnVo-LSmSwYyb3n5lsKWp8o" 

genai.configure(api_key=API_KEY)

print("🔍 BUSCANDO MODELOS DISPONIBLES...")
try:
    # Preguntamos a Google qué hay en el menú
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ ENCONTRADO: {m.name}")
except Exception as e:
    print(f"❌ ERROR: {e}")