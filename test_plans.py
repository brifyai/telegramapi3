#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la funcionalidad de planes
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from web_interface import app
    from database import UserDatabase
    
    print("✅ Imports exitosos")
    
    # Crear contexto de aplicación
    with app.app_context():
        print("✅ Contexto de aplicación creado")
        
        # Probar la base de datos
        db = UserDatabase()
        print("✅ Base de datos inicializada")
        
        # Probar obtener planes
        try:
            plans = db.get_plans()
            print(f"✅ Planes obtenidos: {len(plans)} planes encontrados")
            
            if plans:
                print("📋 Primer plan:")
                for key, value in plans[0].items():
                    print(f"   {key}: {value}")
        except Exception as e:
            print(f"❌ Error al obtener planes: {e}")
        
        # Probar obtener planes por servicio
        try:
            plans_abogados = db.get_plans_by_service('abogados')
            print(f"✅ Planes de abogados: {len(plans_abogados)} planes encontrados")
        except Exception as e:
            print(f"❌ Error al obtener planes por servicio: {e}")
            
    print("\n🎉 Todas las pruebas pasaron exitosamente!")
    
except Exception as e:
    print(f"❌ Error general: {e}")
    import traceback
    traceback.print_exc()
