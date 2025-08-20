import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('config.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def test_connection():
    """Probar conexión con Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"🔗 Probando conexión con: {SUPABASE_URL}")
    print(f"🔑 Usando key: {SUPABASE_KEY[:20]}...")
    
    try:
        # Probar conexión básica
        response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
        print(f"✅ Conexión exitosa: {response.status_code}")
        
        # Verificar tablas disponibles
        print("\n📋 Tablas disponibles:")
        response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
        if response.status_code == 200:
            print(response.text)
        
        # Revisar estructura de la tabla users
        print("\n👥 Estructura de la tabla 'users':")
        response = requests.get(f"{SUPABASE_URL}/rest/v1/users?select=*&limit=1", headers=headers)
        if response.status_code == 200:
            users = response.json()
            if users:
                print("Columnas disponibles:")
                for key, value in users[0].items():
                    print(f"  - {key}: {type(value).__name__}")
            else:
                print("Tabla users está vacía")
        else:
            print(f"❌ Error al acceder a users: {response.status_code}")
        
        # Revisar estructura de la tabla plans
        print("\n💳 Estructura de la tabla 'plans':")
        response = requests.get(f"{SUPABASE_URL}/rest/v1/plans?select=*&limit=1", headers=headers)
        if response.status_code == 200:
            plans = response.json()
            if plans:
                print("Columnas disponibles:")
                for key, value in plans[0].items():
                    print(f"  - {key}: {type(value).__name__}")
            else:
                print("Tabla plans está vacía")
        else:
            print(f"❌ Error al acceder a plans: {response.status_code}")
        
        # Revisar estructura de la tabla orders
        print("\n🛒 Estructura de la tabla 'orders':")
        response = requests.get(f"{SUPABASE_URL}/rest/v1/orders?select=*&limit=1", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            if orders:
                print("Columnas disponibles:")
                for key, value in orders[0].items():
                    print(f"  - {key}: {type(value).__name__}")
            else:
                print("Tabla orders está vacía")
        else:
            print(f"❌ Error al acceder a orders: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    test_connection()
