# Despliegue en Heroku

Este documento contiene las instrucciones para desplegar la aplicación en Heroku.

## Archivos de Configuración

Los siguientes archivos han sido configurados para Heroku:

- **Procfile**: Define los procesos web y worker
- **runtime.txt**: Especifica la versión de Python (3.9.18)
- **requirements.txt**: Lista todas las dependencias necesarias
- **app.json**: Configuración de la aplicación para Heroku
- **.gitignore**: Actualizado con archivos específicos de Heroku

## Variables de Entorno Requeridas

Configura las siguientes variables de entorno en Heroku:

```
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_clave_de_supabase
TELEGRAM_BOT_TOKEN=tu_token_del_bot
SECRET_KEY=clave_secreta_generada_automaticamente
```

## Pasos para el Despliegue

### 1. Preparar el repositorio
```bash
git add .
git commit -m "Configuración para Heroku"
git push origin main
```

### 2. Crear aplicación en Heroku
```bash
heroku create nombre-de-tu-app
```

### 3. Configurar variables de entorno
```bash
heroku config:set SUPABASE_URL=tu_url_aqui
heroku config:set SUPABASE_KEY=tu_clave_aqui
heroku config:set TELEGRAM_BOT_TOKEN=tu_token_aqui
```

### 4. Desplegar la aplicación
```bash
git push heroku main
```

### 5. Escalar los procesos
```bash
heroku ps:scale web=1 worker=1
```

### 6. Ver logs
```bash
heroku logs --tail
```

## Notas Importantes

- El proceso **web** ejecuta la interfaz Flask
- El proceso **worker** ejecuta el bot de Telegram
- Ambos procesos son necesarios para el funcionamiento completo
- La aplicación usa el plan gratuito de Heroku (eco dynos)
- Se incluye PostgreSQL como addon por defecto

## Comandos Útiles

```bash
# Ver estado de la aplicación
heroku ps

# Reiniciar la aplicación
heroku restart

# Abrir la aplicación en el navegador
heroku open

# Acceder a la consola de Heroku
heroku run python

# Ver configuración
heroku config
```

## Solución de Problemas

1. **Error de dependencias**: Verifica que todas las dependencias estén en requirements.txt
2. **Error de variables de entorno**: Asegúrate de que todas las variables estén configuradas
3. **Error de base de datos**: Verifica la conexión a Supabase
4. **Error del bot**: Verifica que el token de Telegram sea válido

Para más información, consulta la [documentación oficial de Heroku](https://devcenter.heroku.com/articles/getting-started-with-python).