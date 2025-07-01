from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import UserDatabase
import os
import secrets
import requests  # Añadir esta importación
from dotenv import load_dotenv 

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Clave secreta aleatoria

# Inicializar la base de datos
db = UserDatabase()


# Definir planes disponibles
PLANS = {
    'lite_monthly': {
        'id': 'lite_monthly',
        'name': 'Plan Lite Mensual',
        'storage': 0.1, # GB (100 MB)
        'tokens': 500000,
        'price': 2490,
        'description': 'Plan básico con almacenamiento limitado y tokens para IA.',
        'duration': 30, # días
        'duration_type': 'mensual'
    },
    'lite_annual': {
        'id': 'lite_annual',
        'name': 'Plan Lite Anual',
        'storage': 0.1, # GB (100 MB)
        'tokens': 500000,
        'price': 24900,
        'description': 'Plan básico con almacenamiento limitado y tokens para IA.',
        'duration': 365, # días
        'duration_type': 'anual'
    },
    'pro_monthly': {
        'id': 'pro_monthly',
        'name': 'Plan Pro Mensual',
        'storage': 0.4, # GB (400 MB)
        'tokens': 3000000,
        'price': 4990,
        'description': 'Plan profesional con mayor almacenamiento y 6 veces más tokens que Lite.',
        'duration': 30, # días
        'duration_type': 'mensual'
    },
    'pro_annual': {
        'id': 'pro_annual',
        'name': 'Plan Pro Anual',
        'storage': 0.4, # GB (400 MB)
        'tokens': 3000000,
        'price': 49900,
        'description': 'Plan profesional con mayor almacenamiento y 6 veces más tokens que Lite.',
        'duration': 365, # días
        'duration_type': 'anual'
    },
    'empresa_monthly': {
        'id': 'empresa_monthly',
        'name': 'Plan Empresa Mensual',
        'storage': 1, # GB (1024 MB)
        'tokens': 9000000,
        'price': 11990,
        'description': 'Plan empresarial con almacenamiento completo y 3 veces más tokens que Pro.',
        'duration': 30, # días
        'duration_type': 'mensual'
    },
    'empresa_annual': {
        'id': 'empresa_annual',
        'name': 'Plan Empresa Anual',
        'storage': 1, # GB (1024 MB)
        'tokens': 9000000,
        'price': 119900,
        'description': 'Plan empresarial con almacenamiento completo y 3 veces más tokens que Pro.',
        'duration': 365, # días
        'duration_type': 'anual'
    }
}


