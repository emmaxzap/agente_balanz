# utils/constants.py - Constantes del proyecto

# Selectores CSS
SELECTORS = {
    'price_elements': 'p.mb-0.fw-semibold.text-color-primary-alt-dark[id]',
    'expand_button_acciones': 'app-button-expand a.cursor-pointer',
    'expand_button_cedears': 'a.cursor-pointer img[src*="angledown"]',
    'cierre_anterior': '#CotizacionPrecioCierreAnterior',
    
    # Login selectors
    'username_fields': [
        'input[formcontrolname="user"]',
        'input[formcontrolname="username"]',
        'input[name="username"]',
        'input[type="email"]'
    ],
    'password_fields': [
        'input[formcontrolname="pass"]',
        'input[formcontrolname="password"]',
        'input[type="password"]'
    ],
    'submit_buttons': [
        'button:has-text("Continuar")',
        'button:has-text("Ingresar")',
        'button[type="submit"]'
    ]
}

# Configuración de scroll para CEDEARs
SCROLL_CONFIG = {
    'max_attempts': 500,
    'max_no_change': 15,
    'checkpoint_interval': 50,
    'sleep_time': 0.8,
    'target_cedears': 960
}

# Mensajes de log
LOG_MESSAGES = {
    'login_step1': "🔹 PASO 1: Ingresando usuario",
    'login_step2': "🔹 PASO 2: Ingresando contraseña",
    'extracting_acciones': "📊 Extrayendo cotizaciones de acciones...",
    'extracting_cedears': "📈 Extrayendo cotizaciones de CEDEARs...",
    'scroll_progress': "📊 Progreso de carga:",
    'processing_item': "--- Procesando {} {}/{} ---"
}