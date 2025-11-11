import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio
import feedparser # Sin comentarios
import os 
from datetime import datetime

# Configuración de logging para scraper
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# RSS Feeds 
RSS_FEEDS = [
    {'nombre': 'El País', 'url': 'https://www.elpais.com.uy/rss/'},
    {'nombre': 'El Observador', 'url': 'https://www.elobservador.com.uy/rss/homepage.xml'},
    {'nombre': 'La Diaria', 'url': 'https://ladiaria.com.uy/feed/'},
    {'nombre': 'Montevideo Portal', 'url': 'https://www.montevideo.com.uy/rss/index.xml'},
    {'nombre': 'Subrayado', 'url': 'https://www.subrayado.com.uy/rss/'},
    {'nombre': 'La Red 21', 'url': 'https://www.lr21.com.uy/feed'},
    {'nombre': 'República', 'url': 'https://www.republica.com.uy/feed'},
]

async def obtener_noticias_rss(session, feed):
    """Obtiene noticias desde un feed RSS usando feedparser con corrección de encoding"""
    try:
        async with session.get(feed['url'], timeout=20) as response:
            if response.status == 200:
                
                # CORRECCIÓN DE ENCODING: Usa el encoding reportado por el servidor, o utf-8 por defecto.
                content = await response.text(encoding=response.charset or 'utf-8')
                
                parsed_feed = feedparser.parse(content)
                items = parsed_feed.entries[:3]
                
                noticias = []
                for entry in items:
                    titulo = entry.get('title')
                    link = entry.get('link')
                    
                    if titulo and link:
                        noticias.append({
                            'titulo': titulo.strip(),
                            'url': link.strip(),
                            'fuente': feed['nombre']
                        })
                
                return noticias
            else:
                 logging.error(f"Error HTTP {response.status} al obtener RSS de {feed['nombre']}")
                 return []
                 
    except aiohttp.ClientConnectorError:
        logging.error(f"Error de conexión al portal: {feed['nombre']}")
        return []
    except asyncio.TimeoutError:
        logging.error(f"Tiempo de espera agotado al portal: {feed['nombre']}")
        return []
    except Exception as e:
        logging.exception(f"Error desconocido al procesar RSS de {feed['nombre']}")
        return []

async def obtener_noticias_uruguay():
    """Obtiene noticias de todos los portales uruguayos"""
    todas_noticias = []
    
    # Headers para simular un navegador y evitar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Usamos un solo ClientSession con headers
    async with aiohttp.ClientSession(headers=headers) as session:
        tareas = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        
        resultados = await asyncio.gather(*tareas) 
        
        for noticias in resultados:
            todas_noticias.extend(noticias)
    
    if not todas_noticias:
         logging.warning("La función obtener_noticias_uruguay terminó sin noticias.")
         return []
    
    return todas_noticias[:10]
