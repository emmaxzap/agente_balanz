# scraper/web_scraper.py - Clase principal del scraper
from playwright.sync_api import sync_playwright
import time
from config import BROWSER_CONFIG, URLS
from .login_handler import LoginHandler
from .acciones_extractor import AccionesExtractor
from .cedears_extractor import CedearsExtractor

class WebScraperPlaywright:
    def __init__(self, headless=None):
        self.headless = headless if headless is not None else BROWSER_CONFIG['headless']
        self.browser = None
        self.page = None
        self.playwright = None
        
        # Inicializar extractores
        self.login_handler = None
        self.acciones_extractor = None
        self.cedears_extractor = None
        
    def start_browser(self):
        """Inicializa el navegador"""
        print("🔧 Iniciando navegador...")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=BROWSER_CONFIG['args']
        )
        self.page = self.browser.new_page()
        
        # Headers para parecer más humano
        self.page.set_extra_http_headers({
            'User-Agent': BROWSER_CONFIG['user_agent']
        })
        
        # Inicializar extractores con la página
        self.login_handler = LoginHandler(self.page)
        self.acciones_extractor = AccionesExtractor(self.page)
        self.cedears_extractor = CedearsExtractor(self.page)
        
        print("✅ Navegador iniciado correctamente")
    
    def login(self, url, username, password):
        """Realiza login usando el handler especializado"""
        if not self.login_handler:
            raise Exception("Navegador no iniciado. Ejecuta start_browser() primero.")
        
        return self.login_handler.perform_login(url, username, password)
    
    def extract_stock_prices_to_df(self):
        """Extrae cotizaciones de acciones"""
        if not self.acciones_extractor:
            raise Exception("Navegador no iniciado. Ejecuta start_browser() primero.")
        
        return self.acciones_extractor.extract_to_df(URLS['acciones'])
    
    def extract_cedears_to_df(self):
        """Extrae cotizaciones de CEDEARs"""
        if not self.cedears_extractor:
            raise Exception("Navegador no iniciado. Ejecuta start_browser() primero.")
        
        return self.cedears_extractor.extract_to_df(URLS['cedears'])
    
    def close(self):
        """Cierra el navegador"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✅ Navegador cerrado")