import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
from datetime import datetime
import json
import os
from scraper import obtener_noticias_uruguay

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Archivo para guardar suscriptores
SUSCRIPTORES_FILE = 'suscriptores.json'

def cargar_suscriptores():
    """Carga la lista de suscriptores desde el archivo"""
    if os.path.exists(SUSCRIPTORES_FILE):
        with open(SUSCRIPTORES_FILE, 'r') as f:
            return json.load(f)
    return []

def guardar_suscriptores(suscriptores):
    """Guarda la lista de suscriptores en el archivo"""
    with open(SUSCRIPTORES_FILE, 'w') as f:
        json.dump(suscriptores, f)

# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida"""
    mensaje = """
🇺🇾 *Bot de Noticias de Uruguay* 🇺🇾

Comandos disponibles:
/noticias - Ver las 10 noticias más destacadas
/suscribir - Recibir noticias automáticamente (8am y 8pm)
/desuscribir - Dejar de recibir noticias
/help - Ver esta ayuda
    """
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía las noticias actuales"""
    await update.message.reply_text("🔍 Buscando las últimas noticias de Uruguay...")
    
    try:
        noticias = await obtener_noticias_uruguay()
        mensaje = "📰 *TOP 10 NOTICIAS DE URUGUAY*\n\n"
        
        for i, noticia in enumerate(noticias[:10], 1):
            mensaje += f"*{i}. {noticia['titulo']}*\n"
            mensaje += f"   📌 {noticia['fuente']}\n"
            mensaje += f"   🔗 {noticia['url']}\n\n"
        
        mensaje += f"_Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}_"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Error al obtener noticias: {e}")
        await update.message.reply_text("❌ Error al obtener noticias. Intenta de nuevo más tarde.")

async def suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suscribe al usuario para recibir noticias automáticamente"""
    chat_id = update.effective_chat.id
    suscriptores = cargar_suscriptores()
    
    if chat_id not in suscriptores:
        suscriptores.append(chat_id)
        guardar_suscriptores(suscriptores)
        await update.message.reply_text("✅ ¡Te has suscrito! Recibirás noticias a las 8:00 AM y 8:00 PM (GMT-3)")
    else:
        await update.message.reply_text("ℹ️ Ya estás suscrito a las noticias.")

async def desuscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desuscribe al usuario"""
    chat_id = update.effective_chat.id
    suscriptores = cargar_suscriptores()
    
    if chat_id in suscriptores:
        suscriptores.remove(chat_id)
        guardar_suscriptores(suscriptores)
        await update.message.reply_text("❌ Te has desuscrito. Ya no recibirás noticias automáticas.")
    else:
        await update.message.reply_text("ℹ️ No estabas suscrito.")

async def enviar_noticias_programadas(context: ContextTypes.DEFAULT_TYPE):
    """Envía noticias a todos los suscriptores"""
    suscriptores = cargar_suscriptores()
    
    if not suscriptores:
        return
    
    try:
        noticias = await obtener_noticias_uruguay()
        mensaje = "📰 *NOTICIAS DEL DÍA - URUGUAY*\n\n"
        
        for i, noticia in enumerate(noticias[:10], 1):
            mensaje += f"*{i}. {noticia['titulo']}*\n"
            mensaje += f"   📌 {noticia['fuente']}\n"
            mensaje += f"   🔗 {noticia['url']}\n\n"
        
        mensaje += f"_Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}_"
        
        for chat_id in suscriptores:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=mensaje,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                await asyncio.sleep(0.5)  # Evitar límite de rate
            except Exception as e:
                logging.error(f"Error al enviar mensaje a {chat_id}: {e}")
    except Exception as e:
        logging.error(f"Error en envío programado: {e}")

def main():
    """Función principal"""
    TOKEN = os.getenv('TOKEN')
    
    if not TOKEN:
        raise ValueError("No se encontró el TOKEN. Configura la variable de entorno TOKEN")
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("noticias", noticias))
    app.add_handler(CommandHandler("suscribir", suscribir))
    app.add_handler(CommandHandler("desuscribir", desuscribir))
    
    # Tareas programadas (8:00 AM y 8:00 PM hora Uruguay GMT-3)
    job_queue = app.job_queue
    job_queue.run_daily(enviar_noticias_programadas, time=datetime.strptime("08:00", "%H:%M").time())
    job_queue.run_daily(enviar_noticias_programadas, time=datetime.strptime("20:00", "%H:%M").time())
    
    logging.info("Bot iniciado...")
    app.run_polling()

if __name__ == '__main__':
    main()