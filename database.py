import os
import json
import time
import uuid
import hashlib
import secrets
import datetime
import requests
from dotenv import load_dotenv
import logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

class UserDatabase:
    def __init__(self, db_file='users.json'):
        # Mantener compatibilidad con el archivo local para transición gradual
        self.db_file = db_file
        self.users = {}
        self.load_users()
    
    def load_users(self):
        """Cargar usuarios desde el archivo JSON (para compatibilidad)"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except json.JSONDecodeError:
                self.users = {}
        else:
            self.users = {}
        return self.users
    
    def _save_users(self):
        """Guardar usuarios en el archivo JSON (para compatibilidad)"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4)
    
    def _get_supabase_headers(self):
        """Obtener headers para las solicitudes a Supabase"""
        return {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
    
    def add_user(self, telegram_id, user_data=None):
        """Añadir un usuario a Supabase"""
        if user_data is None:
            user_data = {}
        
        headers = self._get_supabase_headers()
        
        # Verificar si el usuario ya existe en Supabase
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            # El usuario ya existe, actualizar datos si es necesario
            user_id = response.json()[0]['id']
            update_data = {}
            
            # Actualizar solo los campos proporcionados
            if 'name' in user_data:
                update_data['name'] = user_data['name']
            if 'is_active' in user_data:
                update_data['is_active'] = user_data['is_active']
            
            if update_data:
                update_response = requests.patch(
                    f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                    headers=headers,
                    json=update_data
                )
                return update_response.status_code == 204
            
            return True  # No hay cambios que hacer
        else:
            # Crear nuevo usuario
            new_user = {
                "telegram_id": telegram_id,
                "name": user_data.get('name', ''),
                "email": user_data.get('email', ''),
                "created_at": datetime.datetime.now().isoformat(),
                "is_active": True,
                "used_storage_bytes": 0,
                "registered_via": "telegram"
            }
            
            # Si se proporciona un plan, añadirlo
            if 'current_plan_id' in user_data:
                new_user['current_plan_id'] = user_data['current_plan_id']
                
                # Calcular fecha de expiración si se proporciona duración
                if 'plan_duration_days' in user_data:
                    expiration = datetime.datetime.now() + datetime.timedelta(days=user_data['plan_duration_days'])
                    new_user['plan_expiration'] = expiration.isoformat()
            
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                json=new_user
            )
            
            # También guardar en el archivo local para compatibilidad
            self.users[str(telegram_id)] = new_user
            self._save_users()
            
            return response.status_code == 201
    
    def remove_user(self, telegram_id):
        """Eliminar un usuario de Supabase"""
        headers = self._get_supabase_headers()
        
        # Primero obtener el UUID del usuario
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            user_id = response.json()[0]['id']
            
            # Eliminar el usuario por su UUID
            delete_response = requests.delete(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers=headers
            )
            
            # También eliminar del archivo local para compatibilidad
            if str(telegram_id) in self.users:
                del self.users[str(telegram_id)]
                self._save_users()
            
            return delete_response.status_code == 204
        
        return False
    def get_user_by_id(self, user_id):
        """Obtener información de un usuario de Supabase por su UUID"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        # Si no se encuentra en Supabase, devolver None
        return None
    def get_user(self, telegram_id):
        """Obtener información de un usuario de Supabase"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        # Si no se encuentra en Supabase, intentar en el archivo local
        return self.users.get(str(telegram_id))
    
    def get_all_users(self):
        """Obtener todos los usuarios de Supabase"""
        headers = self._get_supabase_headers()
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers
        )
        
        if response.status_code == 200:
            # Convertir la lista a un diccionario con telegram_id como clave
            users_dict = {}
            for user in response.json():
                if user.get('telegram_id'):
                    users_dict[str(user['telegram_id'])] = user
            return users_dict
        
        # Si hay un error, devolver los usuarios del archivo local
        return self.users
    
    def register_web_user(self, email, password, telegram_id=None):
        """Registrar un nuevo usuario web en Supabase"""
        headers = self._get_supabase_headers()
        # Convertir email a minúsculas
        email = email.lower()
        logging.info(f"Intentando registrar usuario con email: {email}")
        # Verificar si el email ya existe
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"email": f"eq.{email}"}
        )
        
        if response.status_code == 200 and response.json():
            return False, "El email ya está registrado"
        
        # Hash de la contraseña
        salt = os.urandom(32)
        salt_hex = salt.hex()  # Convertir a hexadecimal para almacenar
        
        # Generar hash de la contraseña
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt, 
            100000
        )
        password_hash_hex = password_hash.hex()  # Convertir a hexadecimal para almacenar
        
        # Datos del usuario
        user_data = {
            "email": email,
            "password_hash": password_hash_hex,  # Almacenar como texto hexadecimal
            "salt": salt_hex,  # Almacenar como texto hexadecimal
            "created_at": datetime.datetime.now().isoformat(),
            "is_active": True,
            "used_storage_bytes": 0,
            "registered_via": "web"
        }
        
        # Añadir telegram_id si se proporciona
        if telegram_id:
            user_data["telegram_id"] = int(telegram_id) if telegram_id.isdigit() else None
        
        # Crear usuario en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            json=user_data
        )
        
        if response.status_code == 201:
            # Obtener el UUID generado
            get_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"email": f"eq.{email}"}
            )
            
            if get_response.status_code == 200 and get_response.json():
                user_id = get_response.json()[0]['id']
                
                # También guardar en el archivo local para compatibilidad
                self.users[user_id] = user_data
                self._save_users()
                
                return True, user_id
        
        return False, "Error al registrar el usuario"
    def login_telegram_user(self, telegram_id, email, password):
        """Iniciar sesión de usuario desde Telegram y vincular cuentas"""
        # Convertir email a minúsculas
        email = email.lower()
        # Primero intentamos el login normal
        success, message = self.login_web_user(email, password)
        
        if success:
            user_id = message  # El ID del usuario en Supabase
            headers = self._get_supabase_headers()
            
            # Actualizar el telegram_id en la cuenta del usuario
            update_data = {"telegram_id": telegram_id}
            
            # Actualizar en Supabase
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"id": f"eq.{user_id}"},
                json=update_data
            )
            
            if response.status_code == 204:  # Supabase devuelve 204 en actualizaciones exitosas
                return True, "Inicio de sesión exitoso y cuenta vinculada"
            else:
                return False, "Error al vincular cuenta de Telegram"
        
        return False, message
    def login_web_user(self, email, password):
        """Iniciar sesión de usuario web en Supabase"""
        headers = self._get_supabase_headers()
        # Convertir email a minúsculas
        email = email.lower()
        logging.info(f"Intentando iniciar sesión con email: {email}")
        
        # Buscar usuario por email
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"email": f"eq.{email}"}
        )
        
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
            user_id = user_data['id']
            
            try:
                # Obtener salt (siempre debe ser hexadecimal)
                salt_hex = user_data.get('salt', '')
                logging.info(f"Salt obtenido: {salt_hex[:10]}...")
                
                # Intentar convertir salt de hex a bytes
                try:
                    salt = bytes.fromhex(salt_hex)
                except ValueError as e:
                    logging.error(f"Error al convertir salt: {str(e)}")
                    return False, "Error en formato de credenciales"
                
                # Obtener password_hash almacenado
                stored_hash = user_data.get('password_hash', '')
                logging.info(f"Hash almacenado: {stored_hash[:10]}...")
                
                # Generar hash con la contraseña proporcionada
                calculated_hash = hashlib.pbkdf2_hmac(
                    'sha256', 
                    password.encode('utf-8'), 
                    salt, 
                    100000
                ).hex()  # Convertir a hexadecimal para comparar como texto
                
                logging.info(f"Hash calculado: {calculated_hash[:10]}...")
                
                # Comparar hashes como texto
                if calculated_hash == stored_hash:
                    return True, user_id
                else:
                    return False, "Contraseña incorrecta"
                    
            except Exception as e:
                logging.error(f"Error al verificar contraseña: {str(e)}")
                return False, f"Error al verificar credenciales: {str(e)}"
        
        # Si no se encuentra en Supabase, intentar en el archivo local
        for user_id, user_data in self.users.items():
            if user_data.get('email') == email:
                try:
                    # Obtener salt (siempre debe ser hexadecimal)
                    salt_hex = user_data.get('salt', '')
                    
                    # Intentar convertir salt de hex a bytes
                    try:
                        salt = bytes.fromhex(salt_hex)
                    except ValueError as e:
                        logging.error(f"Error al convertir salt local: {str(e)}")
                        return False, "Error en formato de credenciales"
                    
                    # Obtener password_hash almacenado
                    stored_hash = user_data.get('password_hash', '')
                    
                    # Generar hash con la contraseña proporcionada
                    calculated_hash = hashlib.pbkdf2_hmac(
                        'sha256', 
                        password.encode('utf-8'), 
                        salt, 
                        100000
                    ).hex()  # Convertir a hexadecimal para comparar como texto
                    
                    # Comparar hashes como texto
                    if calculated_hash == stored_hash:
                        return True, user_id
                    else:
                        return False, "Contraseña incorrecta"
                        
                except Exception as e:
                    logging.error(f"Error al verificar contraseña local: {str(e)}")
                    return False, f"Error al verificar credenciales: {str(e)}"
        
        return False, "Usuario no encontrado"
    
    def update_user_plan(self, user_id, plan_id, expiration_days=30):
        """Actualizar el plan de un usuario en Supabase"""
        headers = self._get_supabase_headers()
    
        # Calcular fecha de expiración
        expiration_date = (datetime.datetime.now() + 
                        datetime.timedelta(days=expiration_days)).isoformat()
    
        # Datos a actualizar
        update_data = {
            "current_plan_id": plan_id,
            "plan_expiration": expiration_date,
            "is_active": True
        }
        
        # Actualizar en Supabase
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"},
            json=update_data
        )
        
        return response.status_code == 204

   
    
    def add_order(self, user_id, plan_id, amount):
        """Registrar una nueva orden en Supabase"""
        headers = self._get_supabase_headers()
        
        # Buscar el UUID del plan basado en el plan_code
        plan_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/plans",
            headers=headers,
            params={"plan_code": f"eq.{plan_id}"}
        )
        
        if plan_response.status_code != 200 or not plan_response.json():
            logging.error(f"Error al buscar plan: {plan_id}")
            return False, None
        
        # Obtener el UUID del plan
        plan_uuid = plan_response.json()[0]['id']
        
        # Crear nueva orden
        order_id = str(uuid.uuid4())
        order = {
            "id": order_id,
            "user_id": user_id,
            "plan_id": plan_uuid,  # Usar el UUID del plan
            "amount_usd": amount,
            "payment_status": "paid",
            "payment_provider": "manual",
            "payment_ref": f"manual-{order_id}",
            "paid_at": datetime.datetime.now().isoformat()
        }
        
        # Insertar en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/payments",
            headers=headers,
            json=order
        )
        
        # Verificar respuesta y registrar errores
        if response.status_code != 201:
            logging.error(f"Error al crear orden: {response.status_code} - {response.text}")
            return False, None
        
        # También guardar en el archivo local para compatibilidad
        if str(user_id) in self.users:
            if 'orders' not in self.users[str(user_id)]:
                self.users[str(user_id)]['orders'] = []
            
            local_order = {
                'order_id': order_id,
                'plan_id': plan_id,  # Guardar el código original del plan
                'amount': amount,
                'date': datetime.datetime.now().isoformat(),
                'status': 'completed'
            }
            
            self.users[str(user_id)]['orders'].append(local_order)
            self._save_users()
        
        return response.status_code == 201, order_id



    def create_group(self, admin_id, group_name, verification_type='phone'):
        """Crear un nuevo grupo con el usuario como administrador"""
        headers = self._get_supabase_headers()
        
        group_id = str(uuid.uuid4())
        group = {
            "id": group_id,
            "name": group_name,
            "admin_id": admin_id,
            "verification_type": verification_type,
            "created_at": datetime.datetime.now().isoformat(),
            "is_active": True,
            "shared_storage_bytes": 0
        }
        
        # Insertar en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            json=group
        )
        
        # Añadir al administrador como miembro del grupo
        if response.status_code == 201:
            self.add_group_member(group_id, admin_id, is_admin=True, status='verified')
            return True, group_id
        
        return False, "Error al crear el grupo"

    def add_group_member(self, group_id, user_id, is_admin=False, status='pending'):
        """Añadir un miembro a un grupo"""
        headers = self._get_supabase_headers()
        
        member = {
            "group_id": group_id,
            "user_id": user_id,
            "is_admin": is_admin,
            "status": status,
            "joined_at": datetime.datetime.now().isoformat()
        }
        
        # Insertar en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            json=member
        )
        
        return response.status_code == 201

    def verify_group_member(self, group_id, user_id):
        """Verificar un miembro de grupo"""
        headers = self._get_supabase_headers()
        
        # Actualizar estado del miembro
        update_data = {"status": "verified"}
        
        # Actualizar en Supabase
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}"},
            json=update_data
        )
        
        return response.status_code == 204

    def get_user_groups(self, user_id):
        """Obtener grupos a los que pertenece un usuario"""
        headers = self._get_supabase_headers()
        
        print(f"Buscando grupos para el usuario: {user_id}")
        
        # Obtener membresías del usuario
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"user_id": f"eq.{user_id}"}
        )
        
        # Depurar la respuesta
        print(f"Status code memberships: {response.status_code}")
        print(f"Response memberships: {response.text}")
        
        groups = []
        
        if response.status_code == 200:
            memberships = response.json()
            
            for membership in memberships:
                group_response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/groups",
                    headers=headers,
                    params={"id": f"eq.{membership['group_id']}"}
                )
                
                # Depurar la respuesta
                print(f"Status code group: {group_response.status_code}")
                print(f"Response group: {group_response.text}")
                
                if group_response.status_code == 200 and group_response.json():
                    group = group_response.json()[0]
                    group['is_admin'] = membership['is_admin']
                    group['status'] = membership['status']
                    groups.append(group)
        
        # Siempre buscar grupos donde el usuario es administrador, independientemente de si ya encontramos grupos
        print(f"Buscando grupos donde el usuario es administrador")
        admin_groups_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            params={"admin_id": f"eq.{user_id}"}
        )
        
        # Depurar la respuesta
        print(f"Status code admin groups: {admin_groups_response.status_code}")
        print(f"Response admin groups: {admin_groups_response.text}")
        
        if admin_groups_response.status_code == 200 and admin_groups_response.json():
            for admin_group in admin_groups_response.json():
                # Verificar si este grupo ya está en la lista
                group_already_added = False
                for existing_group in groups:
                    if existing_group['id'] == admin_group['id']:
                        group_already_added = True
                        break
                
                if not group_already_added:
                    # Verificar si ya existe una membresía para este grupo
                    member_check = requests.get(
                        f"{SUPABASE_URL}/rest/v1/group_members",
                        headers=headers,
                        params={"group_id": f"eq.{admin_group['id']}", "user_id": f"eq.{user_id}"}
                    )
                    
                    print(f"Verificando membresía para grupo {admin_group['id']}")
                    print(f"Status code member check: {member_check.status_code}")
                    print(f"Response member check: {member_check.text}")
                    
                    if member_check.status_code != 200 or not member_check.json():
                        # Si no existe, añadir al usuario como miembro verificado
                        print(f"Añadiendo al usuario como miembro verificado del grupo {admin_group['id']}")
                        self.add_group_member(admin_group['id'], user_id, is_admin=True, status='verified')
                    
                    # Añadir el grupo a la lista con los atributos necesarios
                    admin_group['is_admin'] = True
                    admin_group['status'] = 'verified'
                    groups.append(admin_group)
        
        print(f"Total de grupos encontrados: {len(groups)}")
        return groups

    def add_group_content(self, group_id, admin_id, content_type, content_data, file_size=0):
        """Añadir contenido compartido a un grupo"""
        headers = self._get_supabase_headers()
        
        # Verificar que el usuario es administrador del grupo
        admin_check = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"group_id": f"eq.{group_id}", "user_id": f"eq.{admin_id}", "is_admin": "is.true"}
        )
        
        if admin_check.status_code != 200 or not admin_check.json():
            return False, "Solo los administradores pueden añadir contenido"
        
        # Crear contenido
        content_id = str(uuid.uuid4())
        content = {
            "id": content_id,
            "group_id": group_id,
            "added_by": admin_id,
            "content_type": content_type,
            "content_data": content_data,
            "file_size_bytes": file_size,
            "created_at": datetime.datetime.now().isoformat(),
            # Añadir los campos faltantes directamente desde content_data
            "file_path": content_data.get("file_path"),
            "file_type": content_data.get("file_type"),
            "file": content_data.get("file")
        }
        # Imprimir el contenido para depuración
        print("Contenido a guardar:")
        print(content)
        
        # Insertar en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/group_contents",
            headers=headers,
            json=content
        )
        
        # Imprimir información de depuración
        print(f"Status code group_contents: {response.status_code}")
        print(f"Response group_contents: {response.text}")
        
        # Actualizar almacenamiento usado por el grupo
        if response.status_code == 201:
            self.update_group_storage(group_id, file_size)
            return True, content_id
        
        return False, "Error al añadir contenido"

    def update_group_storage(self, group_id, added_bytes):
        """Actualizar el almacenamiento usado por un grupo"""
        headers = self._get_supabase_headers()
        
        # Obtener almacenamiento actual
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            params={"id": f"eq.{group_id}"}
        )
        
        if response.status_code == 200 and response.json():
            group = response.json()[0]
            current_storage = group.get('shared_storage_bytes', 0)
            new_storage = current_storage + added_bytes
            
            # Actualizar almacenamiento
            update_data = {"shared_storage_bytes": new_storage}
            update_response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/groups",
                headers=headers,
                params={"id": f"eq.{group_id}"},
                json=update_data
            )
            
            return update_response.status_code == 204
        
        return False
    def upload_and_vectorize_file(self, group_id, user_id, file, content_type):
        """Subir archivo, procesarlo y vectorizarlo para IA"""
        headers = self._get_supabase_headers()
        
        # Verificar que el usuario es administrador del grupo
        admin_check = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}", "is_admin": "is.true"}
        )
        
        if admin_check.status_code != 200 or not admin_check.json():
            return False, "Solo los administradores pueden subir contenido"
        
        # 1. Subir archivo a Supabase Storage
        file_name = file.filename
        file_path = f"groups/{group_id}/{file_name}"
        file_size = len(file.read())
        file.seek(0)  # Reiniciar puntero del archivo
        
        # Subir archivo a Supabase Storage (bucket público "telegrambucket")
        storage_url = f"{SUPABASE_URL}/storage/v1/object/telegrambucket/{file_path}"
        
        # Preparar headers para la subida de archivos
        upload_headers = headers.copy()
        # Eliminar Content-Type para que requests lo establezca automáticamente con el boundary correcto
        if 'Content-Type' in upload_headers:
            del upload_headers['Content-Type']
        
        # Subir el archivo
        files = {
            'file': (file_name, file, 'application/octet-stream')
        }
        
        upload_response = requests.post(
            storage_url,
            headers=upload_headers,
            files=files
        )
        
        print(f"Status code upload: {upload_response.status_code}")
        print(f"Response upload: {upload_response.text}")
        
        if upload_response.status_code not in [200, 201]:
            return False, f"Error al subir archivo: {upload_response.text}"
        
        # Generar URL pública para el archivo
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/telegrambucket/{file_path}"
        # Limpiar caracteres problemáticos
        file_url = file_url.replace('`', '').strip()
        
        # 2. Procesar el contenido según el tipo
        text_content = ""
        if content_type == 'text':
            file.seek(0)  # Reiniciar puntero del archivo
            text_content = file.read().decode('utf-8')
        elif content_type == 'pdf':
            # Aquí usarías una biblioteca como PyPDF2 o pdfminer para extraer texto
            # Por ahora, simulamos
            text_content = f"Contenido extraído del PDF {file_name}"
        elif content_type == 'image':
            # Para imágenes, podríamos usar OCR en un entorno real
            # Por ahora, simplemente usamos un texto descriptivo
            text_content = f"Imagen: {file_name}"
        
        import numpy as np
        import json
        
        # Generar un vector aleatorio y asegurarnos de que no tenga valores NaN o infinitos
        embedding_array = np.random.rand(1536)  # Ajusta esta dimensión si es necesario
        
        # Convertir a lista de Python y redondear a 6 decimales para evitar problemas de precisión
        embedding = [float(round(x, 6)) for x in embedding_array.tolist()]
        
        # Verificar que no haya valores NaN o infinitos
        embedding = [0.0 if np.isnan(x) or np.isinf(x) else x for x in embedding]
        
        # Asegurarse de que metadata sea un objeto JSON válido
        metadata = {
            "filename": file_name,
            "content_type": content_type,
            "file_size": file_size,
            "file_url": file_url
        }
        
        # Validar que metadata sea serializable
        try:
            json.dumps(metadata)
        except (TypeError, OverflowError) as e:
            return False, f"Error en formato de metadata: {str(e)}"
        
        # 4. Guardar documento en la tabla documents
        document = {
            "title": file_name,  
            "content": text_content,
            "file_type": content_type,  
            "file_path": file_url,  
            "file_size": file_size,  
            "metadata": metadata,
            "embedding": embedding
        }
        
        # Insertar en Supabase
        document_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/documents",
            headers=headers,
            json=document
        )
        
        # Imprimir información de depuración
        print(f"Status code document: {document_response.status_code}")
        print(f"Response document: {document_response.text}")
        
        if document_response.status_code != 201:
            return False, f"Error al guardar documento vectorizado: {document_response.text}"
        
        # Obtener ID del documento creado
        document_id = None
        try:
            # Intentar obtener el ID del documento de la respuesta
            document_id = json.loads(document_response.text).get('id')
        except:
            # Si no se puede obtener de la respuesta, buscar por contenido
            get_doc_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={"content": f"eq.{text_content}"}
            )
            
            if get_doc_response.status_code == 200 and get_doc_response.json():
                document_id = get_doc_response.json()[0]['id']
            else:
                return False, "Error al obtener ID del documento"
        
        # 5. Relacionar documento con el grupo
        group_document = {
            "group_id": group_id,
            "document_id": document_id,
            "added_by": user_id
        }
        
        group_doc_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/group_documents",
            headers=headers,
            json=group_document
        )
        
        if group_doc_response.status_code != 201:
            return False, "Error al relacionar documento con grupo"
        
        # 6. Registrar el contenido en group_contents para compatibilidad
        content_data = {
            "filename": file_name,
            "file_url": file_url,
            "document_id": document_id,
            "file_path": file_path,  # Añadir file_path
            "file_type": content_type,  # Añadir file_type
            "file": file_name  # Añadir file (usando el nombre del archivo)
        }
        
        success, content_id = self.add_group_content(group_id, user_id, content_type, content_data, file_size)
        
        if not success:
            return False, "Error al registrar contenido en el grupo"
        
        # 7. Actualizar almacenamiento usado por el grupo
        self.update_group_storage(group_id, file_size)
        
        return True, content_id
    def get_group_contents(self, group_id, user_id):
        """Obtener contenidos de un grupo (solo para miembros verificados)"""
        headers = self._get_supabase_headers()
        import json
        
        # Verificar que el usuario es miembro verificado del grupo
        member_check = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}", "status": "eq.verified"}
        )
        
        if member_check.status_code != 200 or not member_check.json():
            return False, "Solo los miembros verificados pueden ver el contenido"
        
        # Obtener contenidos
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_contents",
            headers=headers,
            params={"group_id": f"eq.{group_id}"}
        )
        
        if response.status_code == 200:
            contents = response.json()
            
            # Procesar cada contenido para asegurar que content_data sea un objeto
            for content in contents:
                if isinstance(content.get('content_data'), str):
                    try:
                        content['content_data'] = json.loads(content['content_data'])
                    except json.JSONDecodeError:
                        # Si no se puede parsear, dejarlo como está
                        pass
                        
            return True, contents
        
        return False, "Error al obtener contenidos"

    def invite_to_group(self, group_id, admin_id, email=None, phone=None):
        """Invitar a un usuario a un grupo mediante email o teléfono"""
        headers = self._get_supabase_headers()
        
        # Verificar que el administrador tiene permisos
        admin_check = requests.get(
            f"{SUPABASE_URL}/rest/v1/group_members",
            headers=headers,
            params={"group_id": f"eq.{group_id}", "user_id": f"eq.{admin_id}", "is_admin": "is.true"}
        )
        
        if admin_check.status_code != 200 or not admin_check.json():
            return False, "Solo los administradores pueden invitar miembros"
        
        # Obtener información del grupo
        group_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            params={"id": f"eq.{group_id}"}
        )
        
        if group_response.status_code != 200 or not group_response.json():
            return False, "Grupo no encontrado"
            
        group = group_response.json()[0]
        verification_type = group.get('verification_type', 'email')
        
        # Buscar si el usuario ya existe
        user_id = None
        if email:
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"email": f"eq.{email.lower()}"}
            )
            if user_response.status_code == 200 and user_response.json():
                user_id = user_response.json()[0]['id']
        
        if not user_id and phone:
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"phone": f"eq.{phone}"}
            )
            if user_response.status_code == 200 and user_response.json():
                user_id = user_response.json()[0]['id']
        
        # Generar código de verificación
        import secrets
        verification_code = secrets.token_hex(3)  # Código de 6 caracteres
        
        # Fecha de expiración (24 horas)
        expires_at = (datetime.datetime.now() + 
                      datetime.timedelta(hours=24)).isoformat()
        
        # Crear invitación
        invitation = {
            "group_id": group_id,
            "invited_by": admin_id,
            "verification_type": verification_type,
            "verification_code": verification_code,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": expires_at,
            "status": "pending"
        }
        
        # Añadir user_id si existe
        if user_id:
            invitation["user_id"] = user_id
        
        # Añadir email o teléfono según corresponda
        if email:
            invitation["email"] = email.lower()
        if phone:
            invitation["phone"] = phone
        
        # Insertar en Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/group_invitations",
            headers=headers,
            json=invitation
        )
        
        if response.status_code == 201:
            # Si el usuario existe, añadirlo como miembro pendiente
            if user_id:
                self.add_group_member(group_id, user_id, is_admin=False, status='pending')
            
            # Aquí implementarías el envío de la notificación
            # Por email o SMS según verification_type
            if verification_type == 'email' and email:
                self._send_email_invitation(email, group['name'], verification_code)
            elif verification_type == 'phone' and phone:
                self._send_sms_invitation(phone, group['name'], verification_code)
            
            return True, verification_code
        
        return False, "Error al crear invitación"
    
    def _send_email_invitation(self, email, group_name, verification_code):
        """Enviar invitación por email (implementación simulada)"""
        # Aquí implementarías el envío real de emails
        # Puedes usar servicios como SendGrid, Mailgun, etc.
        logging.info(f"Enviando invitación por email a {email} para el grupo {group_name}")
        logging.info(f"Código de verificación: {verification_code}")
        
        # Ejemplo de implementación con SendGrid (requiere instalar sendgrid)
        # import sendgrid
        # from sendgrid.helpers.mail import Mail, Email, To, Content
        # sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        # from_email = Email("tu@email.com")
        # to_email = To(email)
        # subject = f"Invitación al grupo {group_name}"
        # content = Content("text/plain", f"Has sido invitado al grupo {group_name}. Tu código de verificación es: {verification_code}")
        # mail = Mail(from_email, to_email, subject, content)
        # response = sg.client.mail.send.post(request_body=mail.get())
        
        return True
    
    def _send_sms_invitation(self, phone, group_name, verification_code):
        """Enviar invitación por SMS (implementación simulada)"""
        # Aquí implementarías el envío real de SMS
        # Puedes usar servicios como Twilio, Nexmo, etc.
        logging.info(f"Enviando invitación por SMS a {phone} para el grupo {group_name}")
        logging.info(f"Código de verificación: {verification_code}")
        
        # Ejemplo de implementación con Twilio (requiere instalar twilio)
        # from twilio.rest import Client
        # account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        # auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"Has sido invitado al grupo {group_name}. Tu código de verificación es: {verification_code}",
        #     from_='+1234567890',  # Tu número de Twilio
        #     to=phone
        # )
        
        return True    

    def update_user_tokens(self, user_id, tokens_used):
        """Actualizar los tokens usados por un usuario"""
        headers = self._get_supabase_headers()
        
        # Obtener datos actuales del usuario
        user = self.get_user_by_id(user_id)  # Cambiar get_user por get_user_by_id
        if not user:
            return False
        
        current_tokens_used = user.get("tokens_used", 0)
        
        # Actualizar tokens
        update_data = {
            "tokens_used": current_tokens_used + tokens_used
        }
        
        # Actualizar en Supabase
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            params={"id": f"eq.{user_id}"},
            json=update_data
        )
        
        return response.status_code == 204
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
            
            # Obtener documentos del grupo usando la tabla group_documents con select específico
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/group_documents",
                headers=headers,
                params={
                    "group_id": f"eq.{group_id}",
                    "select": "id,created_at,documents(id,title,content,file_type,file_path,file_size,metadata,created_at)",
                    "order": "created_at.desc",
                    "limit": str(limit)
                }
            )
            
            print(f"Debug - Status code: {response.status_code}")
            print(f"Debug - Response: {response.text}")
            
            if response.status_code == 200:
                group_docs = response.json()
                documents = []
                
                for group_doc in group_docs:
                    # Verificar que documents existe y no es None
                    if group_doc.get('documents') and isinstance(group_doc['documents'], dict):
                        doc = group_doc['documents']
                        # Verificar que el documento tiene los campos requeridos
                        if doc.get('id'):
                            # Extraer información del metadata si existe
                            metadata = doc.get('metadata', {})
                            if isinstance(metadata, dict):
                                filename = metadata.get('filename', doc.get('title', 'Sin nombre'))
                                file_type = metadata.get('content_type', doc.get('file_type', 'unknown'))
                                file_url = metadata.get('file_url', '')
                                file_size = metadata.get('file_size', doc.get('file_size', 0))
                            else:
                                filename = doc.get('title', 'Sin nombre')
                                file_type = doc.get('file_type', 'unknown')
                                file_url = doc.get('file_path', '')
                                file_size = doc.get('file_size', 0)
                            
                            documents.append({
                                'id': doc['id'],
                                'title': doc.get('title', filename),
                                'filename': filename,
                                'content': doc.get('content', ''),
                                'file_type': file_type,
                                'file_path': file_url,
                                'created_at': doc.get('created_at', ''),
                                'file_size': file_size
                            })
                
                return True, documents
            
            return False, []
            
        except Exception as e:
            logging.error(f"Error obteniendo documentos del usuario: {e}")
            print(f"Debug - Exception: {e}")
            return False, []
    def get_personal_group_contents(self, user_id, limit=20):
        """Obtener contenidos del grupo personal del usuario"""
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
            
            # Obtener documentos del grupo usando la tabla group_documents con select específico
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/group_documents",
                headers=headers,
                params={
                    "group_id": f"eq.{group_id}",
                    "select": "id,created_at,documents(id,title,content,file_type,file_path,file_size,metadata,created_at)",
                    "order": "created_at.desc",
                    "limit": str(limit)
                }
            )
            
            if response.status_code == 200:
                group_docs = response.json()
                documents = []
                
                for group_doc in group_docs:
                    # Verificar que documents existe y no es None
                    if group_doc.get('documents') and isinstance(group_doc['documents'], dict):
                        doc = group_doc['documents']
                        # Verificar que el documento tiene los campos requeridos
                        if doc.get('id'):
                            # Extraer información del metadata si existe
                            metadata = doc.get('metadata', {})
                            if isinstance(metadata, dict):
                                filename = metadata.get('filename', doc.get('title', 'Sin nombre'))
                                file_type = metadata.get('content_type', doc.get('file_type', 'unknown'))
                                file_url = metadata.get('file_url', '')
                                file_size = metadata.get('file_size', doc.get('file_size', 0))
                            else:
                                filename = doc.get('title', 'Sin nombre')
                                file_type = doc.get('file_type', 'unknown')
                                file_url = doc.get('file_path', '')
                                file_size = doc.get('file_size', 0)
                            
                            documents.append({
                                'id': doc['id'],
                                'title': doc.get('title', filename),
                                'filename': filename,
                                'content': doc.get('content', ''),
                                'file_type': file_type,
                                'file_path': file_url,
                                'created_at': doc.get('created_at', ''),
                                'file_size': file_size,
                                'file_size_bytes': file_size  # Añadido para compatibilidad con la plantilla
                            })
                
                return True, documents
            
            return False, []
            
        except Exception as e:
            logging.error(f"Error obteniendo documentos del grupo personal: {e}")
            print(f"Debug - Exception: {e}")
            return False, []

    def create_invitation(self, invitation_data):
        headers = self._get_supabase_headers()
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/invitations",
            headers=headers,
            json=invitation_data
        )
        if response.status_code == 201:
            return True, response.json().get('id')
        return False, None

    def update_invitation_status(self, invitation_id, status):
        headers = self._get_supabase_headers()
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/invitations?id=eq.{invitation_id}",
            headers=headers,
            json={'status': status}
        )
        return response.status_code == 200

    def get_group_name(self, group_id):
        headers = self._get_supabase_headers()
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups?id=eq.{group_id}",
            headers=headers
        )
        if response.status_code == 200 and response.json():
            return response.json()[0].get('name')
        return None


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
        """Obtener documentos del usuario para usar como contexto automático usando búsqueda vectorial"""
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
            
            # Realizar búsqueda vectorial usando la función pgvector de Supabase
            search_response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/search_documents",
                headers=headers,
                json={
                    "query_text": query_text,
                    "group_id": group_id,
                    "match_limit": limit
                }
            )
            
            if search_response.status_code == 200:
                documents = search_response.json()
                
                # Limitar el contenido para no sobrecargar el contexto
                context_docs = []
                for doc in documents:
                    context_doc = {
                        'id': doc['id'],
                        'title': doc['title'],
                        'content': doc['content'][:1000] + "..." if len(doc['content']) > 1000 else doc['content'],
                        'file_type': doc['file_type'],
                        'file_path': doc['file_path'],
                        'created_at': doc['created_at']
                    }
                    context_docs.append(context_doc)
                
                return True, context_docs
            
            # Si la búsqueda vectorial falla, volver al método anterior de documentos recientes
            logging.warning("Búsqueda vectorial falló, usando documentos recientes como respaldo")
            success, all_docs = self.get_user_documents(user_id, limit)
            
            if success:
                context_docs = []
                for doc in all_docs:
                    context_doc = doc.copy()
                    if len(context_doc['content']) > 1000:
                        context_doc['content'] = context_doc['content'][:1000] + "..."
                    context_docs.append(context_doc)
                
                return True, context_docs
            
            return False, []
            
        except Exception as e:
            logging.error(f"Error en búsqueda vectorial: {e}")
            # Intentar método de respaldo
            return self.get_user_documents(user_id, limit)