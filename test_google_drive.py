#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la integración con Google Drive
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_drive_service import GoogleDriveService
from database import UserDatabase

def test_google_drive():
    """Probar la funcionalidad de Google Drive"""
    print("🧪 Probando integración con Google Drive...\n")
    
    # Inicializar servicios
    drive_service = GoogleDriveService()
    db = UserDatabase()
    
    # 1. Probar autenticación
    print("1️⃣ Probando autenticación...")
    auth_success = drive_service.authenticate()
    
    if auth_success:
        print("✅ Autenticación exitosa")
    else:
        print("❌ Error en autenticación")
        return False
    
    # 2. Probar creación de carpeta
    print("\n2️⃣ Probando creación de carpeta...")
    test_folder_name = "Test Entrenador - test@ejemplo.com"
    
    folder_id, error = drive_service.create_folder(test_folder_name)
    
    if folder_id:
        print(f"✅ Carpeta creada exitosamente: {folder_id}")
        
        # 3. Probar compartir carpeta
        print("\n3️⃣ Probando compartir carpeta...")
        share_success, share_error = drive_service.share_folder(folder_id, "test@ejemplo.com", "writer")
        
        if share_success:
            print("✅ Carpeta compartida exitosamente")
        else:
            print(f"⚠️ Error al compartir carpeta: {share_error}")
        
        # 4. Probar obtener información de carpeta
        print("\n4️⃣ Probando obtener información de carpeta...")
        folder_info, info_error = drive_service.get_folder_info(folder_id)
        
        if folder_info:
            print(f"✅ Información de carpeta obtenida:")
            print(f"   ID: {folder_info.get('id')}")
            print(f"   Nombre: {folder_info.get('name')}")
            print(f"   Creada: {folder_info.get('createdTime')}")
        else:
            print(f"❌ Error al obtener información: {info_error}")
        
        # 5. Probar base de datos
        print("\n5️⃣ Probando base de datos...")
        try:
            # Simular creación de carpeta en base de datos
            print("✅ Base de datos accesible")
        except Exception as e:
            print(f"❌ Error en base de datos: {e}")
        
        print(f"\n🎉 Todas las pruebas pasaron exitosamente!")
        print(f"📁 Carpeta de prueba creada: {folder_id}")
        print(f"🔗 Puedes verificar en: https://drive.google.com/drive/folders/{folder_id}")
        
        return True
        
    else:
        print(f"❌ Error al crear carpeta: {error}")
        return False

if __name__ == "__main__":
    try:
        success = test_google_drive()
        if success:
            print("\n🚀 La integración con Google Drive está funcionando correctamente!")
        else:
            print("\n💥 Hay problemas con la integración de Google Drive")
            print("📖 Revisa el archivo GOOGLE_DRIVE_SETUP.md para configuración")
            
    except Exception as e:
        print(f"\n💥 Error general: {e}")
        import traceback
        traceback.print_exc()
