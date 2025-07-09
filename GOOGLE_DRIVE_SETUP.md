# 🔧 Configuración de Google Drive API

Esta guía detalla cómo configurar Google Drive API y OAuth2 para la integración con el bot de Telegram.

## 📋 Requisitos previos

- Cuenta de Google Cloud Platform
- Proyecto con facturación habilitada (para uso en producción)
- Acceso al Google Cloud Console

## 🚀 Paso 1: Configurar Google Cloud Console

### 1.1 Crear/Seleccionar proyecto

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un nuevo proyecto o seleccionar uno existente
3. Anotar el **Project ID** para referencia

### 1.2 Habilitar Google Drive API

1. En el menú lateral, ir a **APIs & Services** → **Library**
2. Buscar "Google Drive API"
3. Hacer clic en "Google Drive API"
4. Hacer clic en **"Enable"**

### 1.3 Configurar OAuth2 Consent Screen

1. Ir a **APIs & Services** → **OAuth consent screen**
2. Seleccionar **"External"** (para usuarios externos)
3. Completar la información requerida:
   - **App name**: Nombre de tu aplicación (ej: "Telegram Bot AI")
   - **User support email**: Tu email
   - **Developer contact information**: Tu email
4. Hacer clic en **"Save and Continue"**

### 1.4 Configurar Scopes

1. En la sección **"Scopes"**, hacer clic en **"Add or Remove Scopes"**
2. Agregar los siguientes scopes:
   - `https://www.googleapis.com/auth/drive.file`
3. Hacer clic en **"Save and Continue"**

### 1.5 Usuarios de prueba (opcional)

Si tu app está en modo de prueba, agregar usuarios de prueba:
1. Hacer clic en **"Add Users"**
2. Agregar las direcciones de email que podrán usar la app
3. Hacer clic en **"Save and Continue"**

## 🔐 Paso 2: Crear credenciales OAuth2

### 2.1 Crear credenciales

1. Ir a **APIs & Services** → **Credentials**
2. Hacer clic en **"Create Credentials"** → **"OAuth 2.0 Client IDs"**
3. Seleccionar **"Web application"** como tipo

### 2.2 Configurar URLs de redireccionamiento

1. En **"Authorized redirect URIs"**, agregar:
   - `http://localhost:5000/auth/google/callback` (para desarrollo)
   - `https://tu-dominio.com/auth/google/callback` (para producción)

### 2.3 Descargar credenciales

1. Hacer clic en **"Create"**
2. Aparecerá un modal con las credenciales
3. Anotar el **Client ID** y **Client Secret**
4. Opcionalmente, descargar el archivo JSON para respaldo

## 🛠️ Paso 3: Configurar variables de entorno

Agregar las siguientes variables al archivo `.env`:

```bash
# Google Drive API
GOOGLE_CLIENT_ID=tu_client_id_aqui
GOOGLE_CLIENT_SECRET=tu_client_secret_aqui
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Clave de cifrado para tokens (generar una segura)
ENCRYPTION_KEY=tu_clave_de_cifrado_de_32_caracteres

# OpenAI (opcional, para embeddings mejorados)
OPENAI_API_KEY=tu_openai_api_key
USE_OPENAI_EMBEDDINGS=false
```

## 🔒 Paso 4: Generar clave de cifrado

Para generar una clave de cifrado segura:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

O usar este comando:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 🧪 Paso 5: Probar la configuración

### 5.1 Ejecutar migración de base de datos

```bash
python migrate_database.py
```

### 5.2 Probar conexión con Google Drive

```python
from google_drive_service import GoogleDriveService
import os

# Inicializar servicio
drive_service = GoogleDriveService(
    supabase_url=os.getenv('SUPABASE_URL'),
    supabase_key=os.getenv('SUPABASE_KEY'),
    encryption_key=os.getenv('ENCRYPTION_KEY')
)

# Generar URL de autorización
auth_url = drive_service.get_authorization_url(
    user_id="test_user",
    redirect_uri=os.getenv('GOOGLE_REDIRECT_URI')
)

print(f"URL de autorización: {auth_url}")
```

## 🔄 Paso 6: Actualizar la aplicación web

Agregar las siguientes rutas al archivo `web_interface.py`:

```python
# Ruta para iniciar autorización Google Drive
@app.route('/auth/google')
def google_auth():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    auth_url = drive_service.get_authorization_url(
        user_id=user_id,
        redirect_uri=url_for('google_callback', _external=True)
    )
    
    return redirect(auth_url)

# Ruta para callback OAuth2
@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        flash('Error en autorización con Google Drive', 'error')
        return redirect(url_for('dashboard'))
    
    success, message = drive_service.handle_oauth_callback(
        code=code,
        state=state,
        redirect_uri=url_for('google_callback', _external=True)
    )
    
    if success:
        flash('Google Drive conectado exitosamente!', 'success')
    else:
        flash(f'Error conectando Google Drive: {message}', 'error')
    
    return redirect(url_for('dashboard'))
```

## 📊 Paso 7: Actualizar dashboard

Agregar sección para Google Drive en el dashboard:

```html
<!-- En el template del dashboard -->
<div class="card">
    <div class="card-header">
        <h3>Google Drive</h3>
    </div>
    <div class="card-body">
        {% if user.google_drive_connected %}
            <p class="text-success">✅ Google Drive conectado</p>
            <p>Conectado el: {{ user.google_drive_connected_at }}</p>
            <a href="{{ url_for('manage_google_drive') }}" class="btn btn-primary">Gestionar Drive</a>
        {% else %}
            <p class="text-warning">⚠️ Google Drive no conectado</p>
            <a href="{{ url_for('google_auth') }}" class="btn btn-success">Conectar Google Drive</a>
        {% endif %}
    </div>
</div>
```

## 🛡️ Consideraciones de seguridad

### Para desarrollo:
- Usar `http://localhost:5000` está bien
- Mantener la app en modo "Testing"

### Para producción:
- Usar HTTPS obligatoriamente
- Verificar el dominio en Google Cloud Console
- Publicar la app (sacarla del modo "Testing")
- Implementar rate limiting
- Usar claves de cifrado seguras
- Monitorear logs de acceso

## 🔍 Troubleshooting

### Error: "redirect_uri_mismatch"
- Verificar que la URL de callback coincida exactamente con la configurada en Google Cloud Console
- Asegurarse de incluir `http://` o `https://`

### Error: "access_denied"
- El usuario canceló la autorización
- Verificar que el scope sea correcto

### Error: "invalid_client"
- Verificar Client ID y Client Secret
- Asegurarse de que estén en las variables de entorno

### Error: "insufficient_scope"
- Verificar que el scope `drive.file` esté configurado
- Re-autorizar la aplicación

## 📚 Recursos adicionales

- [Google Drive API Documentation](https://developers.google.com/drive/api/v3/about-sdk)
- [OAuth2 for Web Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Cloud Console](https://console.cloud.google.com/)

## 🎯 Próximos pasos

Una vez completada la configuración:

1. Ejecutar la migración de base de datos
2. Probar la conexión con Google Drive
3. Actualizar el bot de Telegram para usar Google Drive
4. Implementar búsqueda semántica con embeddings
5. Migrar datos existentes de Supabase Storage a Google Drive

¡La configuración está completa! 🎉