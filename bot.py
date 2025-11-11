import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

# Token desde variable de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Fuentes de noticias Uruguay
NEWS_SOURCES = {
    'el_pais': 'https://www.elpais.com.uy/',
    'el_observador': 'https://www.elobservador.com.uy/',
    'la_diaria': 'https://ladiaria.com.uy/'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        '¡Hola! Soy tu bot de noticias de Uruguay 🇺🇾\n\n'
        'Comandos disponibles:\n'
        '/noticias - Ver últimas noticias\n'
        '/help - Ayuda'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    await update.message.reply_text(
        'Comandos:\n'
        '/start - Iniciar bot\n'
        '/noticias - Últimas noticias de Uruguay\n'
        '/help - Esta ayuda'
    )

async def fetch_news():
    """Obtiene noticias de El País Uruguay"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(NEWS_SOURCES['el_pais'], timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar títulos de noticias
                    headlines = []
                    # El País usa diferentes selectores, intentamos varios
                    for selector in ['h2', 'h3', '.title', '.headline']:
                        titles = soup.find_all(selector, limit=5)
                        if titles:
                            for title in titles:
                                text = title.get_text().strip()
                                if text and len(text) > 10:
                                    headlines.append(text)
                            if headlines:
                                break
                    
                    return headlines[:5] if headlines else ['No se pudieron cargar noticias']
                else:
                    return ['Error al cargar noticias']
    except Exception as e:
        print(f"Error: {e}")
        return ['Error al obtener noticias']

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /noticias"""
    await update.message.reply_text('Cargando noticias... ⏳')
    
    headlines = await fetch_news()
    
    message = f"📰 *Noticias de Uruguay*\n"
    message += f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
    
    for i, headline in enumerate(headlines, 1):
        message += f"{i}. {headline}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def main():
    """Función principal"""
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN no configurado")
        return
    
    print("Iniciando bot...")
    
    # Crear aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Registrar comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("noticias", noticias))
    
    # Iniciar bot
    print("Bot iniciado correctamente ✓")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())
