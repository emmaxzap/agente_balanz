# scraper/cedears_extractor.py - Extracción especializada de CEDEARs (versión simplificada)
import pandas as pd
import time
from utils.helpers import clean_price_text, extract_ticker_from_id, safe_click_with_retry
from utils.constants import SELECTORS, SCROLL_CONFIG, LOG_MESSAGES

class CedearsExtractor:
    def __init__(self, page):
        self.page = page
    
    def extract_to_df(self, url, max_cedears=60):
        """
        Extrae cotizaciones de CEDEARs con scroll limitado para optimizar velocidad
        """
        try:
            print(f"🏛️ Navegando a CEDEARs: {url}")
            self.page.goto(url, wait_until='networkidle')
            time.sleep(5)
            
            # Realizar scroll limitado
            final_count = self._perform_limited_scroll(max_cedears)
            
            if final_count == 0:
                print("❌ No se encontraron elementos CEDEARs")
                return pd.DataFrame()
            
            # Extraer datos con precios de cierre
            return self._extract_cedears_data(min(final_count, max_cedears))
            
        except Exception as e:
            print(f"❌ Error extrayendo CEDEARs: {str(e)}")
            return pd.DataFrame()
    
    def _perform_limited_scroll(self, max_cedears):
        """Realiza scroll limitado para cargar solo los primeros CEDEARs"""
        print(f"📊 Extrayendo cotizaciones de CEDEARs...")
        
        previous_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50
        no_change_counter = 0
        max_no_change = 8
        
        while scroll_attempts < max_scroll_attempts:
            # Contar elementos actuales
            current_elements = self.page.locator(SELECTORS['price_elements'])
            current_count = current_elements.count()
            
            # Mostrar progreso solo cada 10 scrolls
            if scroll_attempts % 10 == 0 or current_count != previous_count:
                print(f"   📊 {current_count} CEDEARs cargados...")
            
            # Si ya tenemos suficientes CEDEARs, parar
            if current_count >= max_cedears:
                print(f"✅ {current_count} CEDEARs cargados")
                break
            
            # Verificar si hay cambios
            if current_count == previous_count:
                no_change_counter += 1
                if no_change_counter >= max_no_change:
                    print(f"✅ {current_count} CEDEARs cargados")
                    break
            else:
                no_change_counter = 0
            
            previous_count = current_count
            
            # Scroll más simple y rápido
            if scroll_attempts % 2 == 0:
                self.page.keyboard.press('PageDown')
            else:
                self.page.evaluate('window.scrollBy(0, 800)')
            
            time.sleep(0.3)
            scroll_attempts += 1
        
        final_count = self.page.locator(SELECTORS['price_elements']).count()
        return final_count
    
    def _extract_cedears_data(self, final_count):
        """Extrae datos de todos los CEDEARs con precios de cierre"""        
        final_elements = self.page.locator(SELECTORS['price_elements'])
        data = []
        
        for i in range(final_count):
            try:
                # Mostrar progreso cada 10 CEDEARs para reducir logs
                if i % 10 == 0:
                    print(f"--- Procesando CEDEAR {i+1}/{final_count} ---")
                
                cedear_data = self._process_single_cedear(final_elements.nth(i), i, final_count)
                if cedear_data:
                    data.append(cedear_data)
                    if i % 10 == 0:
                        print(f"✅ {cedear_data['cedear']} procesado correctamente")
                        
            except Exception as e:
                continue
        
        # Crear DataFrame
        if data:
            df = pd.DataFrame(data)
            print(f"✅ {len(df)} CEDEARs extraídos exitosamente")
            return df
        else:
            print("⚠️ No se procesaron CEDEARs")
            return pd.DataFrame()
    
    def _process_single_cedear(self, price_element, index, total):
        """Procesa un CEDEAR individual"""
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
            'cedear': ticker,
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
            # Scroll hacia el elemento y click (sin prints)
            price_element.scroll_into_view_if_needed()
            time.sleep(0.2)
            
            if not safe_click_with_retry(expand_button, sleep_time=0.5):
                return None, "N/A"
            
            time.sleep(1)
            
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
            
            # Cerrar desplegable
            safe_click_with_retry(expand_button, sleep_time=0.2)
            
            return precio_cierre, precio_texto
            
        except Exception as e:
            try:
                expand_button.click()
            except:
                pass
            return None, "N/A"
    
    def _find_expand_button(self, price_element, index):
        """Encuentra el botón de expansión correspondiente al CEDEAR"""
        expand_buttons = self.page.locator(SELECTORS['expand_button_cedears']).locator('..')
        
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