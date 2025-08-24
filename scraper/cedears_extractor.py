# scraper/cedears_extractor.py - Extracción especializada de CEDEARs
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
        
        Args:
            url: URL de la página de CEDEARs
            max_cedears: Máximo número de CEDEARs a extraer (por defecto 60)
        """
        try:
            print(f"\n📈 Navegando a CEDEARs: {url}")
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
        #print(f"🔄 Iniciando scroll limitado para cargar {max_cedears} CEDEARS...")
        #print(LOG_MESSAGES['scroll_progress'])
        
        previous_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50  # Reducido significativamente
        no_change_counter = 0
        max_no_change = 8  # Menos tolerancia
        
        while scroll_attempts < max_scroll_attempts:
            # Contar elementos actuales
            current_elements = self.page.locator(SELECTORS['price_elements'])
            current_count = current_elements.count()
            
            # Mostrar progreso
            if scroll_attempts % 5 == 0 or current_count != previous_count:
                print(f"   Scroll {scroll_attempts}: {current_count} CEDEARS cargados")
            
            # Si ya tenemos suficientes CEDEARs, parar
            if current_count >= max_cedears:
                print(f"✅ Objetivo alcanzado: {current_count} CEDEARS (objetivo: {max_cedears})")
                break
            
            # Verificar si hay cambios
            if current_count == previous_count:
                no_change_counter += 1
                if no_change_counter >= max_no_change:
                    print(f"✅ Carga completada con {current_count} CEDEARS")
                    break
            else:
                no_change_counter = 0
            
            previous_count = current_count
            
            # Scroll más simple y rápido
            if scroll_attempts % 2 == 0:
                self.page.keyboard.press('PageDown')
            else:
                self.page.evaluate('window.scrollBy(0, 800)')
            
            time.sleep(0.3)  # Menos tiempo de espera
            scroll_attempts += 1
        
        final_count = self.page.locator(SELECTORS['price_elements']).count()
        print(f"\n🎯 Scroll completado!")
        print(f"📊 Total de elementos encontrados: {final_count}")
        print(f"🔄 Scrolls realizados: {scroll_attempts}")
        
        return final_count
    
    def _perform_scroll_action(self, scroll_attempts):
        """Realiza diferentes tipos de scroll"""
        if scroll_attempts % 4 == 0:
            # Scroll con Page Down múltiple
            for _ in range(3):
                self.page.keyboard.press('PageDown')
                time.sleep(0.1)
        elif scroll_attempts % 4 == 1:
            # Scroll con rueda del mouse agresivo
            self.page.mouse.wheel(0, 2000)
        elif scroll_attempts % 4 == 2:
            # Scroll JavaScript al final
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        else:
            # Scroll JavaScript suave
            self.page.evaluate('window.scrollBy(0, 1500)')
    
    def _checkpoint_scroll(self, scroll_attempts, current_count):
        """Scroll de checkpoint para asegurar carga"""
        print(f"🔄 Scroll checkpoint {scroll_attempts}: {current_count} CEDEARS - forzando más carga...")
        for extra in range(5):
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            self.page.keyboard.press('End')
            time.sleep(0.5)
    
    def _final_aggressive_scroll(self, current_count):
        """Scroll agresivo final para los últimos elementos"""
        for extra_scroll in range(20):
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            self.page.keyboard.press('End')
            time.sleep(0.5)
            new_count = self.page.locator(SELECTORS['price_elements']).count()
            if new_count > current_count:
                current_count = new_count
                print(f"   📈 Scroll extra {extra_scroll + 1}: {current_count} CEDEARS")
            if new_count >= 950:
                break
    
    def _extract_cedears_data(self, final_count):
        """Extrae datos de todos los CEDEARs con precios de cierre"""
        print("🔍 Extrayendo precios actuales y expandiendo para obtener precios de cierre anterior...")
        
        final_elements = self.page.locator(SELECTORS['price_elements'])
        data = []
        
        for i in range(final_count):
            try:
                if i % 50 == 0:
                    print(f"\n--- Procesando CEDEAR {i+1}/{final_count} ---")
                
                cedear_data = self._process_single_cedear(final_elements.nth(i), i, final_count)
                if cedear_data:
                    data.append(cedear_data)
                    if i % 50 == 0:
                        print(f"📝 {cedear_data['cedear']} agregado al DataFrame")
                        
            except Exception as e:
                print(f"⚠️ Error procesando elemento {i}: {str(e)}")
                continue
        
        # Crear DataFrame
        if data:
            df = pd.DataFrame(data)
            print(f"\n📈 DataFrame CEDEARS creado exitosamente!")
            print(f"📊 Total procesados: {len(df)} CEDEARS")
            print(f"🎯 Objetivo esperado: 960 CEDEARS")
            print(f"Columnas: {list(df.columns)}")
            
            # Mostrar estado
            if len(df) >= 950:
                print("✅ ¡Excelente! Se cargaron prácticamente todos los CEDEARS")
            elif len(df) >= 800:
                print("⚠️ Se cargó la mayoría de CEDEARS, pero podrían faltar algunos")
            else:
                print("⚠️ Se cargaron menos CEDEARS de los esperados")
            
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
        
        if index % 50 == 0:
            print(f"✅ {ticker}: Precio actual ${precio_actual:,.2f}")
        
        # Obtener precio de cierre anterior
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
            if index % 50 == 0:
                print(f"⚠️ No se encontró botón de expansión para {ticker}")
            return None, "N/A"
        
        try:
            if index % 50 == 0:
                print(f"🖱️ Expandiendo información de {ticker}...")
            
            # Scroll hacia el elemento y click
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
                    if index % 50 == 0:
                        print(f"💰 Precio cierre encontrado: '{texto}'")
                    
                    precio_limpio = texto.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
                    try:
                        precio_cierre = float(precio_limpio)
                        precio_texto = texto
                        if index % 50 == 0:
                            print(f"✅ {ticker}: Cierre anterior ${precio_cierre:,.2f}")
                        break
                    except ValueError:
                        continue
            
            # Cerrar desplegable
            safe_click_with_retry(expand_button, sleep_time=0.2)
            
            return precio_cierre, precio_texto
            
        except Exception as e:
            if index % 50 == 0:
                print(f"⚠️ Error expandiendo {ticker}: {str(e)}")
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