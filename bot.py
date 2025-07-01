import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import UserDatabase
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import json
import datetime 



# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Cargar variables de entorno
load_dotenv()

# Obtener token del bot
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# URL de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
# URL de la landing page
LANDING_PAGE_URL = os.getenv('LANDING_PAGE_URL', 'http://localhost:5000/plans')

# Inicializar la base de datos
db = UserDatabase()

# Obtener token del bot
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Inicializar la base de datos
db = UserDatabase()


# Estados para el flujo de conversación de login
EMAIL, PASSWORD, FILE_NAME_INPUT, ASK_QUESTION = range(4)
user_file_data = {}
async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar el proceso de login desde Telegram"""
    await update.message.reply_text(
        "Por favor, ingresa tu correo electrónico para iniciar sesión:"
    )
    return EMAIL

async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar la entrada del correo electrónico"""
    email = update.message.text.lower()  # Convertir a minúsculas
    context.user_data['email'] = email
    
    await update.message.reply_text(
        "Ahora, ingresa tu contraseña:"
    )
    return PASSWORD

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar la entrada de la contraseña y completar el login"""
    password = update.message.text
    email = context.user_data.get('email')
    telegram_id = update.effective_user.id
    
    # Intentar iniciar sesión
    success, message = db.login_telegram_user(telegram_id, email, password)
    
    if success:
        await update.message.reply_text(
            f"¡Inicio de sesión exitoso! Tu cuenta de Telegram ha sido vinculada con tu cuenta web."
        )
    else:
        await update.message.reply_text(
            f"Error al iniciar sesión: {message}\n\nPuedes intentarlo nuevamente con el comando /login"
        )
    
    # Limpiar datos sensibles
    if 'email' in context.user_data:
        del context.user_data['email']
    
    return ConversationHandler.END

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancelar el proceso de login"""
    await update.message.reply_text(
        "Proceso de inicio de sesión cancelado."
    )
    
    # Limpiar datos sensibles
    if 'email' in context.user_data:
        del context.user_data['email']
    
    return ConversationHandler.END

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar callbacks de botones inline"""
    query = update.callback_query
    user_id = update.effective_user.id

    # Manejar selección de documentos
    if query.data.startswith("select_doc_"):
        doc_id = query.data.replace("select_doc_", "")
        
        # Obtener información del documento
        success, doc_info = db.get_document_info(doc_id)
        
        if success:
            doc_name = doc_info.get('title', doc_info.get('filename', 'Documento'))
            file_type = doc_info.get('file_type', '')
            file_path = doc_info.get('file_path', '')
            
            # Guardar información del documento en el contexto
            if not hasattr(context, 'user_data'):
                context.user_data = {}
            
            context.user_data['last_document'] = {
                'document_id': doc_id,
                'file_path': file_path,
                'filename': doc_name,
                'content_type': 'image' if 'image' in file_type else 'document'
            }
            
            # Enviar mensaje de confirmación
            await query.edit_message_text(
                f"✅ Documento seleccionado: {doc_name}\n\n"
                f"¿Qué pregunta tienes sobre \"{doc_name}\"?"
            )
            
            return ASK_QUESTION
    
    elif query.data == "cancel_selection":
        await query.edit_message_text("❌ Selección cancelada.")
        return
    
    # Manejar otros callbacks (como login_bot)
    elif query.data == "login_bot":
        await query.answer()
        await query.message.reply_text(
            "Por favor, ingresa tu correo electrónico para iniciar sesión:"
        )
        context.user_data['waiting_for_email'] = True
        return EMAIL
async def group_documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar documentos del grupo para seleccionar"""
    user_id = update.effective_user.id
    
    # Verificar plan del usuario
    user_plan = check_user_plan(user_id)
    if not user_plan['active']:
        keyboard = [[InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder usar el asistente.",
            reply_markup=reply_markup
        )
        return

    # Obtener documentos del grupo (implementar esta función en database.py)
    success, documents = db.get_group_documents(user_id)
    
    if not success or not documents:
        await update.message.reply_text(
            "No hay documentos disponibles en el grupo."
        )
        return

    # Crear botones inline para cada documento
    keyboard = []
    for doc in documents[:10]:  # Limitar a 10 documentos
        doc_name = doc.get('title', doc.get('filename', 'Documento sin nombre'))[:30]
        doc_type = doc.get('file_type', 'unknown')
        emoji = "📄" if doc_type == 'application/pdf' else "🖼️" if 'image' in str(doc_type) else "📎"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {doc_name}",
                callback_data=f"select_doc_{doc['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 **Documentos del Grupo:**\n\n"
        "Selecciona un documento para usarlo como contexto en tu próxima consulta:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar la pregunta del usuario sobre un documento"""
    if 'last_document' not in context.user_data:
        await update.message.reply_text(
            "Por favor, primero selecciona o sube un documento sobre el cual hacer preguntas."
        )
        return ConversationHandler.END

    doc_info = context.user_data['last_document']
    action = "process_image" if doc_info['content_type'] == 'image' else "process_document"

    # Enviar mensaje de procesamiento
    await update.message.reply_text(
        f"🤔 Analizando tu {doc_info['content_type']} y procesando tu pregunta..."
    )

    # Preparar payload para n8n
    payload = {
        "telegram_id": update.effective_user.id,
        "text": update.message.text,
        "document_id": doc_info['document_id'],
        "file_path": doc_info['file_path'],
        "action": action
    }

    try:
        n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
        response = requests.post(n8n_webhook_url, json=payload)
        
        if response.status_code != 200:
            await update.message.reply_text(
                "Hubo un problema al procesar tu pregunta. Por favor, intenta de nuevo."
            )
    except Exception as e:
        logging.error(f"Error al procesar pregunta: {e}")
        await update.message.reply_text(
            "Ocurrió un error al procesar tu pregunta. Por favor, intenta de nuevo."
        )

    # Limpiar el documento seleccionado después de procesar
    del context.user_data['last_document']
    return ConversationHandler.END
# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para iniciar el bot"""
    user = update.effective_user
    user_data = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    
    # Guardar automáticamente al usuario que inicia el bot
    db.add_user(user.id, user_data)
    
    # Crear botones para la landing page y registro
    keyboard = [
        [InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)],
        [InlineKeyboardButton("📝 Registrarse en la web", url=f"{LANDING_PAGE_URL.split('/plans')[0]}/register")],
        [InlineKeyboardButton("🔑 Iniciar sesión en la web", url=f"{LANDING_PAGE_URL.split('/plans')[0]}/login")],
        [InlineKeyboardButton("🔐 Iniciar sesión en el bot", callback_data="login_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'¡Hola {user.first_name}! Soy el asistente de IA que te ayudará con tus consultas. '
        'Puedes enviarme imágenes, PDFs o texto y te ayudaré a interpretarlos. '
        'Para comenzar, necesitas registrarte en nuestra web y adquirir un plan de almacenamiento.\n\n'
        f'Tu ID de Telegram es: {user.id} - Guárdalo para vincularlo con tu cuenta web.',
        reply_markup=reply_markup
    )
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar documentos enviados por el usuario"""
    user = update.effective_user
    user_id = user.id
    
    # Verificar si el usuario tiene un plan activo y espacio disponible
    user_plan = check_user_plan(user_id)
    if not user_plan['active']:
        keyboard = [
            [InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder subir archivos.",
            reply_markup=reply_markup
        )
        return
    
    if user_plan['used_storage'] + update.message.document.file_size > user_plan['storage_limit']:
        await update.message.reply_text(
            "No tienes suficiente espacio disponible. Por favor, actualiza tu plan o libera espacio."
        )
        return
    
    # Obtener el archivo
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_url = file.file_path
    filename = document.file_name
    file_type = filename.split('.')[-1].lower()
    size_bytes = document.file_size
    
    await update.message.reply_text("Descargando y procesando tu archivo...")
    
    # Descargar el archivo temporalmente
    import tempfile
    import os
    import requests
    from io import BytesIO
    
    # Crear un archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}")
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # Descargar el archivo
        await file.download_to_drive(temp_file_path)
        
        # Abrir el archivo para procesarlo
        with open(temp_file_path, 'rb') as f:
            # Determinar el tipo de contenido para vectorización
            content_type = 'text'
            if file_type.lower() in ['pdf']:
                content_type = 'pdf'
            elif file_type.lower() in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                content_type = 'image'
            
            # Obtener o crear un grupo personal para el usuario
            group_id = get_or_create_personal_group(user_id)
            if not group_id:
                await update.message.reply_text("Error al crear grupo personal. Por favor, intenta de nuevo.")
                return
            
            # Obtener el UUID del usuario desde la base de datos
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"telegram_id": f"eq.{user_id}"}
            )
            
            if user_response.status_code != 200 or not user_response.json():
                await update.message.reply_text("Error al obtener información del usuario. Por favor, intenta de nuevo.")
                return
            
            user_uuid = user_response.json()[0]['id']
            
            # Crear un objeto similar a un archivo de Flask para la función upload_and_vectorize_file
            from types import SimpleNamespace
            file_obj = SimpleNamespace()
            file_obj.filename = filename
            file_obj.read = lambda: f.read()
            file_obj.seek = lambda x: f.seek(x)
            
            # Vectorizar el archivo usando el UUID del usuario
            success, result = db.upload_and_vectorize_file(group_id, user_uuid, file_obj, content_type)
            
            if success:
                # Notificar al usuario
                await update.message.reply_text("¡Archivo procesado y vectorizado correctamente!")
                
                # Enviar a n8n para notificación (opcional)
                payload = {
                    "telegram_id": user_id,
                    "action": "document_added", 
                    "document_id": result,
                    "group_id": group_id,
                    "filename": filename,
                    "content_type": content_type
                }
                
                n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
                requests.post(n8n_webhook_url, json=payload)
            else:
                await update.message.reply_text(f"Error al procesar el archivo: {result}")
    except Exception as e:
        logging.error(f"Error al procesar archivo: {e}")
        await update.message.reply_text(f"Ocurrió un error al procesar tu archivo: {str(e)}")
    finally:
        # Eliminar el archivo temporal
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar fotos enviadas por el usuario"""
    user = update.effective_user
    user_id = user.id
    
    # Verificar si el usuario tiene un plan activo y espacio disponible
    user_plan = check_user_plan(user_id)
    if not user_plan['active']:
        keyboard = [
            [InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder subir imágenes.",
            reply_markup=reply_markup
        )
        return
    
    # Obtener la foto más grande disponible
    photo = update.message.photo[-1]
    
    if user_plan['used_storage'] + photo.file_size > user_plan['storage_limit']:
        await update.message.reply_text(
            "No tienes suficiente espacio disponible. Por favor, actualiza tu plan o libera espacio."
        )
        return
    
    # Obtener el archivo
    file = await context.bot.get_file(photo.file_id)
    file_url = file.file_path
    filename = f"photo_{user_id}_{photo.file_id}.jpg"
    file_type = "jpg"
    size_bytes = photo.file_size
    
    await update.message.reply_text("Procesando tu imagen...")
    
    # Descargar el archivo temporalmente
    import tempfile
    import os
    import requests
    from io import BytesIO
    
    # Crear un archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # Descargar el archivo
        await file.download_to_drive(temp_file_path)
        
        # Abrir el archivo para procesarlo
        with open(temp_file_path, 'rb') as f:
            # Obtener o crear un grupo personal para el usuario
            group_id = get_or_create_personal_group(user_id)
            if not group_id:
                await update.message.reply_text("Error al crear grupo personal. Por favor, intenta de nuevo.")
                return
            
            # Obtener el UUID del usuario desde la base de datos
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"telegram_id": f"eq.{user_id}"}
            )
            
            if user_response.status_code != 200 or not user_response.json():
                await update.message.reply_text("Error al obtener información del usuario. Por favor, intenta de nuevo.")
                return
            
            user_uuid = user_response.json()[0]['id']
            
            # Crear un objeto similar a un archivo de Flask para la función upload_and_vectorize_file
            from types import SimpleNamespace
            file_obj = SimpleNamespace()
            file_obj.filename = filename
            file_obj.read = lambda: f.read()
            file_obj.seek = lambda x: f.seek(x)
            
            # Vectorizar el archivo usando el UUID del usuario
            success, result = db.upload_and_vectorize_file(group_id, user_uuid, file_obj, 'image')
            
            if success:
                # Notificar al usuario
                await update.message.reply_text("¡Imagen procesada y vectorizada correctamente!")
                
                # Enviar a n8n para notificación (opcional)
                payload = {
                    "telegram_id": user_id,
                    "action": "image_added",  
                    "document_id": result,
                    "group_id": group_id,
                    "filename": filename,
                    "content_type": "image"
                }
                
                n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
                requests.post(n8n_webhook_url, json=payload)
            else:
                await update.message.reply_text(f"Error al procesar la imagen: {result}")
    except Exception as e:
        logging.error(f"Error al procesar imagen: {e}")
        await update.message.reply_text(f"Ocurrió un error al procesar tu imagen: {str(e)}")
    finally:
        # Eliminar el archivo temporal
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
# Agregar después de los otros comandos
async def my_documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar documentos del usuario con opción de selección"""
    user_id = update.effective_user.id
    
    # Verificar plan del usuario
    user_plan = check_user_plan(user_id)
    if not user_plan:
        keyboard = [[InlineKeyboardButton("Ver Planes", url="https://tu-dominio.com/plans")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder usar el asistente.",
            reply_markup=reply_markup
        )
        return
    
    # Obtener documentos del usuario
    success, documents = db.get_user_documents(user_id)
    
    if not success or not documents:
        await update.message.reply_text(
            "No tienes documentos subidos aún. Sube un documento o imagen para comenzar."
        )
        return
    
    # Crear botones inline para cada documento
    keyboard = []
    for doc in documents[:10]:  # Limitar a 10 documentos
        doc_name = doc.get('title', doc.get('filename', 'Documento sin nombre'))[:30]
        doc_type = doc.get('file_type', 'unknown')
        emoji = "📄" if doc_type == 'application/pdf' else "🖼️" if 'image' in doc_type else "📎"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {doc_name}",
                callback_data=f"select_doc_{doc['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 *Tus documentos subidos:*\n\nSelecciona un documento para usarlo como contexto en tu próxima consulta:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def document_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de documentos"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "cancel_selection":
        await query.edit_message_text("❌ Selección cancelada.")
        return
    
    if query.data.startswith("select_doc_"):
        doc_id = query.data.replace("select_doc_", "")
        
        # Guardar el documento seleccionado en el contexto del usuario
        context.user_data['selected_document'] = doc_id
        
        # Obtener información del documento
        success, doc_info = db.get_document_info(doc_id)
        
        if success:
            doc_name = doc_info.get('title', doc_info.get('filename', 'Documento'))
            await query.edit_message_text(
                f"✅ Documento seleccionado: {doc_name}\n\n"
                f"El documento ha sido cargado como contexto. Ahora puedes hacer tu consulta y el sistema utilizará este documento como referencia.",
                parse_mode=None  # Evitar problemas de parsing
            )
        else:
            await query.edit_message_text("❌ Error al seleccionar el documento.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto del usuario"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Ignorar si es un comando o parte de una conversación activa
    if message_text.startswith('/'):
        return
    
    # Verificar si estamos en medio de una conversación
    current_conversation = context.user_data.get('conversation_state')
    if current_conversation in ['login', 'registration', 'file_upload']:
        return
    
    # Verificar plan del usuario
    user_plan = check_user_plan(user_id)
    if not user_plan:
        keyboard = [[InlineKeyboardButton("Ver Planes", url="https://tu-dominio.com/plans")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder usar el asistente.",
            reply_markup=reply_markup
        )
        return
    
    # Obtener o crear un grupo personal para el usuario
    group_id = get_or_create_personal_group(user_id)
    if not group_id:
        await update.message.reply_text("Error al acceder a tu grupo personal. Por favor, intenta de nuevo.")
        return
    
    # Verificar si hay un documento seleccionado
    selected_doc_id = context.user_data.get('selected_document')
    documents = []

    if selected_doc_id:
        # Usar documento específico seleccionado
        success, doc_info = db.get_document_info(selected_doc_id)
        if success:
            documents = [doc_info]
            doc_name = doc_info.get('title', 'Documento')
            # Limpiar selección después de usar
            context.user_data.pop('selected_document', None)
            
            await update.message.reply_text(
                f"Procesando tu consulta utilizando el documento seleccionado: {doc_name}..."
            )
    
    # Enviar el texto a n8n para procesamiento
    try:
        payload = {
            "telegram_id": user_id,
            "text": message_text,
            "type": "text",
            "action": "query",
            "group_id": group_id,
            "documents": documents,
            "has_selected_context": bool(selected_doc_id)
        }
        
        n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL_TEXT', os.getenv('N8N_WEBHOOK_URL'))
        response = requests.post(n8n_webhook_url, json=payload)
        
        if response.status_code == 200:
            if not selected_doc_id:  # Solo mostrar mensaje si no hay documento seleccionado
                await update.message.reply_text(
                    "Procesando tu consulta..."
                )
        else:
            await update.message.reply_text(
                "Hubo un problema al procesar tu consulta. Por favor, intenta de nuevo más tarde."
            )
    except Exception as e:
        logging.error(f"Error al procesar texto: {e}")
        await update.message.reply_text(
            "Ocurrió un error al procesar tu consulta. Por favor, intenta de nuevo más tarde."
        )
def get_user_documents(self, user_id, limit=20):
    """Obtener todos los documentos del usuario"""
    headers = self._get_supabase_headers()
    
    try:
        # Obtener UUID del usuario
        user_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"telegram_id": f"eq.{user_id}"}
        )
        
        if user_response.status_code != 200 or not user_response.json():
            return False, []
        
        user_uuid = user_response.json()[0]['id']
        
        # Buscar el grupo personal
        group_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            params={"name": f"eq.Personal_{user_id}", "admin_id": f"eq.{user_uuid}"}
        )
        
        if group_response.status_code != 200 or not group_response.json():
            return False, []
        
        group_id = group_response.json()[0]['id']
        
        # Obtener documentos del grupo
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_documents",
            headers=headers,
            params={
                "group_id": f"eq.{group_id}",
                "select": "*,documents(*)",
                "order": "created_at.desc",
                "limit": str(limit)
            }
        )
        
        if response.status_code == 200:
            group_docs = response.json()
            documents = []
            
            for group_doc in group_docs:
                if group_doc.get('documents'):
                    doc = group_doc['documents']
                    documents.append({
                        'id': doc['id'],
                        'title': doc['title'],
                        'content': doc['content'],
                        'file_type': doc['file_type'],
                        'file_path': doc['file_path'],
                        'created_at': doc['created_at'],
                        'file_size': doc['file_size']
                    })
            
            return True, documents
        
        return False, []
        
    except Exception as e:
        logging.error(f"Error obteniendo documentos del usuario: {e}")
        return False, []

def get_document_info(self, document_id):
    """Obtener información específica de un documento"""
    headers = self._get_supabase_headers()
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/documents",
            headers=headers,
            params={"id": f"eq.{document_id}"}
        )
        
        if response.status_code == 200 and response.json():
            doc = response.json()[0]
            return True, {
                'id': doc['id'],
                'title': doc['title'],
                'content': doc['content'],
                'file_type': doc['file_type'],
                'file_path': doc['file_path'],
                'created_at': doc['created_at']
            }
        
        return False, None
        
    except Exception as e:
        logging.error(f"Error obteniendo información del documento: {e}")
        return False, None

def get_user_documents_for_context(self, user_id, query_text, limit=3):
    """Obtener documentos del usuario para usar como contexto automático"""
    # Por ahora, obtener los documentos más recientes
    # Más adelante se puede implementar búsqueda vectorial
    success, all_docs = self.get_user_documents(user_id, limit)
    
    if success:
        # Limitar el contenido para no sobrecargar el contexto
        context_docs = []
        for doc in all_docs:
            context_doc = doc.copy()
            # Limitar contenido a 1000 caracteres por documento
            if len(context_doc['content']) > 1000:
                context_doc['content'] = context_doc['content'][:1000] + "..."
            context_docs.append(context_doc)
        
        return True, context_docs
    
    return False, []        
def get_or_create_personal_group(user_id):
    """Obtener o crear un grupo personal para el usuario"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Primero, obtener el UUID del usuario desde la tabla users
    user_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        params={"telegram_id": f"eq.{user_id}"}
    )
    
    if user_response.status_code != 200 or not user_response.json():
        logging.error(f"Usuario con telegram_id {user_id} no encontrado en la base de datos")
        return None
    
    user_uuid = user_response.json()[0]['id']
    
    # Buscar si el usuario ya tiene un grupo personal
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/groups",
        headers=headers,
        params={"name": f"eq.Personal_{user_id}", "admin_id": f"eq.{user_uuid}"}
    )
    
    if response.status_code == 200 and response.json():
        # El grupo ya existe
        return response.json()[0]['id']
    else:
        # Crear un nuevo grupo personal
        group_data = {
            "name": f"Personal_{user_id}",
            "description": f"Grupo personal para el usuario {user_id}",
            "admin_id": user_uuid,  # Usar UUID en lugar de telegram_id
            "is_active": True,
            "created_at": datetime.datetime.now().isoformat(),
            "shared_storage_bytes": 0
        }
        
        create_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            json=group_data
        )
        
        if create_response.status_code == 201:
            # Obtener el ID del grupo creado
            get_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/groups",
                headers=headers,
                params={"name": f"eq.Personal_{user_id}", "admin_id": f"eq.{user_uuid}"}
            )
            
            if get_response.status_code == 200 and get_response.json():
                group_id = get_response.json()[0]['id']
                
                # Añadir al usuario como miembro verificado del grupo
                db.add_group_member(group_id, user_uuid, is_admin=True, status='verified')
                
                return group_id
        else:
            logging.error(f"Error al crear grupo: {create_response.status_code} - {create_response.text}")
        
        return None