# Rutas para la administración (existentes)
@app.route('/admin')
def index():
    # Verificar si el usuario es administrador
    if not is_admin():
        flash('Acceso denegado', 'danger')
        return redirect(url_for('login'))
    
    # Obtener todos los usuarios
    users = db.get_all_users()
    return render_template('admin/index.html', users=users)

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    # Verificar si el usuario es administrador
    if not is_admin():
        flash('Acceso denegado', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        
        try:
            user_id = int(user_id)
            user_data = {
                'username': username,
                'first_name': first_name,
                'added_by': 'web_interface',
                'status': 'active'
            }
            
            db.add_user(user_id, user_data)
            flash('Usuario añadido correctamente', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('El ID de usuario debe ser un número', 'danger')
    
    return render_template('admin/add_user.html')

@app.route('/admin/remove_user/<user_id>', methods=['POST'])
def remove_user(user_id):
    # Verificar si el usuario es administrador
    if not is_admin():
        flash('Acceso denegado', 'danger')
        return redirect(url_for('login'))
    
    try:
        user_id = int(user_id)
        if db.remove_user(user_id):
            flash('Usuario eliminado correctamente', 'success')
        else:
            flash('Usuario no encontrado', 'danger')
    except ValueError:
        flash('ID de usuario inválido', 'danger')
    
    return redirect(url_for('index'))

# Nuevas rutas para usuarios
@app.route('/')
def home():
    # Si el usuario está logueado, redirigir al dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # Si no, mostrar la página de inicio
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        telegram_id = request.form.get('telegram_id')
        
        # Validar datos
        if not email or not password:
            flash('Por favor, completa todos los campos obligatorios', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('register.html')
        
        # Registrar usuario
        success, message = db.register_web_user(email, password, telegram_id)
        
        if success:
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validar credenciales
        success, message = db.login_web_user(email, password)
        
        if success:
            # Guardar ID de usuario en la sesión
            session['user_id'] = message
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Eliminar datos de sesión
    session.pop('user_id', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder', 'danger')
        return redirect(url_for('login'))
    
    # Obtener datos del usuario
    user_id = session['user_id']
    user_data = db.get_user_by_id(user_id) 
    
    if not user_data:
        session.pop('user_id', None)
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('login'))
    
    # Calcular almacenamiento usado y disponible
    storage_used = user_data.get('storage_used', 0) / (1024 * 1024 * 1024)  # Convertir a GB
    
    # Obtener plan actual
    current_plan_id = user_data.get('current_plan_id') 
    storage_limit = 0

    if current_plan_id and current_plan_id in PLANS:
        storage_limit = PLANS[current_plan_id]['storage']
    
    # Verificar si el plan está activo
    plan_active = False
    if user_data.get('plan_expiration'):
        import datetime
        expiration_date = datetime.datetime.fromisoformat(user_data['plan_expiration'])
        plan_active = expiration_date > datetime.datetime.now()
    
    return render_template('dashboard.html', 
                           user=user_data, 
                           storage_used=storage_used,
                           storage_limit=storage_limit,
                           plan_active=plan_active)

@app.route('/plans')
def plans():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver los planes', 'danger')
        return redirect(url_for('login'))
    
    return render_template('plans.html', plans=PLANS)

@app.route('/buy_plan/<plan_id>', methods=['GET', 'POST'])
def buy_plan(plan_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para comprar un plan', 'danger')
        return redirect(url_for('login'))
    
    # Verificar si el plan existe
    if plan_id not in PLANS:
        flash('Plan no válido', 'danger')
        return redirect(url_for('plans'))
    
    if request.method == 'POST':
        # Aquí implementarías la integración con Mercado Pago
        # Por ahora, simularemos una compra exitosa
        
        user_id = session['user_id']
        plan = PLANS[plan_id]
        
        # Registrar la orden (tanto para compra normal como temporal)
        success, order_id = db.add_order(user_id, plan_id, plan['price'])
        
        if success:
            # Agregar logs para depuración
            print(f"Actualizando plan para usuario: {user_id}, plan: {plan_id}, duración: {plan['duration']}")
            
            # Actualizar el plan del usuario con la duración correspondiente
            update_success = db.update_user_plan(user_id, plan_id, expiration_days=plan['duration'])
            print(f"Resultado de actualización de plan: {update_success}")
            
            # Mensaje específico según el tipo de compra
            if 'temp_complete' in request.form:
                flash(f'¡Has adquirido el {plan["name"]} temporalmente con éxito!', 'success')
            else:
                flash(f'¡Has adquirido el {plan["name"]} con éxito!', 'success')
                
            return redirect(url_for('dashboard'))
        else:
            # Registrar el error para depuración
            print(f"Error al procesar la orden: {order_id}")
            flash('Error al procesar la orden', 'danger')
    
    plan = PLANS[plan_id]
    return render_template('buy_plan.html', plan=plan)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver tu perfil', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = db.get_user_by_id(user_id)
    
    if request.method == 'POST':
        # Actualizar datos del perfil
        # Aquí implementarías la lógica para actualizar el perfil
        flash('Perfil actualizado correctamente', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=user_data)

@app.route('/orders')
def orders():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver tus órdenes', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = db.get_user_by_id(user_id)
    
    # Obtener órdenes del usuario
    orders = user_data.get('orders', [])
    
    return render_template('orders.html', orders=orders, plans=PLANS)

def is_admin():
    # Verificar si el usuario actual es administrador
    if 'user_id' in session:
        user_id = session['user_id']
        user_data = db.get_user(user_id)
        return user_data and user_data.get('role') == 'admin'
    return False



@app.template_filter('format_number')
def format_number(value):
    """Formatear números grandes con separadores de miles"""
    return f"{value:,}".replace(',', '.')


@app.route('/groups')
def groups():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver tus grupos', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = db.get_user_by_id(user_id)
    
    # Verificar si el usuario tiene un plan activo
    plan_active = False
    if user_data.get('plan_expiration'):
        import datetime
        expiration_date = datetime.datetime.fromisoformat(user_data['plan_expiration'])
        plan_active = expiration_date > datetime.datetime.now()
    
    if not plan_active:
        flash('Necesitas un plan activo para usar grupos', 'warning')
        return redirect(url_for('plans'))
    
    # Obtener grupos del usuario
    groups = db.get_user_groups(user_id)
    
    return render_template('groups.html', groups=groups, user=user_data)

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para crear un grupo', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = db.get_user_by_id(user_id)
    
    # Verificar si el usuario tiene un plan activo
    plan_active = False
    if user_data.get('plan_expiration'):
        import datetime
        expiration_date = datetime.datetime.fromisoformat(user_data['plan_expiration'])
        plan_active = expiration_date > datetime.datetime.now()
    
    if not plan_active:
        flash('Necesitas un plan activo para crear grupos', 'warning')
        return redirect(url_for('plans'))
    
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        verification_type = request.form.get('verification_type', 'phone')
        
        if not group_name:
            flash('El nombre del grupo es obligatorio', 'danger')
            return redirect(url_for('create_group'))
        
        success, group_id = db.create_group(user_id, group_name, verification_type)
        
        if success:
            flash(f'Grupo "{group_name}" creado con éxito', 'success')
            return redirect(url_for('group_detail', group_id=group_id))
        else:
            flash('Error al crear el grupo', 'danger')
    
    return render_template('create_group.html')

@app.route('/group/<group_id>')
def group_detail(group_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver detalles del grupo', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Obtener detalles del grupo
    headers = db._get_supabase_headers()
    
    # Verificar que el usuario es miembro del grupo
    member_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members",
        headers=headers,
        params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}"}
    )
    
    # Depurar la respuesta
    print(f"Status code: {member_check.status_code}")
    print(f"Response: {member_check.text}")
    
    membership = None
    
    if member_check.status_code != 200 or not member_check.json():
        # Verificar si el usuario es el administrador del grupo
        group_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/groups",
            headers=headers,
            params={"id": f"eq.{group_id}", "admin_id": f"eq.{user_id}"}
        )
        
        if group_response.status_code == 200 and group_response.json():
            # El usuario es el administrador, añadirlo como miembro verificado
            db.add_group_member(group_id, user_id, is_admin=True, status='verified')
            # Obtener la membresía recién creada
            member_check = requests.get(
                f"{SUPABASE_URL}/rest/v1/group_members",
                headers=headers,
                params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}"}
            )
            if member_check.status_code == 200 and member_check.json():
                membership = member_check.json()[0]
            else:
                # Si aún no podemos obtener la membresía, crear una temporal
                membership = {
                    "is_admin": True,
                    "status": "verified"
                }
        else:
            flash('No tienes acceso a este grupo', 'danger')
            return redirect(url_for('groups'))
    else:
        membership = member_check.json()[0]
    
    # Verificar que membership no sea None antes de continuar
    if membership is None:
        flash('Error al obtener información de membresía', 'danger')
        return redirect(url_for('groups'))
    
    # Obtener información del grupo
    group_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/groups",
        headers=headers,
        params={"id": f"eq.{group_id}"}
    )
    
    if group_response.status_code != 200 or not group_response.json():
        flash('Grupo no encontrado', 'danger')
        return redirect(url_for('groups'))
    
    group = group_response.json()[0]
    
    # Obtener miembros del grupo
    members_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members",
        headers=headers,
        params={"group_id": f"eq.{group_id}"}
    )
    
    members = []
    if members_response.status_code == 200:
        for member in members_response.json():
            user_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                params={"id": f"eq.{member['user_id']}"}
            )
            
            if user_response.status_code == 200 and user_response.json():
                user = user_response.json()[0]
                members.append({
                    'user_id': member['user_id'],
                    'email': user.get('email', 'Sin email'),
                    'is_admin': member['is_admin'],
                    'status': member['status'],
                    'joined_at': member['joined_at']
                })
    
    # Obtener contenidos si el usuario está verificado
    contents = []
    if membership['status'] == 'verified':
        success, content_data = db.get_group_contents(group_id, user_id)
        if success:
            contents = content_data
    
    return render_template('group_detail.html', 
                           group=group, 
                           members=members, 
                           contents=contents, 
                           is_admin=membership['is_admin'],
                           is_verified=membership['status'] == 'verified')

