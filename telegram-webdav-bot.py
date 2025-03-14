# bot.py
import os
import logging
import webdav3.client as wc
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, ConversationHandler, filters

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obtener token del bot desde variables de entorno
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Configuración de WebDAV
WEBDAV_HOSTNAME = os.environ.get('WEBDAV_HOSTNAME')
WEBDAV_USERNAME = os.environ.get('WEBDAV_USERNAME')
WEBDAV_PASSWORD = os.environ.get('WEBDAV_PASSWORD')

# Mapeo de canales a directorios (formato CHANNEL_ID:DIRECTORY)
CHANNEL_MAPPING = {}
for mapping in os.environ.get('CHANNEL_MAPPINGS', '').split(','):
    if ':' in mapping:
        channel_id, directory = mapping.split(':', 1)
        CHANNEL_MAPPING[int(channel_id.strip())] = directory.strip()

# Lista de usuarios autorizados
AUTHORIZED_USERS = []
for user_id in os.environ.get('AUTHORIZED_USERS', '').split(','):
    if user_id.strip():
        AUTHORIZED_USERS.append(int(user_id.strip()))

# Estados para el conversation handler
SELECTING_DIRECTORY = 1

# Almacenamiento temporal de archivos enviados por usuarios
user_files = {}

# Cliente WebDAV
webdav_options = {
    'webdav_hostname': WEBDAV_HOSTNAME,
    'webdav_login': WEBDAV_USERNAME,
    'webdav_password': WEBDAV_PASSWORD,
    'disable_check': True
}
webdav_client = wc.Client(webdav_options)

# Verificar que los directorios existan, crearlos si no existen
def ensure_directories():
    for directory in CHANNEL_MAPPING.values():
        if not webdav_client.check(directory):
            logger.info(f"Creando directorio: {directory}")
            webdav_client.mkdir(directory)
            
