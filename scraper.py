import aiohttp
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Portales de noticias de Uruguay
PORTALES = [
    {
        'nombre': 'El País',
        'url': 'https://www.elpais.com.uy/',
        'selector': 'article h2 a, .article-title a'
    },
    {
        'nombre': 'El Observador',
        'url': 'https://www.elobservador.com.uy/',
        'selector': 'article h2 a, .headline a'
    },
    {
        'nombre': 'La Diaria',
        'url': 'https://ladiaria.com.uy/',
        'selector': 'article h2 a, .article-title a'
    },
    {
        'nombre': 'Montevideo Portal',
        'url': 'https://www.montevideo.com.uy/',
        'selector': 'article h2 a, .title a'
    },
    {
        'nombre': 'Subrayado',
        'url': 'https://www.subrayado.com.uy/',
        'selector': 'article h2 a, .nota-title a'
    },
]

# RSS Feeds (más confiable que scraping)
RSS_FEEDS = [
    {'nombre': 'El País', 'url': 'https://www.elpais.com.uy/rss/'},
    {'nombre': 'El Observador', 'url': 'https://www.elobservador.com.uy/rss/homepage.xml'},
    {'nombre': 'La Diaria', 'url': 'https://ladiaria.com.uy/feed/'},
    {'nombre': 'Montevideo Portal', 'url': 'https://www.montevideo.com.uy/rss/index.xml'},
    {'nombre': 'Subrayado', 'url': 'https://www.subrayado.com.uy/rss/'},
    {'nombre': 'La Red 21', 'url': 'https://www.lr21.com.uy/feed'},
    {'nombre': 'República', 'url': 'https://www.republica.com.uy/feed'},
    {'nombre': 'Búsqueda', 'url': 'https://www.busqueda.com.uy/rss'},
]

async def obtener_noticias_rss(session, feed):
    """Obtiene noticias desde un feed RSS"""
    try:
        async with session.get(feed['url'], timeout=10) as response:
            if response.status == 200:
                content = await response.text()
                soup = BeautifulSoup(content, 'xml')
                items = soup.find_all('item')[:3]  # Top 3 de cada fuente
                
                noticias = []
                for item in items:
                    titulo = item.find('title')
                    link = item.find('link')
                    
                    if titulo and link:
                        noticias.append({
                            'titulo': titulo.text.strip(),
                            'url': link.text.strip(),
                            'fuente': feed['nombre']
                        })
                
                return noticias
    except Exception as e:
        logging.error(f"Error al obtener RSS de {feed['nombre']}: {e}")
        return []

async def obtener_noticias_uruguay():
    """Obtiene noticias de todos los portales uruguayos"""
    todas_noticias = []
    
    async with aiohttp.ClientSession() as session:
        tareas = [obtener_noticias_rss(session, feed) for feed in RSS_FEEDS]
        resultados = await asyncio.gather(*tareas)
        
        for noticias in resultados:
            todas_noticias.extend(noticias)
    
    # Si no hay noticias, devolver algunas de ejemplo
    if not todas_noticias:
        todas_noticias = [
            {
                'titulo': 'No se pudieron obtener noticias en este momento',
                'url': 'https://www.google.com/search?q=noticias+uruguay',
                'fuente': 'Sistema'
            }
        ]
    
    return todas_noticias[:10]

import asyncio