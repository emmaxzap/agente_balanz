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