# Obtener lista de directorios disponibles
def get_available_directories():
    directories = set(CHANNEL_MAPPING.values())
    # Listar directorios en la raíz del WebDAV
    try:
        root_dirs = webdav_client.list()
        for dir_path in root_dirs:
            # Eliminar la barra final si existe
            dir_path = dir_path.rstrip('/')
            if dir_path and webdav_client.is_dir(dir_path):
                directories.add(f"/{dir_path}")
    except Exception as e:
        logger.error(f"Error al listar directorios: {str(e)}")
    
    return sorted(list(directories))

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los documentos recibidos de diferentes canales"""
    
    # Obtener el ID del chat (canal) y usuario
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Si es un chat privado y el usuario está autorizado, iniciar el flujo de selección de directorio
    if update.effective_chat.type == 'private' and user_id in AUTHORIZED_USERS:
        return await handle_direct_file(update, context)
    
    # Verificar si el canal está en nuestro mapeo
    if chat_id not in CHANNEL_MAPPING:
        logger.warning(f"Canal no configurado: {chat_id}")
        return
    
    directory = CHANNEL_MAPPING[chat_id]
    document = update.message.document
    file_name = document.file_name
    
    # Descargar el archivo
    file = await context.bot.get_file(document.file_id)
    local_path = f"/tmp/{file_name}"
    await file.download_to_drive(local_path)
    
    # Subir a WebDAV
    remote_path = f"{directory}/{file_name}"
    logger.info(f"Subiendo archivo {file_name} al directorio {directory}")
    
    try:
        webdav_client.upload_sync(local_path, remote_path)
        logger.info(f"Archivo {file_name} subido correctamente a {remote_path}")
    except Exception as e:
        logger.error(f"Error al subir archivo {file_name}: {str(e)}")
    finally:
        # Eliminar archivo temporal
        os.remove(local_path)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los videos recibidos de diferentes canales"""
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Si es un chat privado y el usuario está autorizado, iniciar el flujo de selección de directorio
    if update.effective_chat.type == 'private' and user_id in AUTHORIZED_USERS:
        return await handle_direct_file(update, context)
    
    if chat_id not in CHANNEL_MAPPING:
        logger.warning(f"Canal no configurado: {chat_id}")
        return
    
    directory = CHANNEL_MAPPING[chat_id]
    video = update.message.video
    
    # Generar nombre de archivo si no está disponible
    if hasattr(video, 'file_name') and video.file_name:
        file_name = video.file_name
    else:
        file_name = f"video_{video.file_id}.mp4"
    
    # Descargar el archivo
    file = await context.bot.get_file(video.file_id)
    local_path = f"/tmp/{file_name}"
    await file.download_to_drive(local_path)
    
    # Subir a WebDAV
    remote_path = f"{directory}/{file_name}"
    logger.info(f"Subiendo video {file_name} al directorio {directory}")
    
    try:
        webdav_client.upload_sync(local_path, remote_path)
        logger.info(f"Video {file_name} subido correctamente a {remote_path}")
    except Exception as e:
        logger.error(f"Error al subir video {file_name}: {str(e)}")
    finally:
        # Eliminar archivo temporal
        os.remove(local_path)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las fotos recibidas de diferentes canales"""
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Si es un chat privado y el usuario está autorizado, iniciar el flujo de selección de directorio
    if update.effective_chat.type == 'private' and user_id in AUTHORIZED_USERS:
        return await handle_direct_file(update, context)
    
    if chat_id not in CHANNEL_MAPPING:
        logger.warning(f"Canal no configurado: {chat_id}")
        return
    
    directory = CHANNEL_MAPPING[chat_id]
    
    # Obtener la foto de mayor resolución
    photo = update.message.photo[-1]
    
    # Generar nombre de archivo
    file_name = f"photo_{photo.file_id}.jpg"
    
    # Descargar el archivo
    file = await context.bot.get_file(photo.file_id)
    local_path = f"/tmp/{file_name}"
    await file.download_to_drive(local_path)
    
    # Subir a WebDAV
    remote_path = f"{directory}/{file_name}"
    logger.info(f"Subiendo foto {file_name} al directorio {directory}")
    
    try:
        webdav_client.upload_sync(local_path, remote_path)
        logger.info(f"Foto {file_name} subida correctamente a {remote_path}")
    except Exception as e:
        logger.error(f"Error al subir foto {file_name}: {str(e)}")
    finally:
        # Eliminar archivo temporal
        os.remove(local_path)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los archivos de audio recibidos de diferentes canales"""
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Si es un chat privado y el usuario está autorizado, iniciar el flujo de selección de directorio
    if update.effective_chat.type == 'private' and user_id in AUTHORIZED_USERS:
        return await handle_direct_file(update, context)
    
    if chat_id not in CHANNEL_MAPPING:
        logger.warning(f"Canal no configurado: {chat_id}")
        return
    
    directory = CHANNEL_MAPPING[chat_id]
    audio = update.message.audio
    
    # Generar nombre de archivo
    if hasattr(audio, 'file_name') and audio.file_name:
        file_name = audio.file_name
    else:
        file_name = f"audio_{audio.file_id}.mp3"
    
    # Descargar el archivo
    file = await context.bot.get_file(audio.file_id)
    local_path = f"/tmp/{file_name}"
    await file.download_to_drive(local_path)
    
    # Subir a WebDAV
    remote_path = f"{directory}/{file_name}"
    logger.info(f"Subiendo audio {file_name} al directorio {directory}")
    
    try:
        webdav_client.upload_sync(local_path, remote_path)
        logger.info(f"Audio {file_name} subido correctamente a {remote_path}")
    except Exception as e:
        logger.error(f"Error al subir audio {file_name}: {str(e)}")
    finally:
        # Eliminar archivo temporal
        os.remove(local_path)

