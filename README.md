# Telegram API - BrifyAI

Esta aplicación consiste en un bot de Telegram y una interfaz web desarrollada con Flask.

## Estructura del Proyecto

- `bot.py`: Implementación del bot de Telegram
- `database.py`: Gestión de la base de datos (Supabase)
- `run.py`: Punto de entrada para ejecutar solo el bot
- `run_all.py`: Punto de entrada para ejecutar tanto el bot como la interfaz web
- `web_interface.py`: Interfaz web desarrollada con Flask

## Requisitos

Ver `requirements.txt` para las dependencias.

## Configuración

1. Copia `.env.example` a `.env`
2. Completa las variables de entorno en el archivo `.env`

## Ejecución Local

```bash
# Para ejecutar solo el bot
python run.py

# Para ejecutar tanto el bot como la interfaz web
python run_all.py
```

## Despliegue

Esta aplicación está configurada para ser desplegada en plataformas como Heroku:

1. Crea una nueva aplicación en Heroku
2. Conecta tu repositorio Git
3. Configura las variables de entorno en la sección de configuración de Heroku
4. Despliega la aplicación

El `Procfile` ya está configurado para iniciar tanto el servidor web como el worker del bot.

## Variables de Entorno Necesarias

- `SUPABASE_URL`: URL de tu proyecto Supabase
- `SUPABASE_KEY`: Clave API de Supabase
- `TELEGRAM_BOT_TOKEN`: Token del bot de Telegram
- `SECRET_KEY`: Clave secreta para Flask
