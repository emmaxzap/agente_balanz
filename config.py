<<<<<<< HEAD
# config.py - Configuraciones centralizadas del proyecto
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de login de Balanz
LOGIN_CONFIG = {
    'url': "https://clientes.balanz.com/auth/login",
    'username': os.getenv('BALANZ_USERNAME', 'mhv220'),
    'password': os.getenv('BALANZ_PASSWORD', 'Gesti@n07')
}

# Configuración de Supabase
SUPABASE_CONFIG = {
    'url': os.getenv('SUPABASE_URL', 'https://akenrzmluwgzfbmsdvzg.supabase.co'),
    'key': os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFrZW5yem1sdXdnemZibXNkdnpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU5ODE5NDEsImV4cCI6MjA3MVU1Nzk0MX0.nQRyOTtO0O6jtsBEASSg1xv_SeTec-XVoEZ496bRZXc')
}

# URLs de extracción
URLS = {
    'acciones': "https://clientes.balanz.com/app/cotizaciones/acciones",
    'cedears': "https://clientes.balanz.com/app/cotizaciones/cedears"
}

# Configuración del navegador
BROWSER_CONFIG = {
    'headless': False,
    'args': [
        '--no-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security'
    ],
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
=======
import os
from datetime import timedelta

class Config:
    """Configuración base para la aplicación"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-secreta-temporal')
    
    # Configuración de PostgreSQL
    DB_HOST = os.environ.get('DB_HOST', '34.29.12.0')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'sistema_creditos')
    DB_USER = os.environ.get('DB_USER', 'app_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Geba.1149_2025')
    
    # Configuración de seguridad
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Indica que estamos usando PostgreSQL
    USE_POSTGRES = True

class DevelopmentConfig(Config):
    """Configuración para entorno de desarrollo"""
    DEBUG = True
    ENV = 'development'
    SESSION_COOKIE_SECURE = False
    
class ProductionConfig(Config):
    """Configuración para entorno de producción"""
    DEBUG = False
    ENV = 'production'
    SERVER_NAME = 'trackingdatax.com'
    PREFERRED_URL_SCHEME = 'https'
>>>>>>> 4267be413778e70e7e9c504266f65d63173cd634
