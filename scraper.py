import aiohttp
import logging
import asyncio
import feedparser 
import os 
from datetime import datetime
from bs4 import BeautifulSoup

# Configuración de logging para scraper
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 1. FUENTES QUE USAN WEB SCRAPING DIRECTO (Los Conflictivos) ---
# Usamos esta lista para los portales que bloquean el RSS (El País) o tienen feeds inconsistentes.
HTML_FEEDS = [
    # {'nombre': 'El País', 'url': 'https://www.elpais.com.uy/', 'selector': 'h3.news-title a'}, # El País está bloqueando con 403. Mantener por si se habilita
    {'nombre': 'El Observador', 'url': 'https://www.elobservador.com.uy/', 'selector': 'h2 a'},
    {'nombre': 'Montevideo Portal', 'url': 'https://www.montevideo.com.uy/', 'selector': 'div.news-main-box h3 a'},
    {'nombre': 'Subrayado', 'url': 'https://www.subrayado.com.uy/', 'selector': 'a.post-link'},
]


# --- 2. FUENTES QUE USAN RSS (Más de 20 en total) ---
# Usamos esta lista para portales que tienen feeds RSS funcionales.
RSS_FEEDS = [
    {'nombre': 'La Diaria', 'url': 'https://ladiaria.com.uy/feed/'},
    {'nombre': 'La Red 21', 'url': 'https://www.lr21.com.uy/feed'},
    {'nombre': 'República', 'url': 'https://www.republica.com.uy/feed/'},
    
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

# Cabeceras (headers) que simulan ser un navegador web real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
}

# --- FUNCIONES DE OBTENCIÓN DE NOTICIAS ---

async def obtener_noticias_rss(session, feed):
    """Obtiene noticias de un feed RSS de forma segura, leyendo bytes crudos."""
    try:
        async with session.get(feed['url'], timeout=20) as response:
            if response.status == 200:
                # Leemos bytes crudos para evitar errores de codificación
                content_bytes = await response.read()
                
                parsed_feed = feedparser.parse(content_bytes)
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
                 logging.error(f"Error HTTP {response.status} al obtener RSS de {feed['nombre']}")
                 return []
                 
    except Exception as e:
        logging.error(f"Error al procesar RSS de {feed['nombre']}: {e}")
        return []

async def obtener_noticias_html(session, feed):
    """Realiza Web Scraping directo de la página HTML."""
    try:
        # Usamos las cabeceras de navegador para evitar bloqueos 403
        async with session.get(feed['url'], timeout=20, headers=HEADERS) as response:
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'lxml')
                
                # Buscamos todos los elementos que coincidan con el selector CSS (por ej: 'h3.news-title a')
                enlaces_encontrados = soup.select(feed['selector'])
                
                noticias = []
                # Limitamos a un máximo de 3 noticias por fuente
                for enlace in enlaces_encontrados[:3]: 
                    titulo = enlace.get_text().strip()
                    link = enlace.get('href')
                    
                    # Garantizamos que el enlace sea absoluto si es relativo
                    if link and not link.startswith('http'):
                        link = feed['url'].rstrip('/') + link
                    
                    if titulo and link:
                        noticias.append({
                            'titulo': titulo,
                            'url': link,
                            'fuente': feed['nombre']
                        })
                        
                return noticias
            else:
                 logging.error(f"Error HTTP {response.status} al obtener HTML de {feed['nombre']}")
                 return []
                 
    except Exception as e:
        logging.error(f"Error al procesar HTML de {feed['nombre']}: {e}")
        return []

async def obtener_noticias_uruguay():
    """Coordina la obtención asíncrona de noticias de TODOS los portales (RSS y HTML)."""
    todas_noticias = []
    
    # --- 1. TAREAS DE SCRAPING HTML ---
    # Usamos headers=HEADERS en ClientSession para las solicitudes HTML
    async with aiohttp.ClientSession() as session:
        # Nota: La función obtener_noticias_html ya usa HEADERS en su llamada a session.get.
        tareas_html = [obtener_noticias_html(session, feed) for feed in HTML_FEEDS]
        resultados_html = await asyncio.gather(*tareas_html) 
        
        for noticias in resultados_html:
            if noticias is not None:
                todas_noticias.extend(noticias)

    # --- 2. TAREAS DE SCRAPING RSS ---
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tareas_rss = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        resultados_rss = await asyncio.gather(*tareas_rss) 
        
        for noticias in resultados_rss:
            if noticias is not None:
                todas_noticias.extend(noticias)
    
    if not todas_noticias:
         logging.warning("La función obtener_noticias_uruguay no pudo consolidar ninguna noticia.")
         return []
    
    # Devolvemos el TOP 10 de la gran lista consolidada
    return todas_noticias[:10]
