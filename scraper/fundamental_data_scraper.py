# scraper/fundamental_data_scraper.py - Scraper para datos fundamentales reales
import time
from typing import Dict, Optional
import re

class FundamentalDataScraper:
    def __init__(self, page):
        self.page = page
    
    def scrape_asset_fundamentals(self, ticker: str) -> Dict:
        """Scrapea datos fundamentales reales del activo desde Balanz"""
        try:
            print(f"   📊 Scrapeando datos fundamentales de {ticker}...")
            
            # Construir URL del activo
            base_url = "https://clientes.balanz.com/app/detalleinstrumento"
            params = (
                f"?ticker={ticker}"
                f"&idPlazo=1"
                f"&eventoptfrom=mi-tenencia"
                f"&action_from=mis-instrumentos-cartera"
                f"&url=%2Fapp%2Fmi-cartera%3Fopeninstrument%3DAcciones%26action_from%3Dmis-instrumentos-home"
            )
            
            asset_url = base_url + params
            
            print(f"   🌐 Navegando a: {asset_url}")
            
            # Navegar a la página del activo
            self.page.goto(asset_url, wait_until='networkidle')
            time.sleep(3)
            
            # Extraer datos fundamentales
            fundamental_data = {}
            
            # 1. Extraer Industria y Sector
            sector_industry = self._extract_sector_industry()
            fundamental_data.update(sector_industry)
            
            # 2. Extraer Volumen diario
            daily_volume = self._extract_daily_volume()
            if daily_volume:
                fundamental_data['daily_volume'] = daily_volume
            
            # 3. Otros datos que puedan estar disponibles
            # Se pueden agregar más extractores aquí
            
            fundamental_data['data_source'] = 'balanz_scraping'
            fundamental_data['scraping_success'] = True
            
            print(f"   ✅ Datos fundamentales extraídos: {fundamental_data}")
            return fundamental_data
            
        except Exception as e:
            print(f"   ❌ Error scrapeando datos fundamentales de {ticker}: {str(e)}")
            return {
                'error': str(e),
                'data_source': 'balanz_scraping_failed',
                'scraping_success': False
            }
    
    def _extract_sector_industry(self) -> Dict:
        """Extrae sector e industria del HTML"""
        try:
            # Buscar el elemento que contiene industria y sector
            # <div class="d-flex">
            #   <span class="industries text-size-4">Industria: <span class="fw-semibold industris-category">Gas</span></span>
            #   <span class="industries text-size-4 ms-1">Sector: <span class="fw-semibold industris-category">Utilities</span></span>
            # </div>
            
            sector_industry_data = {}
            
            # Método 1: Buscar por clase específica
            try:
                industry_elements = self.page.locator('span.industries.text-size-4').all()
                
                for element in industry_elements:
                    text = element.text_content().strip()
                    
                    # Extraer Industria
                    if 'Industria:' in text:
                        # Buscar el span con clase fw-semibold dentro
                        industry_span = element.locator('span.fw-semibold.industris-category')
                        if industry_span.count() > 0:
                            industry = industry_span.text_content().strip()
                            sector_industry_data['industry'] = industry
                            print(f"      📊 Industria encontrada: {industry}")
                    
                    # Extraer Sector  
                    elif 'Sector:' in text:
                        # Buscar el span con clase fw-semibold dentro
                        sector_span = element.locator('span.fw-semibold.industris-category')
                        if sector_span.count() > 0:
                            sector = sector_span.text_content().strip()
                            sector_industry_data['sector'] = sector
                            print(f"      📊 Sector encontrado: {sector}")
                
            except Exception as e:
                print(f"      ⚠️ Error método 1 sector/industria: {str(e)}")
            
            # Método 2: Buscar por texto usando regex si método 1 falla
            if not sector_industry_data:
                try:
                    page_content = self.page.content()
                    
                    # Buscar Industria con regex
                    industry_match = re.search(r'Industria:\s*<[^>]*>([^<]+)</span>', page_content)
                    if industry_match:
                        industry = industry_match.group(1).strip()
                        sector_industry_data['industry'] = industry
                        print(f"      📊 Industria (regex): {industry}")
                    
                    # Buscar Sector con regex
                    sector_match = re.search(r'Sector:\s*<[^>]*>([^<]+)</span>', page_content)
                    if sector_match:
                        sector = sector_match.group(1).strip()
                        sector_industry_data['sector'] = sector  
                        print(f"      📊 Sector (regex): {sector}")
                        
                except Exception as e:
                    print(f"      ⚠️ Error método 2 sector/industria: {str(e)}")
            
            return sector_industry_data
            
        except Exception as e:
            print(f"      ❌ Error extrayendo sector/industria: {str(e)}")
            return {}
    
    def _extract_daily_volume(self) -> Optional[str]:
        """Extrae volumen diario del HTML"""
        try:
            # Buscar el elemento de volumen
            # <div class="d-flex justify-content-between border-bottom pb-2">
            #   <span> Volumen</span>
            #   <span class="fw-semibold"> 739.936.940 </span>
            # </div>
            
            # Método 1: Buscar por estructura específica
            try:
                # Buscar divs que contengan "Volumen"
                volume_containers = self.page.locator('div:has-text("Volumen")').all()
                
                for container in volume_containers:
                    container_text = container.text_content().strip()
                    
                    if 'Volumen' in container_text and 'justify-content-between' in container.get_attribute('class', ''):
                        # Buscar el span con fw-semibold que contiene el valor
                        volume_span = container.locator('span.fw-semibold')
                        if volume_span.count() > 0:
                            volume = volume_span.text_content().strip()
                            print(f"      📊 Volumen encontrado: {volume}")
                            return volume
                            
            except Exception as e:
                print(f"      ⚠️ Error método 1 volumen: {str(e)}")
            
            # Método 2: Buscar por texto "Volumen" y el siguiente span
            try:
                volume_elements = self.page.locator(':has-text("Volumen")').all()
                
                for element in volume_elements:
                    # Buscar spans fw-semibold dentro o cerca
                    parent = element.locator('..')
                    volume_spans = parent.locator('span.fw-semibold').all()
                    
                    for span in volume_spans:
                        volume_text = span.text_content().strip()
                        # Verificar que parezca un número de volumen (contiene dígitos y posibles puntos)
                        if re.match(r'^[\d\s\.]+$', volume_text.replace('.', '').replace(' ', '')):
                            print(f"      📊 Volumen (método 2): {volume_text}")
                            return volume_text
                            
            except Exception as e:
                print(f"      ⚠️ Error método 2 volumen: {str(e)}")
            
            # Método 3: Regex en contenido de página
            try:
                page_content = self.page.content()
                volume_match = re.search(r'Volumen</span>\s*<[^>]*class="[^"]*fw-semibold[^"]*"[^>]*>\s*([^<]+)\s*</span>', page_content)
                if volume_match:
                    volume = volume_match.group(1).strip()
                    print(f"      📊 Volumen (regex): {volume}")
                    return volume
                    
            except Exception as e:
                print(f"      ⚠️ Error método 3 volumen: {str(e)}")
            
            print(f"      ⚠️ No se pudo extraer volumen")
            return None
            
        except Exception as e:
            print(f"      ❌ Error extrayendo volumen: {str(e)}")
            return None
    
    def _extract_additional_metrics(self) -> Dict:
        """Extrae métricas adicionales si están disponibles"""
        try:
            additional_data = {}
            
            # Aquí se pueden agregar más extractores para:
            # - Capitalización de mercado
            # - P/E ratio  
            # - Dividend yield
            # - Cualquier otro dato disponible en la página
            
            return additional_data
            
        except Exception as e:
            print(f"      ❌ Error extrayendo métricas adicionales: {str(e)}")
            return {}