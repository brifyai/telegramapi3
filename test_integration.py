#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con Google Drive
"""

import os
import tempfile
from dotenv import load_dotenv
from google_drive_service import GoogleDriveService
from embeddings_service import EmbeddingsService
from database import UserDatabase

# Cargar variables de entorno
load_dotenv()

def test_google_drive_service():
    """Probar GoogleDriveService"""
    print("🧪 Probando GoogleDriveService...")
    
    try:
        drive_service = GoogleDriveService(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_KEY'),
            encryption_key=os.getenv('ENCRYPTION_KEY')
        )
        
        # Probar generar URL de autorización
        auth_url = drive_service.get_authorization_url(
            user_id="test_user",
            redirect_uri="http://localhost:5000/auth/google/callback"
        )
        
        print(f"✅ URL de autorización generada: {auth_url[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Error en GoogleDriveService: {e}")
        return False

def test_embeddings_service():
    """Probar EmbeddingsService"""
    print("🧪 Probando EmbeddingsService...")
    
    try:
        embeddings_service = EmbeddingsService(
            model_name="all-MiniLM-L6-v2",
            use_openai=False
        )
        
        # Probar generar embedding de texto
        test_text = "Este es un texto de prueba para generar embeddings."
        embedding = embeddings_service.generate_embedding(test_text)
        
        print(f"✅ Embedding generado: dimensión {len(embedding)}")
        
        # Probar validación
        is_valid = embeddings_service.validate_embedding(embedding)
        print(f"✅ Embedding válido: {is_valid}")
        
        # Probar extracción de texto de archivo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Contenido de prueba para extracción de texto.")
            temp_path = f.name
        
        try:
            text = embeddings_service.extract_text_from_file(temp_path, 'text')
            print(f"✅ Texto extraído: {text[:30]}...")
            
            # Probar embedding desde archivo
            result = embeddings_service.generate_embedding_from_file(temp_path, 'text')
            print(f"✅ Embedding desde archivo: {len(result['embedding'])} dimensiones")
            
        finally:
            os.unlink(temp_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en EmbeddingsService: {e}")
        return False

def test_database_integration():
    """Probar integración con Database"""
    print("🧪 Probando integración con Database...")
    
    try:
        # Verificar que se pueden importar los servicios
        db = UserDatabase()
        
        # Verificar que los servicios están inicializados
        if hasattr(db, 'drive_service') and hasattr(db, 'embeddings_service'):
            print("✅ Servicios inicializados en Database")
        else:
            print("❌ Servicios no inicializados en Database")
            return False
        
        # Probar método _get_mime_type
        mime_type = db._get_mime_type("test.pdf")
        print(f"✅ MIME type para PDF: {mime_type}")
        
        # Probar método _determine_content_type
        content_type = db._determine_content_type("test.pdf", "application/pdf")
        print(f"✅ Content type para PDF: {content_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en Database integration: {e}")
        return False

def test_environment_variables():
    """Verificar variables de entorno"""
    print("🧪 Verificando variables de entorno...")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables faltantes: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Todas las variables de entorno están configuradas")
        return True

def test_similarity_search():
    """Probar búsqueda por similaridad"""
    print("🧪 Probando búsqueda por similaridad...")
    
    try:
        embeddings_service = EmbeddingsService(use_openai=False)
        
        # Crear embeddings de prueba
        docs = [
            {"text": "Python es un lenguaje de programación", "embedding": None, "id": 1},
            {"text": "JavaScript es usado para web", "embedding": None, "id": 2},
            {"text": "Machine learning con Python", "embedding": None, "id": 3},
            {"text": "Base de datos relacionales", "embedding": None, "id": 4}
        ]
        
        # Generar embeddings
        for doc in docs:
            doc["embedding"] = embeddings_service.generate_embedding(doc["text"])
        
        # Buscar similares
        query = "programación en Python"
        query_embedding = embeddings_service.generate_embedding(query)
        
        similar_docs = embeddings_service.find_similar_documents(
            query_embedding=query_embedding,
            document_embeddings=docs,
            threshold=0.1,  # Umbral bajo para prueba
            limit=3
        )
        
        print(f"✅ Documentos similares encontrados: {len(similar_docs)}")
        for doc in similar_docs:
            print(f"   - ID: {doc['id']}, Similaridad: {doc['similarity']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en búsqueda por similaridad: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("🚀 Iniciando pruebas de integración con Google Drive\n")
    
    tests = [
        ("Variables de entorno", test_environment_variables),
        ("EmbeddingsService", test_embeddings_service),
        ("GoogleDriveService", test_google_drive_service),
        ("Database integration", test_database_integration),
        ("Búsqueda por similaridad", test_similarity_search)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Probando: {test_name}")
        print('='*50)
        
        success = test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    # Resumen
    print(f"\n{'='*50}")
    print("RESUMEN DE PRUEBAS")
    print('='*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nResultado final: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La integración está lista.")
        print("\n📋 Próximos pasos:")
        print("1. Configurar Google Cloud Console")
        print("2. Ejecutar migración de base de datos")
        print("3. Probar con usuarios reales")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar configuración.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)