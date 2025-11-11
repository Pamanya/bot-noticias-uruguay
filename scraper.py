import aiohttp
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import asyncio
import feedparser # <-- NUEVA IMPORTACIÓN: Usaremos feedparser para RSS, es más robusto

# Configuración de logging para scraper
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# RSS Feeds (Usaremos feedparser en lugar de BeautifulSoup para RSS)
RSS_FEEDS = [
    {'nombre': 'El País', 'url': 'https://www.elpais.com.uy/rss/'},
    {'nombre': 'El Observador', 'url': 'https://www.elobservador.com.uy/rss/homepage.xml'},
    {'nombre': 'La Diaria', 'url': 'https://ladiaria.com.uy/feed/'},
    {'nombre': 'Montevideo Portal', 'url': 'https://www.montevideo.com.uy/rss/index.xml'},
    {'nombre': 'Subrayado', 'url': 'https://www.subrayado.com.uy/rss/'},
    {'nombre': 'La Red 21', 'url': 'https://www.lr21.com.uy/feed'},
    {'nombre': 'República', 'url': 'https://www.republica.com.uy/feed'},
    # {'nombre': 'Búsqueda', 'url': 'https://www.busqueda.com.uy/rss'}, # A veces da problemas
]

async def obtener_noticias_rss(session, feed):
    """Obtiene noticias desde un feed RSS usando feedparser"""
    try:
        async with session.get(feed['url'], timeout=15) as response:
            if response.status == 200:
                content = await response.text()
                
                # Usamos feedparser, que es mucho más seguro para RSS
                parsed_feed = feedparser.parse(content)
                items = parsed_feed.entries[:3] # Top 3 de cada fuente
                
                noticias = []
                for entry in items:
                    # Usamos los campos estándar de feedparser
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
    
    # Headers para simular un navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Usamos un solo ClientSession
    async with aiohttp.ClientSession(headers=headers) as session:
        tareas = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        resultados = await asyncio.gather(*tareas)
        
        for noticias in resultados:
            todas_noticias.extend(noticias)
    
    # Si no hay noticias, devolver una lista vacía para que bot.py maneje el error
    if not todas_noticias:
         logging.warning("La función obtener_noticias_uruguay terminó sin noticias.")
         return []
    
    # Devuelve el top 10 de todas las noticias combinadas
    return todas_noticias[:10]
