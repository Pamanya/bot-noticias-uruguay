import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
from datetime import datetime
import json
import os
import pytz
from scraper import obtener_noticias_uruguay

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Archivo para guardar suscriptores
SUSCRIPTORES_FILE = 'suscriptores.json'

def cargar_suscriptores():
    """Carga la lista de suscriptores desde el archivo de forma segura."""
    if os.path.exists(SUSCRIPTORES_FILE):
        try:
            with open(SUSCRIPTORES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Archivo {SUSCRIPTORES_FILE} corrupto o vacío. Iniciando lista vacía.")
            return []
    return []

def guardar_suscriptores(suscriptores):
    """Guarda la lista de suscriptores en el archivo."""
    # Usamos try/except por si hay problemas de permisos en el entorno de Render
    try:
        with open(SUSCRIPTORES_FILE, 'w') as f:
            json.dump(suscriptores, f)
    except IOError as e:
        logging.error(f"Error al guardar suscriptores: {e}")

# --- Comandos del bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida"""
    mensaje = """
🇺🇾 *Bot de Noticias de Uruguay* 🇺🇾

Comandos disponibles:
/noticias - Ver las 10 noticias más destacadas
/suscribir - Recibir noticias automáticamente (8am y 8pm, hora de UY)
/desuscribir - Dejar de recibir noticias
/help - Ver esta ayuda
    """
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía las noticias actuales, con registro de errores detallado."""
    await update.message.reply_text("🔍 Buscando las últimas noticias de Uruguay...")
    
    try:
        noticias_list = await obtener_noticias_uruguay()
        
        if not noticias_list:
             await update.message.reply_text("⚠️ No se pudieron obtener noticias. Las fuentes no están disponibles o fallaron.")
             return

        mensaje = "📰 *TOP 10 NOTICIAS DE URUGUAY*\n\n"
        
        zona_horaria_uy = pytz.timezone('America/Montevideo')
        
        for i, noticia in enumerate(noticias_list[:10], 1):
            mensaje += f"*{i}. {noticia['titulo']}*\n"
            mensaje += f"    📌 {noticia['fuente']}\n"
            mensaje += f"    🔗 {noticia['url']}\n\n"
        
        mensaje += f"_Actualizado: {datetime.now(zona_horaria_uy).strftime('%d/%m/%Y %H:%M')}_"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        # logging.exception registra el Traceback completo para un diagnóstico fácil en Render
        logging.exception("Error CRÍTICO al ejecutar el comando /noticias.")
        await update.message.reply_text("❌ Error al obtener noticias. Intenta de nuevo más tarde.")

async def suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suscribe al usuario."""
    chat_id = update.effective_chat.id
    suscriptores = cargar_suscriptores()
    
    if chat_id not in suscriptores:
        suscriptores.append(chat_id)
        guardar_suscriptores(suscriptores)
        await update.message.reply_text("✅ ¡Te has suscrito! Recibirás noticias a las 8:00 AM y 8:00 PM (GMT-3)")
    else:
        await update.message.reply_text("ℹ️ Ya estás suscrito a las noticias.")

async def desuscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desuscribe al usuario."""
    chat_id = update.effective_chat.id
    suscriptores = cargar_suscriptores()
    
    if chat_id in suscriptores:
        suscriptores.remove(chat_id)
        guardar_suscriptores(suscriptores)
        await update.message.reply_text("❌ Te has desuscrito. Ya no recibirás noticias automáticas.")
    else:
        await update.message.reply_text("ℹ️ No estabas suscrito.")

async def enviar_noticias_programadas(context: ContextTypes.DEFAULT_TYPE):
    """Envía noticias a todos los suscriptores."""
    suscriptores = cargar_suscriptores()
    
    if not suscriptores:
        return
    
    try:
        noticias_list = await obtener_noticias_uruguay()
        
        if not noticias_list:
             logging.warning("El envío programado falló al obtener noticias. Saltando el envío.")
             return
             
        mensaje = "📰 *NOTICIAS DEL DÍA - URUGUAY*\n\n"
        zona_horaria_uy = pytz.timezone('America/Montevideo')
        
        for i, noticia in enumerate(noticias_list[:10], 1):
            mensaje += f"*{i}. {noticia['titulo']}*\n"
            mensaje += f"    📌 {noticia['fuente']}\n"
            mensaje += f"    🔗 {noticia['url']}\n\n"
        
        mensaje += f"_Actualizado: {datetime.now(zona_horaria_uy).strftime('%d/%m/%Y %H:%M')}_"
        
        for chat_id in suscriptores:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=mensaje,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Error al enviar mensaje a {chat_id}: {e}")
                
    except Exception as e:
        logging.exception("Error en envío programado.")


def main():
    """Función principal (síncona) que inicia el bot."""
    TOKEN = os.getenv('TOKEN')
    
    if not TOKEN:
        raise ValueError("No se encontró el TOKEN. Configura la variable de entorno TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()
    
    job_queue = app.job_queue
    
    # Registro de Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("noticias", noticias))
    app.add_handler(CommandHandler("suscribir", suscribir))
    app.add_handler(CommandHandler("desuscribir", desuscribir))
    
    # --- CORRECCIÓN FINAL (Conversión a UTC) ---
    # El servidor usa UTC. Uruguay (GMT-3) está 3 horas detrás de UTC.
    # 8:00 AM (08:00) Uruguay = 11:00 AM (11:00) UTC
    # 8:00 PM (20:00) Uruguay = 11:00 PM (23:00) UTC
    
    time_8am_utc = datetime.strptime("11:00", "%H:%M").time()
    time_8pm_utc = datetime.strptime("23:00", "%H:%M").time()

    # Programamos las tareas usando la hora UTC, eliminando 'tz' y 'tzinfo'
    job_queue.run_daily(enviar_noticias_programadas, time=time_8am_utc)
    job_queue.run_daily(enviar_noticias_programadas, time=time_8pm_utc)
    
    logging.info("Bot iniciado...")
    app.run_polling()

if __name__ == '__main__':
    main()
