# utils/helpers.py - Funciones auxiliares
import pandas as pd
import time

def clean_price_text(price_text):
    """Limpia el texto del precio para convertirlo a float"""
    try:
        # Remover puntos de miles y cambiar coma decimal por punto
        clean_price = price_text.replace('.', '').replace(',', '.')
        return float(clean_price)
    except (ValueError, AttributeError):
        return None

def safe_click_with_retry(element, max_retries=3, sleep_time=0.5):
    """Hace click en un elemento con reintentos en caso de fallo"""
    for attempt in range(max_retries):
        try:
            if element.is_visible():
                element.click()
                time.sleep(sleep_time)
                return True
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} falló: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(sleep_time * 2)
            continue
    return False

def extract_ticker_from_id(element_id):
    """Extrae el ticker del ID completo"""
    if not element_id:
        return None
    return element_id.split('-')[0] if '-' in element_id else element_id

def create_empty_dataframe(columns):
    """Crea un DataFrame vacío con las columnas especificadas"""
    return pd.DataFrame(columns=columns)

def log_progress(current, total, interval=50):
    """Log de progreso cada cierto intervalo"""
    if current % interval == 0 or current == 1:
        print(f"   📊 Procesando: {current}/{total}")

def find_element_by_selectors(page, selectors, description="elemento"):
    """Busca un elemento usando una lista de selectores posibles"""
    for selector in selectors:
        try:
            if page.locator(selector).count() > 0:
                print(f"✅ {description} encontrado: {selector}")
                return page.locator(selector).first, selector
        except Exception:
            continue
    
    print(f"⚠️ No se encontró {description}")
    return None, None