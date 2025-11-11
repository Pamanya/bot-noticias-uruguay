import aiohttp
import logging
import asyncio
import feedparser 
import os 
from datetime import datetime

# Configuración de logging para scraper
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# RSS Feeds 
# Las URLs son fijas para garantizar estabilidad
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
    """
    Obtiene noticias desde un feed RSS de forma segura.
    Implementa manejo de errores de conexión, timeout y parsing.
    """
    try:
        # Timeout de 20 segundos para evitar bloqueos
        async with session.get(feed['url'], timeout=20) as response:
            if response.status == 200:
                
                # CORRECCIÓN DE ENCODING: Usa la codificación reportada por el servidor o 'utf-8' por defecto
                # Esto soluciona el error del 'codec can't decode'
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
        logging.error(f"Error de conexión (DNS o SSL) al portal: {feed['nombre']}")
        return []
    except asyncio.TimeoutError:
        logging.error(f"Tiempo de espera agotado (20s) al portal: {feed['nombre']}")
        return []
    except Exception as e:
        # Captura cualquier error de parsing o inesperado.
        logging.exception(f"Error desconocido al procesar RSS de {feed['nombre']}")
        return []

async def obtener_noticias_uruguay():
    """Coordina la obtención asíncrona de noticias de todos los portales."""
    todas_noticias = []
    
    # User-Agent para evitar ser bloqueado
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        tareas = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        
        # asyncio.gather asegura que las tareas se ejecuten en paralelo. 
        # Es robusto porque obtener_noticias_rss garantiza devolver una lista (incluso vacía).
        resultados = await asyncio.gather(*tareas) 
        
        for noticias in resultados:
            if noticias is not None:
                todas_noticias.extend(noticias)
    
    if not todas_noticias:
         logging.warning("La función obtener_noticias_uruguay no pudo consolidar ninguna noticia.")
         return []
    
    # Devuelve el top 10 general
    return todas_noticias[:10]
