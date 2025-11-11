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

# --- LISTA AMPLIADA DE URLs RSS (Más de 20) ---
# Se agregan más portales nacionales, departamentales y radios.
RSS_FEEDS = [
    # --- Portales Principales ---
    {'nombre': 'El Observador', 'url': 'https://www.elobservador.com.uy/rss/home.xml'},
    {'nombre': 'La Diaria', 'url': 'https://ladiaria.com.uy/feed/'},
    {'nombre': 'Montevideo Portal', 'url': 'https://www.montevideo.com.uy/rss/index.xml'},
    {'nombre': 'Subrayado', 'url': 'https://www.subrayado.com.uy/rss'},
    {'nombre': 'La Red 21', 'url': 'https://www.lr21.com.uy/feed'},
    {'nombre': 'República', 'url': 'https://www.republica.com.uy/feed/'},
    {'nombre': 'El País', 'url': 'https://www.elpais.com.uy/rss/'}, # Habilitado para re-intentar (puede fallar con 403)
    
    # --- Canales de TV ---
    {'nombre': 'Canal 10', 'url': 'https://www.canal10.com.uy/rss'},
    {'nombre': 'Teledoce (Telemundo)', 'url': 'https://www.teledoce.com/feed/'},
    {'nombre': 'Telenoche', 'url': 'https://www.telenoche.com.uy/rss'},

    # --- Radios ---
    {'nombre': 'El Espectador', 'url': 'https://www.elespectador.com/rss'},
    {'nombre': '970 Universal', 'url': 'https://www.970universal.com/feed/'},
    {'nombre': 'Radio Monte Carlo', 'url': 'https://www.radiomontecarlo.com.uy/feed/'},
    
    # --- Otros Portales y Departamentales ---
    {'nombre': 'Agencia Foco', 'url': 'https://www.foco.uy/feed/'},
    {'nombre': 'Crónicas', 'url': 'https://www.cronicas.com.uy/feed/'},
    {'nombre': 'Ecos', 'url': 'https://ecos.la/feed/'},
    {'nombre': 'La Mañana', 'url': 'https://www.lamañana.uy/feed/'},
    {'nombre': 'El Popular', 'url': 'https://www.elpopular.uy/feed/'},
    {'nombre': 'Agesor (Soriano)', 'url': 'https://www.agesor.com.uy/rss.php'},
    {'nombre': 'Durazno Digital', 'url': 'https://www.duraznodigital.uy/feed/'},
    {'nombre': 'Carmelo Portal', 'url': 'https://www.carmeloportal.com/feed/'},
    {'nombre': 'Diario El Pueblo (Salto)', 'url': 'https://diarioelpueblo.com.uy/feed/'},
]

async def obtener_noticias_rss(session, feed):
    """
    Obtiene noticias desde un feed RSS de forma segura.
    Lee bytes crudos y deja que feedparser maneje el encoding.
    """
    try:
        async with session.get(feed['url'], timeout=20) as response:
            if response.status == 200:
                
                # --- CORRECCIÓN DE ENCODING (Montevideo Portal, etc.) ---
                # Leemos bytes crudos (response.read) en lugar de texto (response.text)
                # Esto permite a feedparser detectar el encoding (ej: latin-1)
                content_bytes = await response.read()
                
                # feedparser analizará los bytes
                parsed_feed = feedparser.parse(content_bytes)
                # Reducimos a 2 noticias por fuente para más variedad en el TOP 10
                items = parsed_feed.entries[:2] 
                
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
                 # Errores 403 (Prohibido) o 404 (No Encontrado) se registran aquí
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        tareas = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        resultados = await asyncio.gather(*tareas) 
        
        for noticias in resultados:
            if noticias is not None:
                todas_noticias.extend(noticias)
    
    if not todas_noticias:
         logging.warning("La función obtener_noticias_uruguay no pudo consolidar ninguna noticia.")
         return []
    
    # El bot sigue devolviendo el TOP 10, pero ahora de un pool mucho más grande.
    return todas_noticias[:10]
