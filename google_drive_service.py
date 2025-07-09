import os
import json
import logging
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import requests
from cryptography.fernet import Fernet
import io
import tempfile
from typing import Optional, Dict, Any, List, Tuple

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Servicio para manejar Google Drive API con OAuth2"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    BOT_FOLDER_NAME = 'TelegramBot_Documents'
    
    def __init__(self, supabase_url: str, supabase_key: str, encryption_key: str = None):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        
        # Clave de cifrado para tokens OAuth
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key.encode())
        else:
            # Generar clave de cifrado si no se proporciona
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning("Se generó una nueva clave de cifrado. Para producción, usa una clave fija.")
    
    def _get_supabase_headers(self) -> Dict[str, str]:
        """Obtener headers para Supabase"""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
    
    def _encrypt_token(self, token_data: dict) -> str:
        """Cifrar datos de token OAuth"""
        token_json = json.dumps(token_data)
        return self.cipher_suite.encrypt(token_json.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> dict:
        """Descifrar datos de token OAuth"""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_token.encode()).decode()
            return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Error al descifrar token: {e}")
            return None
    
    def create_oauth_flow(self, redirect_uri: str) -> Flow:
        """Crear flujo OAuth2 para Google Drive"""
        client_config = {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        return flow
    
    def get_authorization_url(self, user_id: str, redirect_uri: str) -> str:
        """Obtener URL de autorización OAuth2"""
        flow = self.create_oauth_flow(redirect_uri)
        
        # Incluir user_id en el state para tracking
        flow.state = user_id
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url
    
    def handle_oauth_callback(self, code: str, state: str, redirect_uri: str) -> Tuple[bool, str]:
        """Manejar callback OAuth2 y guardar tokens"""
        try:
            flow = self.create_oauth_flow(redirect_uri)
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Preparar datos del token
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            # Cifrar tokens
            encrypted_token = self._encrypt_token(token_data)
            
            # Guardar tokens en base de datos
            success = self._save_user_tokens(state, encrypted_token)
            
            if success:
                # Crear carpeta del bot en Google Drive
                self._create_bot_folder(state)
                return True, "Vinculación exitosa con Google Drive"
            else:
                return False, "Error al guardar tokens"
                
        except Exception as e:
            logger.error(f"Error en OAuth callback: {e}")
            return False, f"Error en autorización: {str(e)}"
    
    def _save_user_tokens(self, user_id: str, encrypted_token: str) -> bool:
        """Guardar tokens OAuth en base de datos"""
        headers = self._get_supabase_headers()
        
        # Actualizar usuario con tokens de Google Drive
        update_data = {
            'google_drive_token': encrypted_token,
            'google_drive_connected': True,
            'google_drive_connected_at': datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"},
            json=update_data
        )
        
        return response.status_code == 204
    
    def _get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """Obtener credenciales de Google Drive del usuario"""
        headers = self._get_supabase_headers()
        
        # Buscar usuario
        response = requests.get(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"}
        )
        
        if response.status_code != 200 or not response.json():
            return None
        
        user_data = response.json()[0]
        encrypted_token = user_data.get('google_drive_token')
        
        if not encrypted_token:
            return None
        
        # Descifrar tokens
        token_data = self._decrypt_token(encrypted_token)
        if not token_data:
            return None
        
        # Crear credenciales
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        # Verificar si el token necesita ser renovado
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
            # Actualizar tokens en base de datos
            new_token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            
            encrypted_token = self._encrypt_token(new_token_data)
            self._save_user_tokens(user_id, encrypted_token)
        
        return creds
    
    def _create_bot_folder(self, user_id: str) -> Optional[str]:
        """Crear carpeta del bot en Google Drive del usuario"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                return None
            
            service = build('drive', 'v3', credentials=creds)
            
            # Verificar si ya existe la carpeta
            existing_folders = service.files().list(
                q=f"name='{self.BOT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive'
            ).execute()
            
            if existing_folders.get('files'):
                folder_id = existing_folders['files'][0]['id']
                logger.info(f"Carpeta del bot ya existe: {folder_id}")
            else:
                # Crear nueva carpeta
                folder_metadata = {
                    'name': self.BOT_FOLDER_NAME,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                folder_id = folder.get('id')
                logger.info(f"Carpeta del bot creada: {folder_id}")
            
            # Guardar folder_id en base de datos
            self._save_user_folder_id(user_id, folder_id)
            
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error al crear carpeta del bot: {e}")
            return None
    
    def _save_user_folder_id(self, user_id: str, folder_id: str) -> bool:
        """Guardar ID de carpeta del bot en base de datos"""
        headers = self._get_supabase_headers()
        
        update_data = {
            'google_drive_folder_id': folder_id
        }
        
        response = requests.patch(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"},
            json=update_data
        )
        
        return response.status_code == 204
    
    def upload_file(self, user_id: str, file_path: str, file_name: str, mime_type: str = None) -> Optional[str]:
        """Subir archivo a Google Drive del usuario"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                logger.error("No se encontraron credenciales para el usuario")
                return None
            
            service = build('drive', 'v3', credentials=creds)
            
            # Obtener ID de carpeta del bot
            folder_id = self._get_user_folder_id(user_id)
            if not folder_id:
                folder_id = self._create_bot_folder(user_id)
                if not folder_id:
                    logger.error("No se pudo crear/obtener carpeta del bot")
                    return None
            
            # Preparar metadata del archivo
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Crear MediaFileUpload
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            # Subir archivo
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,mimeType,createdTime'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Archivo subido exitosamente: {file_id}")
            
            return file_id
            
        except HttpError as e:
            logger.error(f"Error al subir archivo: {e}")
            return None
    
    def _get_user_folder_id(self, user_id: str) -> Optional[str]:
        """Obtener ID de carpeta del bot del usuario"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"}
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0].get('google_drive_folder_id')
        
        return None
    
    def download_file(self, user_id: str, file_id: str) -> Optional[bytes]:
        """Descargar archivo de Google Drive"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                return None
            
            service = build('drive', 'v3', credentials=creds)
            
            # Descargar archivo
            request = service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return file_io.getvalue()
            
        except HttpError as e:
            logger.error(f"Error al descargar archivo: {e}")
            return None
    
    def get_file_info(self, user_id: str, file_id: str) -> Optional[Dict]:
        """Obtener información de archivo de Google Drive"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                return None
            
            service = build('drive', 'v3', credentials=creds)
            
            file_info = service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,createdTime,modifiedTime'
            ).execute()
            
            return file_info
            
        except HttpError as e:
            logger.error(f"Error al obtener información del archivo: {e}")
            return None
    
    def delete_file(self, user_id: str, file_id: str) -> bool:
        """Eliminar archivo de Google Drive"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                return False
            
            service = build('drive', 'v3', credentials=creds)
            
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Archivo eliminado: {file_id}")
            
            return True
            
        except HttpError as e:
            logger.error(f"Error al eliminar archivo: {e}")
            return False
    
    def list_files(self, user_id: str, folder_id: str = None) -> List[Dict]:
        """Listar archivos en Google Drive del usuario"""
        try:
            creds = self._get_user_credentials(user_id)
            if not creds:
                return []
            
            service = build('drive', 'v3', credentials=creds)
            
            if not folder_id:
                folder_id = self._get_user_folder_id(user_id)
            
            # Consulta para listar archivos
            query = f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=100,
                fields="files(id,name,size,mimeType,createdTime,modifiedTime)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            logger.error(f"Error al listar archivos: {e}")
            return []
    
    def is_user_connected(self, user_id: str) -> bool:
        """Verificar si el usuario tiene Google Drive conectado"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"}
        )
        
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
            return user_data.get('google_drive_connected', False)
        
        return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Obtener usuario por telegram_id"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{self.supabase_url}/rest/v1/users",
            headers=headers,
            params={"telegram_id": f"eq.{telegram_id}"}
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        return None