#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear la estructura de los planes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import UserDatabase

db = UserDatabase()

print("🔍 Analizando estructura de planes...\n")

# Obtener todos los planes
plans = db.get_plans()
print(f"📊 Total de planes: {len(plans)}")

# Analizar cada plan
for i, plan in enumerate(plans):
    print(f"\n📋 Plan {i+1}:")
    print(f"   ID: {plan.get('id', 'N/A')}")
    print(f"   Plan Code: {plan.get('plan_code', 'N/A')}")
    print(f"   Name: {plan.get('name', 'N/A')}")
    print(f"   Name ES: {plan.get('name_es', 'N/A')}")
    print(f"   Service Type: {plan.get('service_type', 'N/A')}")
    print(f"   Price USD: {plan.get('price_usd', 'N/A')}")
    print(f"   Storage Bytes: {plan.get('storage_limit_bytes', 'N/A')}")
    print(f"   Duration Days: {plan.get('duration_days', 'N/A')}")
    
    # Verificar campos críticos
    critical_fields = ['price_usd', 'storage_limit_bytes', 'duration_days']
    missing_fields = [field for field in critical_fields if plan.get(field) is None]
    
    if missing_fields:
        print(f"   ⚠️  CAMPOS FALTANTES: {missing_fields}")
    else:
        print(f"   ✅ Todos los campos críticos están presentes")

print(f"\n🎯 Planes por servicio:")
for service in ['abogados', 'entrenador', 'general']:
    plans_service = db.get_plans_by_service(service)
    print(f"   {service}: {len(plans_service)} planes")
