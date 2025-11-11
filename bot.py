import logging
import os
import pytz
from datetime import time
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Importar el scraper
from scraper import obtener_noticias_uruguay

# Cargar variables de entorno (para desarrollo local)
load_dotenv()

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE TELEGRAM ---

# Obtener el token del archivo .env o del entorno (Render)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Usar el puerto y URL proporcionados por Render para Webhooks
PORT = int(os.environ.get('PORT', '8080')) # Puerto por defecto 8080
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start."""
    user = update.effective_user
    await update.message.reply_html(
        rf"¡Hola, {user.mention_html()}! Soy tu bot de noticias. Usa /noticias para ver el resumen de hoy."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /help."""
    help_text = (
        "Comandos disponibles:\n"
        "/start - Inicia el bot.\n"
        "/noticias - Obtiene el resumen de noticias de Uruguay ahora mismo.\n"
        "/help - Muestra este mensaje de ayuda."
    )
    await update.message.reply_text(help_text)

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obtiene y envía el resumen de noticias actual."""
    await update.message.reply_text("Buscando las noticias más importantes de Uruguay... 📰")
    
    try:
        noticias = await obtener_noticias_uruguay()
        
        if not noticias:
            mensaje = "Lo siento, no pude encontrar noticias de las fuentes de Uruguay. Intenta más tarde."
        else:
            # Construir el mensaje
            mensaje = "*Resumen de Noticias de Uruguay:*\n\n"
            for n in noticias:
                # Usar formato de enlace en Markdown: [Título](URL)
                # La sanitización se hace en scraper.py, pero por si acaso, usamos V2
                mensaje += f"*{n['fuente']}*: [{n['titulo']}]({n['url']})\n\n"
            
            mensaje += "—\n_Última actualización: _{}".format(
                datetime.now(pytz.timezone('America/Montevideo')).strftime('%H:%M hs, %d/%m/%Y')
            )
            
        # El parse_mode 'Markdown' es el que requiere el formato de enlace
        await update.message.reply_text(
            mensaje, 
            parse_mode='Markdown', 
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error CRÍTICO al ejecutar el comando /noticias: {e}", exc_info=True)
        # Mostrar un mensaje al usuario en caso de fallo
        await update.message.reply_text("Ocurrió un error al obtener o enviar las noticias. Por favor, revisa el log.")

# --- JOB QUEUE (Para la programación diaria) ---

async def enviar_noticias_programadas(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Función que se ejecuta diariamente para enviar noticias a todos los chats."""
    # Nota: Este bot está diseñado para enviar a chats que han interactuado.
    # En un entorno real con webhooks (Render), necesitaríamos una base de datos para almacenar los IDs de chat.
    # Por ahora, para demostrar que el JobQueue funciona, usaremos un chat_id de prueba.
    
    # Asume que el chat ID del usuario que lo inició es el objetivo.
    # Como el bot funciona con webhooks, no podemos almacenar fácilmente IDs aquí.
    # Para fines de prueba y despliegue simple, usaremos un placeholder y registrar el evento.
    
    logger.info("Tarea programada de noticias iniciada.")
    
    # En un bot de producción, se iteraría sobre los IDs de chat guardados en una DB.
    # Para que funcione la demo, usaremos el chat_id que se pueda obtener de alguna interacción.
    
    # Placeholder: Enviaremos un mensaje simple para confirmar la ejecución.
    # Para el envío real, necesitarías el ID de chat del usuario.
    # Por ahora, simplemente registramos que la función se ejecutó.
    
    # Si quieres que realmente envíe, deberías reemplazar 'CHAT_ID_DE_PRUEBA' por el ID de tu chat (como string)
    CHAT_ID_DE_PRUEBA = os.getenv("PROGRAMMED_CHAT_ID")
    if CHAT_ID_DE_PRUEBA:
        await context.bot.send_message(
            chat_id=CHAT_ID_DE_PRUEBA, 
            text="¡Alarma! La tarea diaria programada se ha ejecutado. Necesita ser configurada para buscar y enviar noticias reales."
        )
    else:
        logger.warning("No se encontró CHAT_ID_DE_PRUEBA para la tarea programada. La tarea se ejecutó, pero no pudo enviar el mensaje.")


def main() -> None:
    """Inicia el bot usando Webhooks."""
    
    if not TOKEN:
        logger.error("Error: La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")
        return

    # Crear la Aplicación y obtener el JobQueue
    application = Application.builder().token(TOKEN).build()
    job_queue = application.job_queue

    # --- REGISTRO DE HANDLERS ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("noticias", noticias))

    # --- CONFIGURACIÓN DE LA TAREA PROGRAMADA ---
    
    # Zona horaria de Uruguay (UTC-3)
    time_zone = pytz.timezone('America/Montevideo')
    
    # Hora de envío (8:00 AM hora de Uruguay, UTC-3)
    # Se debe configurar en la hora UTC, por lo que 8 AM en Uruguay es 11 AM UTC (o 10 AM UTC en horario de verano).
    # Asumiendo que Render opera en UTC, configuramos la hora local de Uruguay:
    time_8am_uy = time(hour=8, minute=0, tzinfo=time_zone)

    # El JobQueue ya está disponible porque instalamos python-telegram-bot[job-queue]
    job_queue.run_daily(enviar_noticias_programadas, time=time_8am_uy)
    logger.info(f"Tarea diaria programada para las {time_8am_uy.strftime('%H:%M')} hs (UY).")
    
    # --- INICIO DEL BOT USANDO WEBHOOKS (Obligatorio en Render) ---
    
    if WEBHOOK_URL:
        # Modo Webhook (para despliegues en la nube como Render)
        
        # 1. Start Webhook: Escucha las peticiones entrantes de Telegram
        application.run_webhook(
            listen="0.0.0.0", # Escucha en todas las interfaces de red
            port=PORT,
            url_path=TOKEN, # La ruta de la URL debe ser secreta (usamos el token)
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}" # URL completa para que Telegram envíe las actualizaciones
        )
        logger.info(f"Aplicación iniciada en modo Webhook en el puerto {PORT}.")
    
    else:
        # Modo Polling (para desarrollo local o bots sin Webhooks)
        logger.warning("WEBHOOK_URL no configurada. Ejecutando en modo Polling (¡No recomendado para Render!).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
