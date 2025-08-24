# scraper/acciones_extractor.py - Extracción especializada de acciones (versión simplificada)
import pandas as pd
import time
from utils.helpers import clean_price_text, extract_ticker_from_id, log_progress, safe_click_with_retry
from utils.constants import SELECTORS, LOG_MESSAGES

class AccionesExtractor:
    def __init__(self, page):
        self.page = page
    
    def extract_to_df(self, url):
        """
        Extrae cotizaciones de acciones con precios de cierre anterior
        """
        try:
            print(f"📊 Navegando a acciones: {url}")
            self.page.goto(url, wait_until='networkidle')
            time.sleep(5)
            
            # Obtener elementos de precios
            price_elements = self.page.locator(SELECTORS['price_elements'])
            count = price_elements.count()
            
            if count == 0:
                print("❌ No se encontraron elementos de precios")
                return pd.DataFrame()
            
            print(f"📊 Extrayendo cotizaciones de acciones...")
            
            # Procesar cada acción
            data = []
            for i in range(count):
                try:
                    # Solo mostrar progreso cada 5 acciones para reducir logs
                    if i % 5 == 0:
                        print(f"--- Procesando acción {i+1}/{count} ---")
                    
                    accion_data = self._process_single_accion(price_elements.nth(i), i)
                    if accion_data:
                        data.append(accion_data)
                        if i % 5 == 0:
                            print(f"📊 {accion_data['accion']}: ${accion_data['precio']:,.2f}")
                            print(f"✅ {accion_data['accion']} procesada correctamente")
                
                except Exception as e:
                    continue
            
            # Crear DataFrame
            if data:
                df = pd.DataFrame(data)
                print(f"✅ {len(df)} acciones extraídas exitosamente")
                return df
            else:
                print("⚠️ No se procesaron acciones")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Error extrayendo acciones: {str(e)}")
            return pd.DataFrame()
    
    def _process_single_accion(self, price_element, index):
        """Procesa una acción individual"""
        # Obtener datos básicos
        element_id = price_element.get_attribute('id')
        price_text = price_element.text_content().strip()
        
        if not element_id or not price_text:
            return None
        
        # Extraer ticker y precio
        ticker = extract_ticker_from_id(element_id)
        precio_actual = clean_price_text(price_text)
        
        if not precio_actual:
            return None
        
        # Obtener precio de cierre anterior (sin prints detallados)
        precio_cierre_anterior, precio_cierre_texto = self._get_precio_cierre_anterior(
            price_element, ticker, index
        )
        
        return {
            'accion': ticker,
            'precio': precio_actual,
            'precio_texto': price_text,
            'precio_cierre_anterior': precio_cierre_anterior,
            'precio_cierre_anterior_texto': precio_cierre_texto,
            'id_completo': element_id
        }
    
    def _get_precio_cierre_anterior(self, price_element, ticker, index):
        """Obtiene el precio de cierre anterior expandiendo el desplegable"""
        expand_button = self._find_expand_button(price_element, index)
        
        if not expand_button:
            return None, "N/A"
        
        try:
            # Click para abrir (sin prints)
            if not safe_click_with_retry(expand_button):
                return None, "N/A"
            
            time.sleep(1.5)
            
            # Buscar precio de cierre
            cierre_elements = self.page.locator(SELECTORS['cierre_anterior'])
            precio_cierre = None
            precio_texto = "N/A"
            
            for i in range(cierre_elements.count()):
                element = cierre_elements.nth(i)
                if element.is_visible():
                    texto = element.text_content().strip()
                    
                    precio_limpio = texto.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
                    try:
                        precio_cierre = float(precio_limpio)
                        precio_texto = texto
                        break
                    except ValueError:
                        continue
            
            # Click para cerrar
            safe_click_with_retry(expand_button, sleep_time=0.5)
            
            return precio_cierre, precio_texto
            
        except Exception as e:
            try:
                expand_button.click()  # Intentar cerrar
            except:
                pass
            return None, "N/A"
    
    def _find_expand_button(self, price_element, index):
        """Encuentra el botón de expansión correspondiente a la acción"""
        expand_buttons = self.page.locator(SELECTORS['expand_button_acciones'])
        
        # Método 1: Por posición relativa
        try:
            element_box = price_element.bounding_box()
            if element_box:
                for j in range(expand_buttons.count()):
                    btn = expand_buttons.nth(j)
                    if btn.is_visible():
                        btn_box = btn.bounding_box()
                        if (btn_box and 
                            abs(element_box['y'] - btn_box['y']) < 50):
                            return btn
        except:
            pass
        
        # Método 2: Por índice
        try:
            if index < expand_buttons.count():
                btn = expand_buttons.nth(index)
                if btn.is_visible():
                    return btn
        except:
            pass
        
        return None