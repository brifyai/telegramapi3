import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

print(f"Probando conexión a Supabase: {SUPABASE_URL}")

try:
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers
    )
    print(f"Código de estado: {response.status_code}")
    print(f"Respuesta: {response.text[:200]}..." if len(response.text) > 200 else response.text)
    print("Conexión exitosa" if response.status_code == 200 else "Error en la conexión")
except Exception as e:
    print(f"Error al conectar: {e}")