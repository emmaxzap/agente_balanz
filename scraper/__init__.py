# ============================================================================
# scraper/__init__.py
# ============================================================================

"""
Módulo de web scraping para Balanz
Contiene todas las clases y funciones necesarias para extraer datos de Balanz
"""

from .web_scraper import WebScraperPlaywright
from .login_handler import LoginHandler
from .acciones_extractor import AccionesExtractor
from .cedears_extractor import CedearsExtractor

__version__ = "2.0.0"
__all__ = [
    'WebScraperPlaywright',
    'LoginHandler', 
    'AccionesExtractor',
    'CedearsExtractor'
]
