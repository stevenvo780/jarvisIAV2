#!/usr/bin/env python3
"""
Script de prueba para validar claves API
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Verificando claves API...\n")

# OpenAI
openai_key = os.getenv('OPENAI_API_KEY')
if openai_key:
    print(f"✅ OpenAI API Key configurada: {openai_key[:20]}...{openai_key[-10:]}")
    # Test simple
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Responde solo 'OK' si me entiendes"}],
            max_tokens=10
        )
        print(f"   💬 Respuesta: {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("❌ OpenAI API Key no configurada")

print()

# Google
google_key = os.getenv('GOOGLE_API_KEY')
if google_key:
    print(f"✅ Google API Key configurada: {google_key[:20]}...{google_key[-10:]}")
    # Test simple
    try:
        import google.generativeai as genai
        genai.configure(api_key=google_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Responde solo 'OK' si me entiendes")
        print(f"   💬 Respuesta: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("❌ Google API Key no configurada")

print()

# HuggingFace
hf_token = os.getenv('HUGGINGFACE_TOKEN')
if hf_token:
    print(f"✅ HuggingFace Token configurado: {hf_token[:20]}...{hf_token[-10:]}")
else:
    print("❌ HuggingFace Token no configurado")
