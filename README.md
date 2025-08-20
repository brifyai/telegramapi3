# Telegram API con Integración de Google Drive

## 🚀 Descripción

Aplicación web para gestionar planes de entrenadores y abogados, con integración automática de Google Drive para crear carpetas personalizadas cuando los usuarios compran planes.

## ✨ Características

- **Sistema de Planes**: Diferentes planes para entrenadores y abogados
- **Integración Google Drive**: Creación automática de carpetas al comprar planes
- **Base de Datos Supabase**: Almacenamiento seguro de datos
- **Interfaz Web**: Dashboard completo para gestión de usuarios y planes
- **Autenticación**: Sistema de login y registro de usuarios

## 🏗️ Arquitectura

- **Backend**: Python Flask
- **Base de Datos**: Supabase (PostgreSQL)
- **Almacenamiento**: Google Drive API
- **Frontend**: HTML/CSS/JavaScript con Bootstrap
- **Despliegue**: Vercel (configurado)

## 📁 Estructura del Proyecto

```
telegram-api/
├── web_interface.py      # Aplicación principal Flask
├── database.py           # Conexión y operaciones de base de datos
├── google_drive_service.py # Servicio de Google Drive
├── templates/            # Plantillas HTML
├── static/              # Archivos estáticos (CSS, JS)
├── api/                 # Entry point para Vercel
├── vercel.json          # Configuración de Vercel
└── requirements.txt     # Dependencias de Python
```

## 🚀 Despliegue en Vercel

### 1. Conectar con GitHub
- Ve a [Vercel](https://vercel.com)
- Conecta tu cuenta de GitHub
- Importa el repositorio `telegramapi3`

### 2. Configurar Variables de Entorno
En Vercel, agrega estas variables:
```
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
FLASK_SECRET_KEY=tu_secret_key
```

### 3. Desplegar
- Vercel detectará automáticamente la configuración
- La aplicación se desplegará en una URL como: `https://telegramapi3.vercel.app`

## 🔧 Configuración Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/brifyai/telegramapi3.git
cd telegramapi3
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea un archivo `.env` basado en `env_example.txt`:
```bash
cp env_example.txt .env
# Edita .env con tus credenciales reales
```

### 4. Ejecutar la aplicación
```bash
python web_interface.py
```

## 🔐 Configuración de Google Drive

### 1. Habilitar Google Drive API
- Ve a [Google Cloud Console](https://console.cloud.google.com)
- Habilita Google Drive API
- Crea credenciales OAuth 2.0

### 2. Configurar URLs de redirección
En Google Cloud Console, agrega:
- `https://tu-app.vercel.app/oauth2callback` (producción)
- `http://localhost:5000/oauth2callback` (desarrollo)

### 3. Descargar credenciales
- Descarga el archivo JSON de credenciales
- Renómbralo a `credentials.json`
- Colócalo en el directorio del proyecto

## 📊 Base de Datos

### Tablas principales:
- `users`: Usuarios del sistema
- `plans`: Planes disponibles
- `carpeta_administrador`: Carpetas de Google Drive creadas
- `user_credentials`: Credenciales de Google Drive

## 🌐 Endpoints principales

- `/`: Página principal
- `/login`: Autenticación de usuarios
- `/register`: Registro de usuarios
- `/plans`: Visualización de planes
- `/buy_plan/<plan_id>`: Compra de planes
- `/dashboard`: Panel de control

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:
- Email: brifyaimaster@gmail.com
- GitHub Issues: [Crear un issue](https://github.com/brifyai/telegramapi3/issues)

## 🔄 Estado del Proyecto

- ✅ Integración con Supabase
- ✅ Sistema de planes
- ✅ Integración con Google Drive
- ✅ Interfaz web
- ✅ Configuración para Vercel
- 🚧 Pruebas de integración
- 🚧 Documentación completa