@app.route('/group/<group_id>/invite', methods=['GET', 'POST'])
def invite_to_group(group_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para invitar a un grupo', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Obtener información del grupo
    headers = db._get_supabase_headers()
    group_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/groups",
        headers=headers,
        params={"id": f"eq.{group_id}"}
    )
    
    if group_response.status_code != 200 or not group_response.json():
        flash('Grupo no encontrado', 'danger')
        return redirect(url_for('groups'))
    
    group = group_response.json()[0]
    verification_type = group.get('verification_type', 'email')
    
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Validar datos según tipo de verificación
        if verification_type == 'email' and not email:
            flash('El email es obligatorio', 'danger')
            return redirect(url_for('invite_to_group', group_id=group_id))
        elif verification_type == 'phone' and not phone:
            flash('El teléfono es obligatorio', 'danger')
            return redirect(url_for('invite_to_group', group_id=group_id))
        
        # Enviar invitación
        success, message = db.invite_to_group(group_id, user_id, email=email, phone=phone)
        
        if success:
            flash(f'Invitación enviada con éxito. Código de verificación: {message}', 'success')
            return redirect(url_for('group_detail', group_id=group_id))
        else:
            flash(f'Error al enviar invitación: {message}', 'danger')
    
    return render_template('invite_to_group.html', group=group, verification_type=verification_type)