async def handle_direct_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja archivos enviados directamente al bot por usuarios autorizados"""
    user_id = update.effective_user.id
    
    # Verificar autorización
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return ConversationHandler.END
    
    # Determinar el tipo de archivo y obtener información
    message = update.message
    file_info = None
    
    if message.document:
        file_info = {
            'file_id': message.document.file_id,
            'file_name': message.document.file_name,
            'file_type': 'document'
        }
    elif message.photo:
        photo = message.photo[-1]  # Obtener la foto de mayor resolución
        file_info = {
            'file_id': photo.file_id,
            'file_name': f"photo_{photo.file_id}.jpg",
            'file_type': 'photo'
        }
    elif message.video:
        video = message.video
        file_name = video.file_name if hasattr(video, 'file_name') and video.file_name else f"video_{video.file_id}.mp4"
        file_info = {
            'file_id': video.file_id,
            'file_name': file_name,
            'file_type': 'video'
        }
    elif message.audio:
        audio = message.audio
        file_name = audio.file_name if hasattr(audio, 'file_name') and audio.file_name else f"audio_{audio.file_id}.mp3"
        file_info = {
            'file_id': audio.file_id,
            'file_name': file_name,
            'file_type': 'audio'
        }
    
    if not file_info:
        await update.message.reply_text("Tipo de archivo no soportado.")
        return ConversationHandler.END
    
    # Guardar información del archivo para su procesamiento posterior
    context.user_data['file_info'] = file_info
    
    # Descargar el archivo
    file = await context.bot.get_file(file_info['file_id'])
    local_path = f"/tmp/{file_info['file_name']}"
    await file.download_to_drive(local_path)
    
    # Guardar la ruta temporal
    context.user_data['local_path'] = local_path
    
    # Obtener directorios disponibles
    directories = get_available_directories()
    
    # Crear botones para cada directorio
    keyboard = []
    for i in range(0, len(directories), 2):
        row = []
        row.append(InlineKeyboardButton(directories[i], callback_data=f"dir:{directories[i]}"))
        if i + 1 < len(directories):
            row.append(InlineKeyboardButton(directories[i+1], callback_data=f"dir:{directories[i+1]}"))
        keyboard.append(row)
    
    # Añadir opción para crear un nuevo directorio
    keyboard.append([InlineKeyboardButton("📁 Crear nuevo directorio", callback_data="new_dir")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"He recibido tu archivo: {file_info['file_name']}.\n"
        f"Por favor, selecciona el directorio donde quieres guardarlo:",
        reply_markup=reply_markup
    )
    
    return SELECTING_DIRECTORY

async def handle_directory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de directorio para guardar el archivo"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "new_dir":
        await query.message.edit_text(
            "Por favor, envía el nombre del nuevo directorio que quieres crear (sin barras):"
        )
        context.user_data['awaiting_new_dir'] = True
        return SELECTING_DIRECTORY
    
    if callback_data.startswith("dir:"):
        directory = callback_data[4:]  # Extraer el directorio de "dir:/directorio"
        
        # Obtener información del archivo y ruta local
        file_info = context.user_data.get('file_info')
        local_path = context.user_data.get('local_path')
        
        if not file_info or not local_path:
            await query.message.edit_text("Hubo un error al procesar tu archivo. Por favor, inténtalo de nuevo.")
            return ConversationHandler.END
        
        # Subir a WebDAV
        remote_path = f"{directory}/{file_info['file_name']}"
        
        try:
            webdav_client.upload_sync(local_path, remote_path)
            await query.message.edit_text(f"✅ Archivo {file_info['file_name']} subido correctamente a {directory}")
            logger.info(f"Archivo {file_info['file_name']} subido por usuario {update.effective_user.id} a {directory}")
        except Exception as e:
            await query.message.edit_text(f"❌ Error al subir el archivo: {str(e)}")
            logger.error(f"Error al subir archivo {file_info['file_name']}: {str(e)}")
        finally:
            # Limpiar datos temporales
            if os.path.exists(local_path):
                os.remove(local_path)
            context.user_data.clear()
        
        return ConversationHandler.END
    
    await query.message.edit_text("Opción no válida. Por favor, inténtalo de nuevo.")
    return ConversationHandler.END

async def handle_new_directory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la creación de un nuevo directorio"""
    if not context.user_data.get('awaiting_new_dir'):
        return SELECTING_DIRECTORY
    
    # Obtener el nombre del directorio
    dir_name = update.message.text.strip()
    
    # Validar el nombre del directorio (no debería contener barras, etc.)
    if '/' in dir_name or '\\' in dir_name or not dir_name:
        await update.message.reply_text(
            "Nombre de directorio no válido. No debe contener barras (/ o \\).\n"
            "Por favor, intenta de nuevo."
        )
        return SELECTING_DIRECTORY
    
    directory = f"/{dir_name}"
    
    # Crear el directorio
    try:
        webdav_client.mkdir(directory)
        logger.info(f"Directorio {directory} creado por usuario {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"Error al crear el directorio: {str(e)}")
        logger.error(f"Error al crear directorio {directory}: {str(e)}")
        return ConversationHandler.END
    
    # Obtener información del archivo y ruta local
    file_info = context.user_data.get('file_info')
    local_path = context.user_data.get('local_path')
    
    if not file_info or not local_path:
        await update.message.reply_text("Hubo un error al procesar tu archivo. Por favor, inténtalo de nuevo.")
        return ConversationHandler.END
    
    # Subir a WebDAV
    remote_path = f"{directory}/{file_info['file_name']}"
    
    try:
        webdav_client.upload_sync(local_path, remote_path)
        await update.message.reply_text(f"✅ Archivo {file_info['file_name']} subido correctamente a {directory}")
        logger.info(f"Archivo {file_info['file_name']} subido por usuario {update.effective_user.id} a {directory}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al subir el archivo: {str(e)}")
        logger.error(f"Error al subir archivo {file_info['file_name']}: {str(e)}")
    finally:
        # Limpiar datos temporales
        if os.path.exists(local_path):
            os.remove(local_path)
        context.user_data.clear()
    
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start"""
    user_id = update.effective_user.id
    
    if user_id in AUTHORIZED_USERS:
        await update.message.reply_text(
            f"¡Hola {update.effective_user.first_name}! Soy un bot para guardar archivos en WebDAV.\n\n"
            "Puedes enviarme documentos, fotos, videos o audios, y te preguntaré dónde quieres guardarlos.\n\n"
            "También recibo archivos de canales configurados y los guardo automáticamente."
        )
    else:
        await update.message.reply_text(
            f"¡Hola {update.effective_user.first_name}! Soy un bot para guardar archivos en WebDAV.\n\n"
            "Lo siento, pero no estás autorizado para usar este bot directamente."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /help"""
    user_id = update.effective_user.id
    
    if user_id in AUTHORIZED_USERS:
        await update.message.reply_text(
            "📋 *Instrucciones de uso:*\n\n"
            "• Envíame cualquier documento, foto, video o audio.\n"
            "• Te preguntaré dónde quieres guardarlo.\n"
            "• Selecciona un directorio existente o crea uno nuevo.\n\n"
            "🔸 *Canales configurados:*\n" + 
            "\n".join([f"• Canal {chat_id} → {directory}" for chat_id, directory in CHANNEL_MAPPING.items()]) +
            "\n\n📝 *Comandos disponibles:*\n"
            "• /start - Inicia el bot\n"
            "• /help - Muestra este mensaje de ayuda\n"
            "• /list - Listar directorios disponibles",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Lo siento, no estás autorizado para usar este bot.")

async def list_directories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los directorios disponibles"""
    user_id = update.effective_user.id
    
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("Lo siento, no estás autorizado para usar este bot.")
        return
    
    directories = get_available_directories()
    
    if not directories:
        await update.message.reply_text("No hay directorios disponibles.")
        return
    
    message = "📁 *Directorios disponibles:*\n\n"
    for directory in directories:
        message += f"• {directory}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación actual"""
    # Limpiar datos temporales
    if 'local_path' in context.user_data and os.path.exists(context.user_data['local_path']):
        os.remove(context.user_data['local_path'])
    context.user_data.clear()
    
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

def main() -> None:
    """Inicia el bot"""
    
    # Verificar configuración
    if not TELEGRAM_BOT_TOKEN:
        logger.error("ERROR: Token de Telegram no configurado")
        return
    
    if not WEBDAV_HOSTNAME or not WEBDAV_USERNAME or not WEBDAV_PASSWORD:
        logger.error("ERROR: Configuración de WebDAV incompleta")
        return
    
    # Verificar/crear directorios en WebDAV
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Error al verificar directorios: {str(e)}")
        return
    
    # Iniciar bot
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Crear manejador de conversación para la selección de directorio
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_direct_file),
            MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_direct_file),
            MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_direct_file),
            MessageHandler(filters.AUDIO & filters.ChatType.PRIVATE, handle_direct_file),
        ],
        states={
            SELECTING_DIRECTORY: [
                CallbackQueryHandler(handle_directory_selection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_directory),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Añadir manejadores
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_directories))
    
    # Añadir manejadores para archivos de canales
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.ChatType.PRIVATE, handle_document))
    application.add_handler(MessageHandler(filters.VIDEO & ~filters.ChatType.PRIVATE, handle_video))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.ChatType.PRIVATE, handle_photo))
    application.add_handler(MessageHandler(filters.AUDIO & ~filters.ChatType.PRIVATE, handle_audio))
    
    # Iniciar bot
    logger.info("Bot iniciado...")
    application.run_polling()

if __name__ == "__main__":
    main()
