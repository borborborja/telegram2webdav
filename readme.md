# Bot de Telegram para WebDAV

Este bot de Telegram recibe archivos de diferentes canales y los envía a directorios específicos en un servidor WebDAV según el canal de origen.

## Características

- Procesa documentos, videos, fotos y archivos de audio de canales de Telegram
- Envía los archivos a directorios específicos en un servidor WebDAV
- Mapeo configurable de canales a directorios
- Permite a usuarios autorizados enviar archivos directamente al bot
- Interfaz interactiva para seleccionar directorios de destino
- Opción para crear nuevos directorios sobre la marcha
- Fácil de implementar con Docker

## Requisitos previos

- Token de bot de Telegram (obtenido de [@BotFather](https://t.me/BotFather))
- Acceso a un servidor WebDAV (como Nextcloud, ownCloud, etc.)
- Docker y Docker Compose instalados en su servidor

## Configuración

### 1. Obtener los IDs de los canales y usuarios

Para obtener el ID de un canal o usuario, puedes:
- Reenviar un mensaje del canal/usuario a [@userinfobot](https://t.me/userinfobot)
- O usar un bot como [@username_to_id_bot](https://t.me/username_to_id_bot)

Los IDs de canales suelen ser números negativos (ej. `-1001234567890`).
Los IDs de usuarios son números positivos (ej. `123456789`).

### 2. Configurar variables de entorno

Edita el archivo `docker-compose.yml` y actualiza las siguientes variables:

- `TELEGRAM_BOT_TOKEN`: Tu token de bot de Telegram
- `WEBDAV_HOSTNAME`: URL de tu servidor WebDAV
- `WEBDAV_USERNAME`: Usuario de WebDAV
- `WEBDAV_PASSWORD`: Contraseña de WebDAV
- `CHANNEL_MAPPINGS`: Mapeo de canales a directorios en formato `CANAL_ID:/directorio, OTRO_CANAL_ID:/otro_directorio`
- `AUTHORIZED_USERS`: Lista de IDs de usuarios autorizados a enviar archivos directamente al bot, separados por comas

Ejemplo:
```yaml
environment:
  - TELEGRAM_BOT_TOKEN=5412345678:AAHxyz123abc456def789ghi0jklmnopqrs
  - WEBDAV_HOSTNAME=https://cloud.ejemplo.com/remote.php/dav/files/usuario/
  - WEBDAV_USERNAME=usuario
  - WEBDAV_PASSWORD=contraseña_segura
  - CHANNEL_MAPPINGS=-1001234567890:/documentos, -1009876543210:/videos
  - AUTHORIZED_USERS=123456789, 987654321
```

### 3. Configurar el bot en Telegram

1. Añade el bot a los canales de los que deseas recibir archivos
2. Asegúrate de darle permiso de administrador para acceder a los mensajes

## Instalación y ejecución

1. Clona este repositorio
2. Configura las variables de entorno como se explicó anteriormente
3. Ejecuta el bot con Docker Compose:

```bash
docker-compose up -d
```

Para ver los logs:
```bash
docker-compose logs -f
```

## Interacción directa con el bot

Los usuarios autorizados pueden enviar archivos directamente al bot y elegir dónde guardarlos:

1. Envía un archivo (documento, foto, video o audio) al bot
2. El bot te preguntará dónde quieres guardarlo
3. Selecciona un directorio existente o crea uno nuevo

### Comandos disponibles

- `/start` - Iniciar el bot con mensaje de bienvenida
- `/help` - Mostrar ayuda e información sobre canales configurados
- `/list` - Listar todos los directorios disponibles
- `/cancel` - Cancelar la operación actual durante la selección de directorio

## Tipos de archivos soportados

- Documentos (cualquier archivo compartido como documento)
- Videos
- Fotos
- Archivos de audio

## Solución de problemas

### Verificar los logs
```bash
docker-compose logs -f
```

### El bot no recibe archivos de los canales
- Asegúrate de que el bot sea administrador en los canales
- Verifica que los IDs de los canales estén correctamente configurados

### Errores de conexión WebDAV
- Verifica la URL, usuario y contraseña de WebDAV
- Asegúrate de que las carpetas destino existan o tengas permisos para crearlas