@app.route('/group/<group_id>/verify/<user_id>', methods=['POST'])
def verify_group_member(group_id, user_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para verificar miembros', 'danger')
        return redirect(url_for('login'))
    
    admin_id = session['user_id']
    
    # Verificar que el usuario actual es administrador del grupo
    headers = db._get_supabase_headers()
    params = { 
        "group_id": f"eq.{group_id}", 
        "user_id": f"eq.{admin_id}", 
        "is_admin": "is.true" 
    } 
    
    admin_check = requests.get( 
        f"{SUPABASE_URL}/rest/v1/group_members", 
        headers=headers, 
        params=params 
    )
    
    if admin_check.status_code != 200 or not admin_check.json():
        flash('Solo los administradores pueden verificar miembros', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Verificar miembro
    success = db.verify_group_member(group_id, user_id)
    
    if success:
        flash('Miembro verificado con éxito', 'success')
    else:
        flash('Error al verificar miembro', 'danger')
    
    return redirect(url_for('group_detail', group_id=group_id))
@app.route('/group/<group_id>/content/<content_id>', methods=['GET'])
def view_group_content(group_id, content_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver el contenido', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Verificar que el usuario es miembro verificado del grupo
    headers = db._get_supabase_headers()
    member_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members",
        headers=headers,
        params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}", "status": "eq.verified"}
    )
    
    if member_check.status_code != 200 or not member_check.json():
        flash('Solo los miembros verificados pueden ver el contenido', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Obtener información del contenido
    content_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_contents",
        headers=headers,
        params={"id": f"eq.{content_id}"}
    )
    
    if content_response.status_code != 200 or not content_response.json():
        flash('Contenido no encontrado', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    content = content_response.json()[0]
    
    # Verificar que el contenido pertenece al grupo
    if content['group_id'] != group_id:
        flash('El contenido no pertenece a este grupo', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Procesar content_data si es un string JSON
    import json
    if isinstance(content.get('content_data'), str):
        try:
            content['content_data'] = json.loads(content['content_data'])
        except json.JSONDecodeError:
            pass
    
    # Determinar cómo mostrar el contenido según su tipo
    content_type = content['content_type']
    
    if content_type == 'pdf':
        # Para PDFs, redirigir a la URL del archivo o mostrar en un visor de PDF
        file_url = content.get('content_data', {}).get('file_url')
        if file_url:
            # En un entorno real, aquí podrías generar una URL firmada para Supabase Storage
            # Por ahora, como es una URL simulada, simplemente mostramos una página con un visor de PDF
            return render_template('view_pdf.html', 
                                  content=content, 
                                  file_url=file_url,
                                  filename=content.get('file'))
    
    elif content_type == 'image':
        # Para imágenes, mostrar la imagen
        file_url = content.get('content_data', {}).get('file_url')
        if file_url:
            return render_template('view_image.html', 
                                  content=content, 
                                  file_url=file_url,
                                  filename=content.get('file'))
    
    elif content_type == 'text':
        # Para texto, mostrar el contenido de texto
        document_id = content.get('content_data', {}).get('document_id')
        if document_id:
            # Obtener el contenido del documento
            doc_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=headers,
                params={"id": f"eq.{document_id}"}
            )
            
            if doc_response.status_code == 200 and doc_response.json():
                document = doc_response.json()[0]
                text_content = document.get('content', '')
                return render_template('view_text.html', 
                                      content=content, 
                                      text_content=text_content,
                                      filename=content.get('file'))
    
    # Si llegamos aquí, no pudimos mostrar el contenido
    flash('No se puede mostrar este tipo de contenido', 'warning')
    return redirect(url_for('group_detail', group_id=group_id))
@app.route('/group/<group_id>/content/<content_id>/download', methods=['GET'])
def download_group_content(group_id, content_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para descargar el contenido', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Verificar que el usuario es miembro verificado del grupo
    headers = db._get_supabase_headers()
    member_check = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members",
        headers=headers,
        params={"group_id": f"eq.{group_id}", "user_id": f"eq.{user_id}", "status": "eq.verified"}
    )
    
    if member_check.status_code != 200 or not member_check.json():
        flash('Solo los miembros verificados pueden descargar el contenido', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Obtener información del contenido
    content_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_contents",
        headers=headers,
        params={"id": f"eq.{content_id}"}
    )
    
    if content_response.status_code != 200 or not content_response.json():
        flash('Contenido no encontrado', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    content = content_response.json()[0]
    
    # Verificar que el contenido pertenece al grupo
    if content['group_id'] != group_id:
        flash('El contenido no pertenece a este grupo', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Procesar content_data si es un string JSON
    import json
    if isinstance(content.get('content_data'), str):
        try:
            content['content_data'] = json.loads(content['content_data'])
        except json.JSONDecodeError:
            pass
    
    # Obtener la URL del archivo
    file_url = content.get('content_data', {}).get('file_url')
    filename = content.get('file', 'archivo')
    
    if not file_url:
        flash('No se encontró la URL del archivo', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Redirigir al usuario a la URL del archivo en Supabase Storage
    return redirect(file_url)  
@app.route('/proxy/pdf/<path:file_path>', methods=['GET'])
def proxy_pdf(file_path):
    """Proxy para PDFs de Supabase Storage para evitar problemas de CORS"""
    import requests
    from flask import Response
    
    # Construir la URL completa
    url = f"{SUPABASE_URL}/storage/v1/object/public/telegrambucket/{file_path}"
    
    # Obtener el archivo
    response = requests.get(url, stream=True)
    
    # Devolver el contenido
    return Response(
        response.iter_content(chunk_size=1024),
        content_type=response.headers.get('content-type', 'application/pdf'),
        headers={
            'Content-Disposition': f'inline; filename="{file_path.split("/")[-1]}"'
        }
    )
@app.route('/group/<group_id>/upload', methods=['GET', 'POST'])
def upload_group_content(group_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para subir contenido', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Verificar que el usuario es administrador del grupo - Enfoque modificado
    headers = db._get_supabase_headers()
    
    # Usar eq.true en lugar de is.true para consultar campos booleanos
    url = f"{SUPABASE_URL}/rest/v1/group_members?group_id=eq.{group_id}&user_id=eq.{user_id}&is_admin=eq.true"
    admin_check = requests.get(url, headers=headers)
    
    # Imprimir información de depuración
    print(f"URL: {url}")
    print(f"Status code: {admin_check.status_code}")
    print(f"Response: {admin_check.json()}")
    
    if admin_check.status_code != 200 or not admin_check.json():
        flash('Solo los administradores pueden subir contenido', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    # Obtener información del grupo
    group_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/groups",
        headers=headers,
        params={"id": f"eq.{group_id}"}
    )
    
    if group_response.status_code != 200 or not group_response.json():
        flash('Grupo no encontrado', 'danger')
        return redirect(url_for('groups'))
    
    group = group_response.json()[0]
    
    # Obtener información de almacenamiento del usuario
    user_data = db.get_user(user_id)
    used_storage = user_data.get('used_storage_bytes', 0) if user_data else 0
    plan_data = user_data.get('current_plan', {}) if user_data else {}
    max_storage = plan_data.get('storage_limit', 10 * 1024 * 1024)  # 10MB por defecto
    available_storage = max(0, max_storage - used_storage)
        
    if request.method == 'POST':
        # Verificar si hay archivo
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        # Verificar tamaño del archivo
        file_size = len(file.read())
        file.seek(0)  # Reiniciar puntero del archivo
        
        if file_size > available_storage:
            flash('El archivo excede el almacenamiento disponible', 'danger')
            return redirect(request.url)
        
        # Determinar tipo de contenido
        filename = file.filename
        content_type = 'other'
        
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            content_type = 'image'
        elif filename.lower().endswith('.pdf'):
            content_type = 'pdf'
        elif filename.lower().endswith(('.doc', '.docx', '.txt', '.rtf')):
            content_type = 'text'
        
        # Procesar y vectorizar el archivo
        success, message = db.upload_and_vectorize_file(group_id, user_id, file, content_type)
        
        if success:
            flash('Contenido subido y procesado con éxito', 'success')
            return redirect(url_for('group_detail', group_id=group_id))
        else:
            flash(f'Error al subir contenido: {message}', 'danger')
    
    return render_template('upload_group_content.html', 
                           group=group, 
                           used_storage=used_storage,
                           available_storage=available_storage)

@app.route('/groups/<group_id>/add_member', methods=['GET', 'POST'])
def add_group_member(group_id):
    # Verificar si el usuario está logueado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para añadir miembros', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Verificar que el usuario es administrador del grupo
    headers = db._get_supabase_headers()
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members?group_id=eq.{group_id}&user_id=eq.{user_id}&is_admin=eq.true",
        headers=headers
    )
    
    if response.status_code != 200 or not response.json():
        flash('No tienes permisos para añadir miembros a este grupo', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Buscar usuario por email o teléfono
        user_to_add = None
        if email:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?email=eq.{email.lower()}",
                headers=headers
            )
            if response.status_code == 200 and response.json():
                user_to_add = response.json()[0]
        
        if not user_to_add and phone:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?phone=eq.{phone}",
                headers=headers
            )
            if response.status_code == 200 and response.json():
                user_to_add = response.json()[0]
        
        if user_to_add:
            # Añadir al grupo
            success, verification_code = db.add_group_member(group_id, user_to_add['id'])
            
            if success:
                flash(f'Usuario añadido al grupo. Código de verificación: {verification_code}', 'success')
            else:
                flash(f'Error al añadir usuario: {verification_code}', 'danger')
        else:
            # Crear invitación pendiente
            verification_code = secrets.token_hex(3)
            invitation = {
                "group_id": group_id,
                "invited_by": user_id,
                "email": email,
                "phone": phone,
                "verification_code": verification_code,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "pending"
            }
            
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/group_invitations",
                headers=headers,
                json=invitation
            )
            
            if response.status_code == 201:
                flash(f'Invitación enviada. Código de verificación: {verification_code}', 'success')
            else:
                flash('Error al crear invitación', 'danger')
    
    return render_template('add_group_member.html', group_id=group_id)

@app.route('/verify_group/<verification_code>', methods=['GET', 'POST'])
def verify_group(verification_code):
    if request.method == 'POST':
        # Si el usuario está logueado, verificar directamente
        if 'user_id' in session:
            user_id = session['user_id']
            success, group_id = db.verify_group_member(verification_code)
            
            if success:
                flash('Has sido verificado como miembro del grupo', 'success')
                return redirect(url_for('group_detail', group_id=group_id))
            else:
                flash('Código de verificación no válido', 'danger')
        else:
            # Si no está logueado, redirigir al registro/login
            session['verification_code'] = verification_code
            return redirect(url_for('register'))
    
    return render_template('verify_group.html', verification_code=verification_code)

@app.route('/groups/<group_id>/add_content', methods=['GET', 'POST'])
def add_group_content(group_id):
    # ... código existente ...
    
    # Verificar que el usuario es administrador del grupo
    headers = db._get_supabase_headers()
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/group_members?group_id=eq.{group_id}&user_id=eq.{user_id}&is_admin=eq.true",
        headers=headers
    )
    
    if response.status_code != 200 or not response.json():
        flash('No tienes permisos para añadir contenido a este grupo', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    if request.method == 'POST':
        content_type = request.form.get('content_type')
        
        if content_type == 'text':
            content_data = request.form.get('content_text')
            file_size = len(content_data.encode('utf-8'))
            success, content_id = db.add_group_content(group_id, user_id, 'text', content_data, file_size=file_size)
        else:
            # Manejar archivos (PDF, imágenes)
            if 'content_file' not in request.files:
                flash('No se ha seleccionado ningún archivo', 'danger')
                return redirect(request.url)
            
            file = request.files['content_file']
            if file.filename == '':
                flash('No se ha seleccionado ningún archivo', 'danger')
                return redirect(request.url)
            
            # Guardar archivo en Supabase Storage
            # (Aquí se implementaría la lógica para subir a Supabase Storage)
            # Por ahora, simulamos una URL
            file_url = f"https://storage.example.com/{file.filename}"
            file_size = len(file.read())
            file.seek(0)  # Resetear el puntero del archivo
            
            success, content_id = db.add_group_content(
                group_id, user_id, content_type, file_url, 
                file_name=file.filename, file_size=file_size
            )
        
        if success:
            flash('Contenido añadido con éxito', 'success')
        else:
            flash(f'Error al añadir contenido: {content_id}', 'danger')
        
        return redirect(url_for('group_detail', group_id=group_id))
    
    return render_template('add_group_content.html', group_id=group_id)

@app.template_filter('format_price')
def format_price(value):
    """Formatear precios"""
    return f"{value:,.2f}".replace(',', '.').replace('.00', '')

if __name__ == '__main__':
    # Crear directorios necesarios
    for dir_path in ['templates', 'templates/admin', 'static', 'static/css', 'static/js']:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    # Configuración para entornos de producción como Heroku
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)