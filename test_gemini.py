import google.generativeai as genai

api_key = "AIzaSyCq_hIUikHej8Vr91LZG32wrWepi-Omumw"
genai.configure(api_key=api_key)

print("Testing different Gemini models...\n")

# List all available models
print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")

print("\n" + "="*50 + "\n")

# Test models one by one
models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-pro', 
    'gemini-pro',
    'gemini-1.0-pro',
]

for model_name in models_to_test:
    try:
        print(f"Testing: {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello")
        print(f"✅ SUCCESS with {model_name}")
        print(f"Response: {response.text}\n")
        break
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}\n")