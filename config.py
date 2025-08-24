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
