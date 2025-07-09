#!/usr/bin/env python3
"""
Script de migración para actualizar el esquema de la base de datos
Agrega campos necesarios para la integración con Google Drive
"""

import os
import requests
import json
import logging
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

def get_supabase_headers():
    """Obtener headers para Supabase con service role key"""
    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

def execute_sql(sql_query: str, description: str = ""):
    """Ejecutar consulta SQL en Supabase"""
    try:
        headers = get_supabase_headers()
        
        # Usar el endpoint de RPC para ejecutar SQL
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/execute_sql",
            headers=headers,
            json={"sql": sql_query}
        )
        
        if response.status_code == 200:
            logger.info(f"✅ {description} - Ejecutado exitosamente")
            return True
        else:
            logger.error(f"❌ {description} - Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ {description} - Excepción: {str(e)}")
        return False

def add_google_drive_columns():
    """Agregar columnas para Google Drive a la tabla users"""
    
    migrations = [
        {
            "sql": """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS google_drive_token TEXT,
                ADD COLUMN IF NOT EXISTS google_drive_connected BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS google_drive_connected_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS google_drive_folder_id TEXT;
            """,
            "description": "Agregar columnas de Google Drive a tabla users"
        },
        {
            "sql": """
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS google_drive_file_id TEXT,
                ADD COLUMN IF NOT EXISTS original_file_name TEXT,
                ADD COLUMN IF NOT EXISTS mime_type TEXT,
                ADD COLUMN IF NOT EXISTS text_content TEXT,
                ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
                ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';
            """,
            "description": "Agregar columnas de Google Drive a tabla documents"
        },
        {
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_documents_google_drive_file_id 
                ON documents(google_drive_file_id);
            """,
            "description": "Crear índice para google_drive_file_id"
        },
        {
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_documents_embedding_gin 
                ON documents USING gin(embedding);
            """,
            "description": "Crear índice GIN para embeddings (búsqueda vectorial)"
        },
        {
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_users_google_drive_connected 
                ON users(google_drive_connected);
            """,
            "description": "Crear índice para usuarios con Google Drive conectado"
        }
    ]
    
    logger.info("🚀 Iniciando migración de base de datos para Google Drive")
    
    success_count = 0
    for migration in migrations:
        if execute_sql(migration["sql"], migration["description"]):
            success_count += 1
        else:
            logger.error(f"❌ Error en migración: {migration['description']}")
    
    logger.info(f"✅ Migración completada: {success_count}/{len(migrations)} exitosas")
    return success_count == len(migrations)

def create_search_functions():
    """Crear funciones para búsqueda semántica"""
    
    functions = [
        {
            "sql": """
                CREATE OR REPLACE FUNCTION search_documents_by_similarity(
                    query_embedding vector(384),
                    user_uuid uuid,
                    similarity_threshold float DEFAULT 0.7,
                    result_limit int DEFAULT 5
                )
                RETURNS TABLE (
                    id uuid,
                    title text,
                    content text,
                    file_type text,
                    google_drive_file_id text,
                    similarity float,
                    created_at timestamp
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        d.id,
                        d.title,
                        d.text_content as content,
                        d.file_type,
                        d.google_drive_file_id,
                        1 - (d.embedding <=> query_embedding) as similarity,
                        d.created_at
                    FROM documents d
                    INNER JOIN group_documents gd ON d.id = gd.document_id
                    INNER JOIN groups g ON gd.group_id = g.id
                    INNER JOIN group_members gm ON g.id = gm.group_id
                    WHERE gm.user_id = user_uuid
                    AND gm.status = 'verified'
                    AND 1 - (d.embedding <=> query_embedding) >= similarity_threshold
                    ORDER BY d.embedding <=> query_embedding
                    LIMIT result_limit;
                END;
                $$ LANGUAGE plpgsql;
            """,
            "description": "Crear función de búsqueda semántica para documentos"
        },
        {
            "sql": """
                CREATE OR REPLACE FUNCTION get_user_documents_with_similarity(
                    user_uuid uuid,
                    query_text text DEFAULT '',
                    result_limit int DEFAULT 20
                )
                RETURNS TABLE (
                    id uuid,
                    title text,
                    content text,
                    file_type text,
                    google_drive_file_id text,
                    file_size bigint,
                    created_at timestamp,
                    similarity float
                ) AS $$
                DECLARE
                    query_embedding vector(384);
                BEGIN
                    -- Si no hay query_text, devolver todos los documentos
                    IF query_text = '' THEN
                        RETURN QUERY
                        SELECT 
                            d.id,
                            d.title,
                            d.text_content as content,
                            d.file_type,
                            d.google_drive_file_id,
                            d.file_size,
                            d.created_at,
                            0.0 as similarity
                        FROM documents d
                        INNER JOIN group_documents gd ON d.id = gd.document_id
                        INNER JOIN groups g ON gd.group_id = g.id
                        WHERE g.admin_id = user_uuid
                        AND g.name LIKE 'Personal_%'
                        ORDER BY d.created_at DESC
                        LIMIT result_limit;
                    ELSE
                        -- Aquí se generaría el embedding del query_text
                        -- Por ahora, usamos una búsqueda por texto
                        RETURN QUERY
                        SELECT 
                            d.id,
                            d.title,
                            d.text_content as content,
                            d.file_type,
                            d.google_drive_file_id,
                            d.file_size,
                            d.created_at,
                            0.8 as similarity
                        FROM documents d
                        INNER JOIN group_documents gd ON d.id = gd.document_id
                        INNER JOIN groups g ON gd.group_id = g.id
                        WHERE g.admin_id = user_uuid
                        AND g.name LIKE 'Personal_%'
                        AND (
                            d.title ILIKE '%' || query_text || '%'
                            OR d.text_content ILIKE '%' || query_text || '%'
                        )
                        ORDER BY d.created_at DESC
                        LIMIT result_limit;
                    END IF;
                END;
                $$ LANGUAGE plpgsql;
            """,
            "description": "Crear función para obtener documentos de usuario con similaridad"
        }
    ]
    
    logger.info("🔍 Creando funciones de búsqueda semántica")
    
    success_count = 0
    for function in functions:
        if execute_sql(function["sql"], function["description"]):
            success_count += 1
    
    logger.info(f"✅ Funciones creadas: {success_count}/{len(functions)} exitosas")
    return success_count == len(functions)

def create_backup_tables():
    """Crear tablas de respaldo antes de la migración"""
    
    backup_sql = """
        -- Crear respaldo de documentos existentes
        CREATE TABLE IF NOT EXISTS documents_backup AS 
        SELECT * FROM documents;
        
        -- Crear respaldo de users existentes
        CREATE TABLE IF NOT EXISTS users_backup AS 
        SELECT * FROM users;
        
        -- Crear tabla de migración log
        CREATE TABLE IF NOT EXISTS migration_log (
            id SERIAL PRIMARY KEY,
            migration_name TEXT NOT NULL,
            executed_at TIMESTAMP DEFAULT NOW(),
            success BOOLEAN DEFAULT FALSE,
            error_message TEXT
        );
    """
    
    return execute_sql(backup_sql, "Crear tablas de respaldo")

def log_migration(migration_name: str, success: bool, error_message: str = None):
    """Registrar migración en log"""
    headers = get_supabase_headers()
    
    log_entry = {
        "migration_name": migration_name,
        "executed_at": datetime.now().isoformat(),
        "success": success,
        "error_message": error_message
    }
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/migration_log",
            headers=headers,
            json=log_entry
        )
        
        if response.status_code == 201:
            logger.info(f"📝 Migración registrada: {migration_name}")
        else:
            logger.error(f"❌ Error al registrar migración: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error al registrar migración: {str(e)}")

def verify_migration():
    """Verificar que la migración fue exitosa"""
    headers = get_supabase_headers()
    
    # Verificar que las columnas existen
    verifications = [
        {
            "table": "users",
            "columns": ["google_drive_token", "google_drive_connected", "google_drive_folder_id"]
        },
        {
            "table": "documents", 
            "columns": ["google_drive_file_id", "original_file_name", "text_content", "embedding_model"]
        }
    ]
    
    logger.info("🔍 Verificando migración...")
    
    for verification in verifications:
        try:
            # Intentar consultar las nuevas columnas
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/{verification['table']}",
                headers=headers,
                params={"select": ",".join(verification['columns']), "limit": "1"}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Tabla {verification['table']} - Columnas verificadas")
            else:
                logger.error(f"❌ Error verificando {verification['table']}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando {verification['table']}: {str(e)}")
            return False
    
    logger.info("✅ Verificación completada exitosamente")
    return True

def main():
    """Función principal de migración"""
    
    logger.info("🚀 Iniciando migración de base de datos para Google Drive")
    
    # Verificar variables de entorno
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Variables de entorno SUPABASE_URL y SUPABASE_KEY requeridas")
        return False
    
    try:
        # Paso 1: Crear tablas de respaldo
        logger.info("📦 Creando tablas de respaldo...")
        if not create_backup_tables():
            logger.error("❌ Error creando tablas de respaldo")
            return False
        
        # Paso 2: Agregar columnas para Google Drive
        logger.info("🔧 Agregando columnas para Google Drive...")
        if not add_google_drive_columns():
            logger.error("❌ Error agregando columnas de Google Drive")
            log_migration("add_google_drive_columns", False, "Error agregando columnas")
            return False
        
        log_migration("add_google_drive_columns", True)
        
        # Paso 3: Crear funciones de búsqueda
        logger.info("🔍 Creando funciones de búsqueda...")
        if not create_search_functions():
            logger.error("❌ Error creando funciones de búsqueda")
            log_migration("create_search_functions", False, "Error creando funciones")
            return False
        
        log_migration("create_search_functions", True)
        
        # Paso 4: Verificar migración
        logger.info("✅ Verificando migración...")
        if not verify_migration():
            logger.error("❌ Error en verificación de migración")
            log_migration("verify_migration", False, "Error en verificación")
            return False
        
        log_migration("verify_migration", True)
        
        logger.info("🎉 Migración completada exitosamente!")
        logger.info("📋 Próximos pasos:")
        logger.info("   1. Configurar Google Cloud Console")
        logger.info("   2. Obtener credenciales OAuth2")
        logger.info("   3. Configurar variables de entorno")
        logger.info("   4. Probar integración con Google Drive")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error general en migración: {str(e)}")
        log_migration("main_migration", False, str(e))
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)