def check_user_plan(user_id):
    """Verificar el plan del usuario y espacio disponible en Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Consultar usuario por telegram_id
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"telegram_id": f"eq.{user_id}"}
        )
        
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
            
            # Verificar si el plan está activo
            now = datetime.datetime.now().isoformat()
            plan_active = user_data.get('plan_expiration', '') > now
            
            # Obtener información del plan
            plan_id = user_data.get('current_plan_id')
            plan_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/plans",
                headers=headers,
                params={"id": f"eq.{plan_id}"}
            )
            
            if plan_response.status_code == 200 and plan_response.json():
                plan_data = plan_response.json()[0]
                return {
                    'active': plan_active,
                    'used_storage': user_data.get('used_storage_bytes', 0),
                    'storage_limit': plan_data.get('storage_limit_bytes', 0)
                }
        
        # Si no hay datos o hay un error, retornar plan inactivo
        return {'active': False, 'used_storage': 0, 'storage_limit': 0}
    
    except Exception as e:
        logging.error(f"Error al verificar plan: {e}")
        return {'active': False, 'used_storage': 0, 'storage_limit': 0}




async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar ayuda sobre los comandos disponibles"""
    help_text = (
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/login - Iniciar sesión con tu cuenta web\n"
        "/help - Mostrar esta ayuda\n"
        "/add_user - Añadir un usuario (solo admin)\n"
        "/remove_user - Eliminar un usuario (solo admin)\n"
        "/list_users - Listar todos los usuarios (solo admin)\n"
        "/mis_documentos - Listar todos los documentos\n"
    )
    await update.message.reply_text(help_text)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Añadir un usuario a la base de datos"""
    # Aquí deberías verificar si el usuario que ejecuta el comando es administrador
    # Por ahora, permitiremos que cualquier usuario lo use
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Por favor, proporciona el ID de usuario de Telegram.\n"
            "Ejemplo: /add_user 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        user_data = {
            'added_by': update.effective_user.id,
            'status': 'active'
        }
        
        db.add_user(user_id, user_data)
        await update.message.reply_text(f"Usuario {user_id} añadido correctamente.")
    except ValueError:
        await update.message.reply_text("El ID de usuario debe ser un número.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eliminar un usuario de la base de datos"""
    # Aquí deberías verificar si el usuario que ejecuta el comando es administrador
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Por favor, proporciona el ID de usuario de Telegram.\n"
            "Ejemplo: /remove_user 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        if db.remove_user(user_id):
            await update.message.reply_text(f"Usuario {user_id} eliminado correctamente.")
        else:
            await update.message.reply_text(f"Usuario {user_id} no encontrado.")
    except ValueError:
        await update.message.reply_text("El ID de usuario debe ser un número.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar todos los usuarios en la base de datos"""
    # Aquí deberías verificar si el usuario que ejecuta el comando es administrador
    
    users = db.get_all_users()
    if not users:
        await update.message.reply_text("No hay usuarios registrados.")
        return
    
    user_list = "Lista de usuarios:\n\n"
    for user_id, user_data in users.items():
        username = user_data.get('username', 'Sin nombre de usuario')
        first_name = user_data.get('first_name', 'Sin nombre')
        user_list += f"ID: {user_id}, Usuario: {username}, Nombre: {first_name}\n"
    
    await update.message.reply_text(user_list)
async def handle_document_with_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar nombre para el documento antes de procesarlo"""
    user_id = update.effective_user.id
    document = update.message.document
    
    # Verificar plan del usuario
    user_plan = check_user_plan(user_id)
    if not user_plan['active']:
        keyboard = [
            [InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder subir archivos.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    if user_plan['used_storage'] + document.file_size > user_plan['storage_limit']:
        await update.message.reply_text(
            "No tienes suficiente espacio disponible. Por favor, actualiza tu plan o libera espacio."
        )
        return ConversationHandler.END
    
    # Guardar información del archivo temporalmente
    user_file_data[user_id] = {
        'type': 'document',
        'file_id': document.file_id,
        'filename': document.file_name,
        'file_size': document.file_size,
        'original_filename': document.file_name
    }
    
    await update.message.reply_text(
        f"📄 **Documento recibido:** `{document.file_name}`\n\n"
        "Por favor, ingresa un **nombre personalizado** para este documento:\n\n"
        "💡 *Ejemplo: 'Contrato de trabajo', 'Factura enero 2025', etc.*\n\n"
        "O envía /cancelar para cancelar la subida.",
        parse_mode='Markdown'
    )
    
    return FILE_NAME_INPUT

async def handle_photo_with_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar nombre para la foto antes de procesarla"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # Obtener la foto de mayor resolución
    
    # Verificar plan del usuario
    user_plan = check_user_plan(user_id)
    if not user_plan['active']:
        keyboard = [
            [InlineKeyboardButton("🛒 Ver planes de almacenamiento", url=LANDING_PAGE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No tienes un plan activo. Por favor, adquiere un plan para poder subir archivos.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    if user_plan['used_storage'] + photo.file_size > user_plan['storage_limit']:
        await update.message.reply_text(
            "No tienes suficiente espacio disponible. Por favor, actualiza tu plan o libera espacio."
        )
        return ConversationHandler.END
    
    # Guardar información de la foto temporalmente
    user_file_data[user_id] = {
        'type': 'photo',
        'file_id': photo.file_id,
        'file_size': photo.file_size,
        'filename': f"photo_{photo.file_id}.jpg"
    }
    
    await update.message.reply_text(
        "🖼️ **Imagen recibida**\n\n"
        "Por favor, ingresa un **nombre descriptivo** para esta imagen:\n\n"
        "💡 *Ejemplo: 'Foto del producto', 'Captura de pantalla', 'Imagen del evento', etc.*\n\n"
        "O envía /cancelar para cancelar la subida.",
        parse_mode='Markdown'
    )
    
    return FILE_NAME_INPUT

async def receive_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibir el nombre personalizado y procesar el archivo"""
    user_id = update.effective_user.id
    custom_name = update.message.text.strip()
    
    if user_id not in user_file_data:
        await update.message.reply_text("❌ Error: No se encontró información del archivo. Por favor, envía el archivo nuevamente.")
        return ConversationHandler.END
    
    file_data = user_file_data[user_id]
    
    # Validar el nombre
    if len(custom_name) < 3:
        await update.message.reply_text(
            "❌ El nombre debe tener al menos 3 caracteres. Por favor, ingresa un nombre más descriptivo:"
        )
        return FILE_NAME_INPUT
    
    if len(custom_name) > 100:
        await update.message.reply_text(
            "❌ El nombre es demasiado largo (máximo 100 caracteres). Por favor, ingresa un nombre más corto:"
        )
        return FILE_NAME_INPUT
    
    await update.message.reply_text(f"✅ Procesando archivo con nombre: **{custom_name}**", parse_mode='Markdown')
    
    try:
        if file_data['type'] == 'document':
            return await process_document_with_custom_name(update, context, file_data, custom_name)
        elif file_data['type'] == 'photo':
            await process_photo_with_custom_name(update, context, file_data, custom_name)
            return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error procesando archivo: {e}")
        # Escapar caracteres especiales
        error_msg = str(e).replace('`', "'").replace('_', "-").replace('*', "-")
        await update.message.reply_text(f"❌ Error al procesar el archivo: {error_msg}", parse_mode=None)
    finally:
        # Limpiar datos temporales
        if user_id in user_file_data:
            del user_file_data[user_id]
    
    return ConversationHandler.END

async def cancel_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancelar la subida del archivo"""
    user_id = update.effective_user.id
    
    if user_id in user_file_data:
        del user_file_data[user_id]
    
    await update.message.reply_text("❌ Subida de archivo cancelada.")
    return ConversationHandler.END   




    
async def process_document_with_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE, file_data, custom_name):
    """Procesar documento con nombre personalizado"""
    user_id = update.effective_user.id
    
    # Obtener el archivo
    file = await context.bot.get_file(file_data['file_id'])
    original_filename = file_data['filename']
    file_extension = original_filename.split('.')[-1].lower() if '.' in original_filename else 'txt'
    
    # Crear nombre de archivo con extensión
    custom_filename = f"{custom_name}.{file_extension}"
    
    await update.message.reply_text("📥 Descargando y procesando tu archivo...")
    
    # Resto del código similar a handle_document pero usando custom_filename
    import tempfile
    import os
    import requests
    import time
    import json
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        await file.download_to_drive(temp_file_path)
        
        with open(temp_file_path, 'rb') as f:
            content_type = 'text'
            if file_extension in ['pdf']:
                content_type = 'pdf'
            elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                content_type = 'image'
            
            group_id = get_or_create_personal_group(user_id)
            if not group_id:
                await update.message.reply_text("Error al crear grupo personal. Por favor, intenta de nuevo.")
                return ConversationHandler.END
            
            # Obtener UUID del usuario
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"telegram_id": f"eq.{user_id}"}
            )
            
            if user_response.status_code != 200 or not user_response.json():
                await update.message.reply_text("Error al obtener información del usuario.")
                return ConversationHandler.END
            
            user_uuid = user_response.json()[0]['id']
            
            # Crear objeto archivo con nombre personalizado
            from types import SimpleNamespace
            file_obj = SimpleNamespace()
            file_obj.filename = custom_filename  # Usar nombre personalizado
            file_obj.read = lambda: f.read()
            file_obj.seek = lambda x: f.seek(x)
            
            success, content_id = db.upload_and_vectorize_file(group_id, user_uuid, file_obj, content_type)
            
            if success:
                # Obtener el document_id y file_path desde group_contents
                document_id = None
                file_path = None
                
                content_response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/group_contents",
                    headers=headers,
                    params={"id": f"eq.{content_id}"},
                    timeout=10
                )
                
                if content_response.status_code == 200 and content_response.json():
                    content_data = content_response.json()[0].get('content_data')
                    if isinstance(content_data, str):
                        try:
                            content_data = json.loads(content_data)
                        except json.JSONDecodeError:
                            pass
                    
                    if isinstance(content_data, dict):
                        document_id = content_data.get('document_id')
                        file_path = content_data.get('file_url')  # Obtener file_url directamente
                        print(f"document_id obtenido: {document_id}")
                        print(f"file_path obtenido: {file_path}")
                
                if not document_id:
                    print("⚠️ No se pudo obtener document_id, usando content_id como fallback")
                    document_id = content_id
                
                # Inicializar payload base
                payload = {
                    "telegram_id": user_id,
                    "action": "document_added",
                    "document_id": document_id,  # Usar el document_id obtenido
                    "content_id": content_id,    # Incluir también el content_id para referencia
                    "group_id": group_id,
                    "filename": custom_filename,
                    "custom_name": custom_name,
                    "content_type": content_type
                }
                
                # Ya no necesitamos consultar la tabla documents, ya tenemos el file_path desde content_data
                
                # Agregar file_path al payload si se obtuvo
                if file_path:
                    payload["file_path"] = file_path
                    print(f"Payload final: {payload}")
                else:
                    print("⚠️ No se pudo obtener file_path, enviando payload sin él")
                                
                # Guardar información del documento en el contexto para usarla después
                if not hasattr(context, 'user_data'):
                    context.user_data = {}
                
                context.user_data['last_document'] = {
                    'document_id': document_id,
                    'content_id': content_id,
                    'group_id': group_id,
                    'file_path': file_path,
                    'filename': custom_filename,
                    'custom_name': custom_name,
                    'content_type': content_type
                }
                
                # Mensaje de éxito y solicitud de pregunta
                await update.message.reply_text(
                    f"✅ Archivo procesado exitosamente\n\n"
                    f"📄 Nombre: {custom_name}\n"
                    f"📁 Archivo: {custom_filename}\n\n"
                    f"Ahora, ¿qué pregunta tienes sobre este documento?",
                    parse_mode=None
                )
                
                return ASK_QUESTION
                
            else:
                error_msg = str(content_id).replace('`', "'").replace('_', "-").replace('*', "-")
                await update.message.reply_text(f"❌ Error al procesar el archivo: {error_msg}", parse_mode=None)
                return ConversationHandler.END
                
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
    return ConversationHandler.END
async def handle_document_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar la pregunta del usuario sobre el documento o imagen recién subida"""
    user_id = update.effective_user.id
    question = update.message.text.strip()
    
    if not hasattr(context, 'user_data') or 'last_document' not in context.user_data:
        await update.message.reply_text("❌ No se encontró información del archivo. Por favor, súbelo nuevamente.")
        return ConversationHandler.END
    
    document_data = context.user_data['last_document']
    content_type = document_data['content_type']
    
    # Crear payload para n8n incluyendo la pregunta
    payload = {
        "telegram_id": user_id,
        "action": "process_document" if content_type == 'pdf' else "process_image",
        "document_id": document_data['document_id'],
        "group_id": document_data['group_id'],
        "file_path": document_data.get('file_path'),
        "filename": document_data['filename'],
        "custom_name": document_data['custom_name'],
        "content_type": content_type,
        "question": question
    }
    
    # Enviar a n8n
    n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
    if n8n_webhook_url:
        try:
            await update.message.reply_text("🤔 Analizando tu " + ("documento" if content_type == 'pdf' else "imagen") + " y procesando tu pregunta...")
            n8n_response = requests.post(n8n_webhook_url, json=payload, timeout=10)
            print(f"Respuesta de n8n para la pregunta: {n8n_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error enviando pregunta a n8n: {e}")
            await update.message.reply_text("❌ Error al procesar tu pregunta. Por favor, intenta de nuevo más tarde.")
    else:
        print("N8N_WEBHOOK_URL no configurada")
        await update.message.reply_text("❌ Error de configuración del sistema. Por favor, contacta al administrador.")
    
    # Limpiar datos del documento
    if 'last_document' in context.user_data:
        del context.user_data['last_document']
    
    return ConversationHandler.END

async def process_photo_with_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE, file_data, custom_name):
    """Procesar foto con nombre personalizado"""
    user_id = update.effective_user.id
    
    file = await context.bot.get_file(file_data['file_id'])
    custom_filename = f"{custom_name}.jpg"
    
    await update.message.reply_text("🖼️ Descargando y procesando tu imagen...")
    
    import tempfile
    import os
    import requests
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        await file.download_to_drive(temp_file_path)
        
        with open(temp_file_path, 'rb') as f:
            group_id = get_or_create_personal_group(user_id)
            if not group_id:
                await update.message.reply_text("Error al crear grupo personal.")
                return
            
            # Obtener UUID del usuario
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"telegram_id": f"eq.{user_id}"}
            )
            
            if user_response.status_code != 200 or not user_response.json():
                await update.message.reply_text("Error al obtener información del usuario.")
                return
            
            user_uuid = user_response.json()[0]['id']
            
            from types import SimpleNamespace
            file_obj = SimpleNamespace()
            file_obj.filename = custom_filename
            file_obj.read = lambda: f.read()
            file_obj.seek = lambda x: f.seek(x)
            
            success, result = db.upload_and_vectorize_file(group_id, user_uuid, file_obj, 'image')
            
            if success:
                # Obtener el file_path del documento
                doc_response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/documents",
                    headers=headers,
                    params={"id": f"eq.{result}"}
                )
                
                file_path = None
                if doc_response.status_code == 200 and doc_response.json():
                    file_path = doc_response.json()[0]['file_path']
                
                # Guardar información de la imagen en el contexto
                if not hasattr(context, 'user_data'):
                    context.user_data = {}
                
                context.user_data['last_document'] = {
                    'document_id': result,
                    'group_id': group_id,
                    'file_path': file_path,
                    'filename': custom_filename,
                    'custom_name': custom_name,
                    'content_type': 'image'
                }
                
                await update.message.reply_text(
                    f"✅ Imagen procesada exitosamente\n\n"
                    f"📄 Nombre: {custom_name}\n"
                    f"📁 Archivo: {custom_filename}\n\n"
                    f"¿Qué pregunta tienes sobre esta imagen?",
                    parse_mode=None
                )
                
                return ASK_QUESTION
            else:
                await update.message.reply_text(f"❌ Error al procesar la imagen: {result}")
                
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)  
async def my_documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar documentos del usuario para seleccionar"""
    user_id = update.effective_user.id
    
    success, documents = db.get_user_documents(user_id)
    
    if not success or not documents:
        await update.message.reply_text(
            "❌ No tienes documentos subidos aún.\n\n"
            "Puedes subir documentos enviándome archivos PDF o imágenes."
        )
        return
    
    # Crear botones inline para cada documento
    keyboard = []
    for doc in documents[:10]:  # Limitar a 10 documentos
        # Validación adicional para evitar errores
        if doc and isinstance(doc, dict):
            doc_name = doc.get('title', doc.get('filename', 'Documento sin nombre'))
            if doc_name:
                doc_name = str(doc_name)[:30]  # Convertir a string y limitar
            else:
                doc_name = 'Documento sin nombre'
                
            doc_type = doc.get('file_type', 'unknown')
            emoji = "📄" if doc_type == 'application/pdf' else "🖼️" if 'image' in str(doc_type) else "📎"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {doc_name}",
                    callback_data=f"select_doc_{doc['id']}"
                )
            ])
    
    if not keyboard:  # Si no hay documentos válidos
        await update.message.reply_text(
            "❌ No se encontraron documentos válidos.\n\n"
            "Puedes subir documentos enviándome archivos PDF o imágenes."
        )
        return
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 **Tus documentos:**\n\n"
        "Selecciona un documento para usarlo como contexto en tu próxima consulta:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
def main():
    """Función principal para iniciar el bot"""
    # Crear la aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos básicos PRIMERO
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_user", add_user))
    application.add_handler(CommandHandler("remove_user", remove_user))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(CommandHandler("mis_documentos", my_documents_command))
    application.add_handler(CommandHandler("documentos_grupo", group_documents_command))
    
    # Registrar ConversationHandlers ANTES que otros handlers
    login_handler = ConversationHandler(
        entry_points=[
            CommandHandler("login", login_command),
            CallbackQueryHandler(button_callback, pattern="^login_bot$")
        ],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    application.add_handler(login_handler)
    
    file_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Document.ALL, handle_document_with_name),
            MessageHandler(filters.PHOTO, handle_photo_with_name)
        ],
        states={
            FILE_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_file_name)],
            ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_document_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel_file_upload)],
    )
    application.add_handler(file_handler)
    
    # Registrar el handler específico para selección de documentos ANTES que el handler genérico
    application.add_handler(CallbackQueryHandler(document_selection_callback, pattern="^(select_doc_|cancel_selection)$"))
    
    # Registrar el handler para mensajes de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Registrar el handler genérico para otros callbacks AL FINAL
    # Asegúrate de que button_callback devuelva None para callbacks que no maneja
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling()

if __name__ == '__main__':
    main()