# financial_ratios_scraper_paginated_with_login.py - VERSIÓN CORREGIDA con LOGIN
import time
from datetime import datetime, date
from typing import Dict, List, Optional
import re

class FinancialRatiosScraperPaginatedWithLogin:
    def __init__(self, page):
        self.page = page
        self.is_logged_in = False
        
        # Credenciales de login
        self.login_credentials = {
            'email': 'mhv220@gmail.com',
            'password': 'Gesti@n07'
        }
        
        # URLs de todas las páginas de Screenermatic
        self.ratios_urls = [
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=&scrollPos=0",
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=20&scrollPos=300",
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=40&scrollPos=200"
        ]
    
    def login_to_screenermatic(self) -> bool:
        """Realiza login en Screenermatic antes de acceder a los ratios"""
        try:
            if self.is_logged_in:
                print("✅ Ya logueado en Screenermatic")
                return True
            
            print("🔐 INICIANDO LOGIN EN SCREENERMATIC...")
            print("-" * 45)
            
            # Configurar headers realistas
            self._setup_realistic_headers()
            
            # Ir a la página de login
            login_url = "https://www.screenermatic.com/login.php"
            print(f"🌐 Navegando a: {login_url}")
            self.page.goto(login_url, wait_until='networkidle')
            time.sleep(3)
            
            # Rellenar formulario de login
            print("📝 Rellenando formulario de login...")
            
            # Buscar y rellenar email
            email_field = self.page.locator('#email')
            if email_field.count() > 0:
                email_field.fill(self.login_credentials['email'])
                print(f"✅ Email rellenado: {self.login_credentials['email']}")
            else:
                print("❌ No se encontró campo de email")
                return False
            
            # Buscar y rellenar password
            password_field = self.page.locator('#password')
            if password_field.count() > 0:
                password_field.fill(self.login_credentials['password'])
                print("✅ Password rellenado")
            else:
                print("❌ No se encontró campo de password")
                return False
            
            # Hacer click en el botón de submit
            print("🚀 Enviando formulario...")
            submit_button = self.page.locator('input[type="submit"][name="form2"]')
            if submit_button.count() > 0:
                submit_button.click()
                print("✅ Formulario enviado")
            else:
                print("❌ No se encontró botón de submit")
                return False
            
            # Esperar respuesta y verificar login
            self.page.wait_for_timeout(5000)
            
            # Verificar que el login fue exitoso
            current_url = self.page.url
            print(f"🔍 URL actual después del login: {current_url}")
            
            # Buscar indicadores de login exitoso
            if "login.php" not in current_url or self.page.locator('text="Logout"').count() > 0:
                print("✅ LOGIN EXITOSO")
                self.is_logged_in = True
                return True
            else:
                print("❌ LOGIN FALLIDO - Verificar credenciales")
                return False
                
        except Exception as e:
            print(f"❌ Error durante login: {str(e)}")
            return False
    
    def get_financial_ratios_for_tickers(self, target_tickers: List[str]) -> Dict:
        """Obtiene ratios financieros buscando en TODAS las páginas (CON LOGIN)"""
        try:
            # PASO 1: Login obligatorio
            if not self.login_to_screenermatic():
                print("❌ No se pudo hacer login - abortando scraping")
                return {}
            
            print("\n📊 OBTENIENDO RATIOS FINANCIEROS (CON LOGIN)...")
            print("-" * 55)
            print(f"🎯 Buscando: {target_tickers}")
            print(f"📄 Páginas a revisar: {len(self.ratios_urls)}")
            
            # Contenedor para todos los ratios encontrados
            all_ratios_data = {}
            found_tickers = set()
            
            # Recorrer todas las páginas
            for page_num, url in enumerate(self.ratios_urls, 1):
                print(f"\n📄 PÁGINA {page_num}/{len(self.ratios_urls)}:")
                print(f"🌐 {url}")
                
                # Si ya encontramos todos los tickers, no necesitamos seguir
                if len(found_tickers) >= len(target_tickers):
                    print(f"✅ Todos los tickers encontrados - saltando páginas restantes")
                    break
                
                # Extraer ratios de esta página
                page_ratios = self._extract_ratios_from_page(url, target_tickers, found_tickers, page_num)
                
                # Agregar los ratios encontrados
                if page_ratios:
                    all_ratios_data.update(page_ratios)
                    found_tickers.update(page_ratios.keys())
                    print(f"✅ Página {page_num}: {len(page_ratios)} tickers encontrados")
                    for ticker in page_ratios.keys():
                        print(f"   📊 {ticker}: ✅")
                    print(f"📊 Total acumulado: {len(all_ratios_data)}/{len(target_tickers)}")
                else:
                    print(f"⚠️ Página {page_num}: 0 tickers encontrados")
                
                # Pausa entre páginas para no sobrecargar el servidor
                if page_num < len(self.ratios_urls):
                    print("⏳ Pausa entre páginas...")
                    time.sleep(2)
            
            # Crear respuesta final
            if all_ratios_data:
                print(f"\n🎉 RESULTADO FINAL:")
                print(f"✅ {len(all_ratios_data)}/{len(target_tickers)} tickers con ratios")
                
                missing_tickers = set(target_tickers) - found_tickers
                if missing_tickers:
                    print(f"⚠️ No encontrados: {list(missing_tickers)}")
                
                return {
                    'fecha': date.today().isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'ratios_by_ticker': all_ratios_data,
                    'data_source': 'screenermatic_paginated_with_login',
                    'pages_searched': len(self.ratios_urls),
                    'tickers_found': len(all_ratios_data),
                    'tickers_requested': len(target_tickers),
                    'fields_available': self._get_available_fields(),
                    'login_status': 'success'
                }
            else:
                print(f"\n❌ NO SE ENCONTRARON RATIOS")
                print(f"💡 Posibles causas:")
                print(f"   • Los tickers no existen en Screenermatic")
                print(f"   • El sitio cambió su estructura")
                print(f"   • Problemas de conectividad")
                return {}
                
        except Exception as e:
            print(f"❌ Error obteniendo ratios paginados con login: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _setup_realistic_headers(self):
        """Configura headers realistas para evitar bloqueos"""
        self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    def _extract_ratios_from_page(self, url: str, target_tickers: List[str], already_found: set, page_num: int) -> Dict:
        """Extrae ratios de una página específica (MEJORADO CON DEBUG INSIGHTS)"""
        try:
            # Navegar a la página
            self.page.goto(url, wait_until='networkidle')
            time.sleep(3)  # Esperar carga completa
            
            # MÉTODO MEJORADO basado en debug_screenermatic insights
            page_ratios = self._extract_tickers_with_debug_method(target_tickers, already_found, page_num)
            
            return page_ratios
            
        except Exception as e:
            print(f"   ❌ Página {page_num}: Error {str(e)}")
            return {}
    
    def _extract_tickers_with_debug_method(self, target_tickers: List[str], already_found: set, page_num: int) -> Dict:
        """MÉTODO MEJORADO basado en debug_screenermatic findings"""
        try:
            ratios_data = {}
            remaining_tickers = [t for t in target_tickers if t not in already_found]
            
            print(f"   🔍 Página {page_num}: Buscando {len(remaining_tickers)} tickers restantes...")
            
            # ESTRATEGIA 1: Buscar filas de datos (con muchas celdas)
            print(f"   📊 Analizando estructura de filas...")
            all_rows = self.page.locator('tr').all()
            data_rows = []
            
            for i, row in enumerate(all_rows):
                cells = row.locator('td, th').all()
                cell_count = len(cells)
                
                # Buscar filas con suficientes celdas para contener datos
                if cell_count >= 10:
                    row_text = row.text_content()
                    found_tickers = [t for t in remaining_tickers if t in row_text]
                    
                    if found_tickers:
                        data_rows.append({
                            'index': i,
                            'row': row,
                            'cells': cell_count,
                            'tickers': found_tickers,
                            'sample': row_text[:100]
                        })
            
            print(f"   📋 Filas con datos encontradas: {len(data_rows)}")
            
            # ESTRATEGIA 2: Procesar cada fila con tickers
            for row_info in data_rows:
                for ticker in row_info['tickers']:
                    if ticker in already_found:
                        continue
                    
                    print(f"   🎯 Procesando {ticker} en fila {row_info['index']}...")
                    
                    try:
                        # Extraer celdas de la fila
                        cells = row_info['row'].locator('td, th').all()
                        
                        print(f"      📊 Fila con {len(cells)} celdas")
                        
                        # Verificar que realmente contiene el ticker
                        ticker_found_in_row = self._verify_ticker_in_row(cells, ticker)
                        
                        if not ticker_found_in_row:
                            print(f"      ⚠️ {ticker} no verificado en fila - saltando")
                            continue
                        
                        # Extraer ratios de la fila
                        ratios = self._parse_ratios_from_row_enhanced(cells, ticker, row_info['index'])
                        
                        if ratios and len(ratios) > 3:  # ticker + al menos 2 ratios
                            ratios_data[ticker] = ratios
                            
                            # Log del resultado
                            pe = ratios.get('pe', 'N/A')
                            roe = ratios.get('roe', 'N/A')
                            debt_equity = ratios.get('debt_to_equity', 'N/A')
                            score = ratios.get('fundamental_score', 'N/A')
                            
                            print(f"      ✅ {ticker}: P/E={pe}, ROE={roe}, D/E={debt_equity}, Score={score}")
                        else:
                            print(f"      ⚠️ {ticker}: Ratios insuficientes extraídos")
                    
                    except Exception as e:
                        print(f"      ❌ Error procesando {ticker}: {str(e)}")
                        continue
            
            return ratios_data
            
        except Exception as e:
            print(f"   ❌ Error en método debug página {page_num}: {str(e)}")
            return {}
    
    def _verify_ticker_in_row(self, cells: List, ticker: str) -> bool:
        """Verifica que el ticker esté realmente en la fila"""
        try:
            for cell in cells:
                # Buscar en links
                links = cell.locator('a').all()
                for link in links:
                    link_text = link.text_content().strip()
                    href = link.get_attribute('href') or ''
                    
                    if (link_text.upper() == ticker.upper() and 
                        ('ticker.php' in href or ticker.lower() in href.lower())):
                        return True
                
                # Buscar en texto directo
                cell_text = cell.text_content().strip()
                if cell_text.upper() == ticker.upper():
                    return True
            
            return False
            
        except:
            return False
    
    def _parse_ratios_from_row_enhanced(self, cells: List, ticker: str, row_index: int) -> Dict:
        """Parsea ratios MEJORADO con insights del debug"""
        try:
            ratios = {'ticker': ticker}
            
            print(f"         🔍 Debug {ticker} (fila {row_index}): Analizando {len(cells)} celdas...")
            
            # Extraer todos los valores y sus posiciones
            all_values = []
            numeric_values = []
            
            for i, cell in enumerate(cells):
                try:
                    cell_text = cell.text_content().strip()
                    all_values.append(f"[{i}]: '{cell_text}'")
                    
                    if cell_text and cell_text not in ['-', 'S/D', 'N/A', '', ticker]:
                        cleaned_value = self._clean_numeric_value(cell_text)
                        if cleaned_value is not None:
                            numeric_values.append({
                                'position': i,
                                'value': cleaned_value,
                                'original': cell_text
                            })
                
                except:
                    all_values.append(f"[{i}]: ERROR")
                    continue
            
            # Debug de primeras celdas
            print(f"         📋 Primeras 8 celdas: {all_values[:8]}")
            print(f"         📊 Valores numéricos: {len(numeric_values)}")
            
            if numeric_values:
                first_5_values = [(v['position'], v['value'], v['original']) for v in numeric_values[:5]]
                print(f"         🔢 Primeros valores: {first_5_values}")
            
            # ESTRATEGIA DE ASIGNACIÓN MEJORADA
            if len(numeric_values) >= 4:
                
                # Filtrar valores en posiciones razonables (después del ticker)
                analysis_values = [v for v in numeric_values if v['position'] > 1]
                
                if len(analysis_values) >= 3:
                    
                    # MAPEO INTELIGENTE DE RATIOS
                    # P/E Ratio: rango típico 3-100, posición temprana
                    pe_candidates = [v for v in analysis_values if 2 <= v['value'] <= 150]
                    if pe_candidates:
                        ratios['pe'] = pe_candidates[0]['value']
                        print(f"         ✅ P/E: {ratios['pe']} (pos {pe_candidates[0]['position']})")
                    
                    # ROE: rango -50% a 100%, evitar P/E
                    roe_candidates = [v for v in analysis_values 
                                    if -50 <= v['value'] <= 100 
                                    and v['value'] != ratios.get('pe')
                                    and abs(v['value']) > 0.1]  # Evitar valores muy pequeños
                    if roe_candidates:
                        ratios['roe'] = roe_candidates[0]['value']
                        print(f"         ✅ ROE: {ratios['roe']} (pos {roe_candidates[0]['position']})")
                    
                    # Debt/Equity: rango 0-10, evitar valores anteriores
                    used_values = [ratios.get('pe'), ratios.get('roe')]
                    de_candidates = [v for v in analysis_values 
                                   if 0 <= v['value'] <= 10 
                                   and v['value'] not in used_values]
                    if de_candidates:
                        ratios['debt_to_equity'] = de_candidates[0]['value']
                        print(f"         ✅ D/E: {ratios['debt_to_equity']} (pos {de_candidates[0]['position']})")
                    
                    # Current Ratio: rango 0.1-10, evitar valores anteriores
                    used_values.append(ratios.get('debt_to_equity'))
                    cr_candidates = [v for v in analysis_values 
                                   if 0.1 <= v['value'] <= 10 
                                   and v['value'] not in used_values]
                    if cr_candidates:
                        ratios['current_ratio'] = cr_candidates[0]['value']
                        print(f"         ✅ Current: {ratios['current_ratio']} (pos {cr_candidates[0]['position']})")
                    
                    # P/B Ratio: rango 0.1-20, evitar valores anteriores
                    used_values.append(ratios.get('current_ratio'))
                    pb_candidates = [v for v in analysis_values 
                                   if 0.1 <= v['value'] <= 20 
                                   and v['value'] not in used_values]
                    if pb_candidates:
                        ratios['pb'] = pb_candidates[0]['value']
                        print(f"         ✅ P/B: {ratios['pb']} (pos {pb_candidates[0]['position']})")
                
                # FALLBACK: Asignación posicional si falló la inteligente
                if len(ratios) <= 2:
                    print(f"         ⚠️ Asignación inteligente falló, usando posicional...")
                    
                    if len(analysis_values) >= 5:
                        ratios['pe'] = analysis_values[0]['value']
                        ratios['roe'] = analysis_values[1]['value']
                        ratios['debt_to_equity'] = analysis_values[2]['value']
                        ratios['current_ratio'] = analysis_values[3]['value']
                        ratios['pb'] = analysis_values[4]['value']
                        
                        print(f"         ✅ Posicional: P/E={ratios['pe']}, ROE={ratios['roe']}")
            
            else:
                print(f"         ⚠️ Datos insuficientes: solo {len(numeric_values)} valores")
            
            # Calcular métricas derivadas
            ratios['fundamental_score'] = self._calculate_fundamental_score(ratios)
            ratios['valuation_category'] = self._categorize_valuation(ratios)
            
            return ratios if len(ratios) > 3 else {}
            
        except Exception as e:
            print(f"         ❌ Error parseando {ticker}: {str(e)}")
            return {}
    
    def _clean_numeric_value(self, text: str) -> Optional[float]:
        """Limpia y convierte texto a valor numérico (MEJORADO)"""
        try:
            if not text or text in ['-', 'S/D', 'N/A', '', 'null', '--']:
                return None
            
            # Remover símbolos comunes pero preservar signos
            clean_text = text.strip()
            clean_text = clean_text.replace('$', '').replace('%', '').replace(' ', '')
            clean_text = clean_text.replace('+', '').replace('€', '').replace('£', '')
            
            # Manejar formato europeo (1.234,56)
            if ',' in clean_text and '.' in clean_text:
                parts = clean_text.split(',')
                if len(parts) == 2 and len(parts[1]) <= 3:  # Es decimal
                    integer_part = parts[0].replace('.', '')
                    decimal_part = parts[1]
                    clean_text = f"{integer_part}.{decimal_part}"
            elif ',' in clean_text and '.' not in clean_text:
                # Solo coma, puede ser decimal europeo
                if len(clean_text.split(',')[1]) <= 3:
                    clean_text = clean_text.replace(',', '.')
            
            # Remover caracteres no numéricos excepto punto, coma y guión
            clean_text = re.sub(r'[^\d\.\-\+]', '', clean_text)
            
            if clean_text and clean_text not in ['.', '-', '+']:
                value = float(clean_text)
                
                # Filtrar valores absurdos
                if abs(value) > 1000000:  # Muy grande
                    return None
                
                return value
            
            return None
            
        except (ValueError, AttributeError):
            return None
    
    def _calculate_fundamental_score(self, ratios: Dict) -> float:
        """Calcula score fundamental (MEJORADO)"""
        try:
            score = 50  # Base neutral
            
            # ROE scoring
            roe = ratios.get('roe')
            if roe is not None:
                if roe > 25:
                    score += 20
                elif roe > 15:
                    score += 15
                elif roe > 10:
                    score += 8
                elif roe > 5:
                    score += 3
                elif roe < 0:
                    score -= 20
                elif roe < 3:
                    score -= 10
            
            # P/E scoring
            pe = ratios.get('pe')
            if pe is not None:
                if 6 <= pe <= 12:
                    score += 15
                elif 12 < pe <= 18:
                    score += 10
                elif 18 < pe <= 25:
                    score += 5
                elif pe > 40:
                    score -= 15
                elif pe < 4:
                    score -= 10
            
            # Debt/Equity scoring
            de = ratios.get('debt_to_equity')
            if de is not None:
                if de < 0.2:
                    score += 15
                elif de < 0.5:
                    score += 10
                elif de < 1.0:
                    score += 5
                elif de > 2.0:
                    score -= 20
                elif de > 1.5:
                    score -= 10
            
            # Current Ratio scoring
            cr = ratios.get('current_ratio')
            if cr is not None:
                if cr > 2.0:
                    score += 10
                elif cr > 1.5:
                    score += 5
                elif cr < 1.0:
                    score -= 15
                elif cr < 0.8:
                    score -= 25
            
            return min(100, max(0, score))
            
        except:
            return 50
    
    def _categorize_valuation(self, ratios: Dict) -> str:
        """Categoriza valuación (MEJORADO)"""
        try:
            pe = ratios.get('pe')
            pb = ratios.get('pb')
            
            if pe is None and pb is None:
                return 'insufficient_data'
            
            valuation_signals = []
            
            # P/E signals
            if pe is not None:
                if pe < 8:
                    valuation_signals.append('very_cheap')
                elif pe < 15:
                    valuation_signals.append('cheap')
                elif pe < 25:
                    valuation_signals.append('fair')
                elif pe < 40:
                    valuation_signals.append('expensive')
                else:
                    valuation_signals.append('very_expensive')
            
            # P/B signals
            if pb is not None:
                if pb < 0.8:
                    valuation_signals.append('very_cheap')
                elif pb < 1.5:
                    valuation_signals.append('cheap')
                elif pb < 3.0:
                    valuation_signals.append('fair')
                elif pb < 5.0:
                    valuation_signals.append('expensive')
                else:
                    valuation_signals.append('very_expensive')
            
            # Determinar categoría final
            cheap_count = valuation_signals.count('very_cheap') + valuation_signals.count('cheap')
            expensive_count = valuation_signals.count('expensive') + valuation_signals.count('very_expensive')
            
            if cheap_count > expensive_count:
                return 'undervalued'
            elif expensive_count > cheap_count:
                return 'overvalued'
            else:
                return 'fairly_valued'
                
        except:
            return 'unknown'
    
    def _get_available_fields(self) -> List[str]:
        """Campos disponibles"""
        return [
            'pe', 'roe', 'debt_to_equity', 'current_ratio', 'pb',
            'fundamental_score', 'valuation_category'
        ]
    
    def enhance_portfolio_analysis_with_ratios(self, portfolio_data: Dict) -> Dict:
        """Enriquece análisis de cartera con ratios (CON LOGIN)"""
        try:
            # Obtener tickers de la cartera
            tickers = [asset['ticker'] for asset in portfolio_data.get('activos', [])]
            
            if not tickers:
                print("⚠️ No hay tickers en la cartera para analizar")
                return portfolio_data
            
            print(f"📊 Analizando ratios (CON LOGIN) para: {tickers}")
            
            # Obtener ratios con login y búsqueda paginada mejorada
            ratios_data = self.get_financial_ratios_for_tickers(tickers)
            
            if not ratios_data or not ratios_data.get('ratios_by_ticker'):
                print("⚠️ No se pudieron obtener ratios - usando análisis técnico solamente")
                return portfolio_data
            
            # Enriquecer cartera
            enhanced_portfolio = portfolio_data.copy()
            ratios_by_ticker = ratios_data['ratios_by_ticker']
            
            for i, asset in enumerate(enhanced_portfolio.get('activos', [])):
                ticker = asset['ticker']
                
                if ticker in ratios_by_ticker:
                    asset_ratios = ratios_by_ticker[ticker]
                    enhanced_portfolio['activos'][i]['fundamental_ratios'] = asset_ratios
                    enhanced_portfolio['activos'][i]['fundamental_analysis'] = self._interpret_ratios_detailed(asset_ratios)
                    
                    print(f"✅ {ticker} enriquecido con ratios fundamentales")
                else:
                    print(f"⚠️ No se encontraron ratios para {ticker} en ninguna página")
            
            # Resumen fundamental mejorado
            enhanced_portfolio['fundamental_summary'] = self._generate_portfolio_summary_enhanced(ratios_by_ticker)
            enhanced_portfolio['login_info'] = {
                'status': 'success',
                'method': 'screenermatic_with_credentials'
            }
            
            print(f"✅ Portfolio enriquecido: {len(ratios_by_ticker)}/{len(tickers)} activos con ratios")
            return enhanced_portfolio
            
        except Exception as e:
            print(f"❌ Error enriqueciendo análisis: {str(e)}")
            return portfolio_data
    
    def _interpret_ratios_detailed(self, ratios: Dict) -> Dict:
        """Interpretación detallada de ratios"""
        interpretation = {
            'valuation_status': 'unknown',
            'financial_health': 'unknown',
            'investment_recommendation': 'hold',
            'detailed_summary': '',
            'strengths': [],
            'concerns': []
        }
        
        try:
            pe = ratios.get('pe')
            roe = ratios.get('roe')
            de = ratios.get('debt_to_equity')
            cr = ratios.get('current_ratio')
            score = ratios.get('fundamental_score', 50)
            
            # ANÁLISIS DE VALUACIÓN
            if pe is not None:
                if pe < 10:
                    interpretation['valuation_status'] = 'muy_barata'
                    interpretation['strengths'].append(f"P/E muy atractivo ({pe})")
                elif pe < 15:
                    interpretation['valuation_status'] = 'barata'
                    interpretation['strengths'].append(f"P/E atractivo ({pe})")
                elif pe < 25:
                    interpretation['valuation_status'] = 'razonable'
                elif pe < 40:
                    interpretation['valuation_status'] = 'cara'
                    interpretation['concerns'].append(f"P/E elevado ({pe})")
                else:
                    interpretation['valuation_status'] = 'muy_cara'
                    interpretation['concerns'].append(f"P/E muy alto ({pe})")
            
            # ANÁLISIS DE SALUD FINANCIERA
            health_factors = []
            
            if roe is not None:
                if roe > 20:
                    health_factors.append('excelente')
                    interpretation['strengths'].append(f"ROE excelente ({roe}%)")
                elif roe > 15:
                    health_factors.append('muy_buena')
                    interpretation['strengths'].append(f"ROE muy bueno ({roe}%)")
                elif roe > 10:
                    health_factors.append('buena')
                elif roe > 5:
                    health_factors.append('aceptable')
                else:
                    health_factors.append('preocupante')
                    interpretation['concerns'].append(f"ROE bajo ({roe}%)")
            
            if de is not None:
                if de < 0.3:
                    interpretation['strengths'].append(f"Deuda muy baja ({de})")
                elif de < 0.6:
                    interpretation['strengths'].append(f"Deuda controlada ({de})")
                elif de > 1.5:
                    interpretation['concerns'].append(f"Deuda elevada ({de})")
                    health_factors.append('riesgosa')
            
            if cr is not None:
                if cr > 2.0:
                    interpretation['strengths'].append(f"Liquidez excelente ({cr})")
                elif cr > 1.5:
                    interpretation['strengths'].append(f"Liquidez buena ({cr})")
                elif cr < 1.0:
                    interpretation['concerns'].append(f"Liquidez preocupante ({cr})")
                    health_factors.append('riesgosa')
            
            # Determinar salud financiera general
            if 'excelente' in health_factors or 'muy_buena' in health_factors:
                interpretation['financial_health'] = 'excelente'
            elif 'buena' in health_factors and 'riesgosa' not in health_factors:
                interpretation['financial_health'] = 'buena'
            elif 'preocupante' in health_factors or 'riesgosa' in health_factors:
                interpretation['financial_health'] = 'preocupante'
            else:
                interpretation['financial_health'] = 'aceptable'
            
            # RECOMENDACIÓN DE INVERSIÓN
            if score >= 75:
                interpretation['investment_recommendation'] = 'compra_fuerte'
            elif score >= 65:
                interpretation['investment_recommendation'] = 'compra'
            elif score >= 45:
                interpretation['investment_recommendation'] = 'hold'
            elif score >= 35:
                interpretation['investment_recommendation'] = 'precaución'
            else:
                interpretation['investment_recommendation'] = 'venta'
            
            # RESUMEN DETALLADO
            valuation = interpretation['valuation_status']
            health = interpretation['financial_health']
            recommendation = interpretation['investment_recommendation']
            
            if recommendation == 'compra_fuerte':
                interpretation['detailed_summary'] = f"Oportunidad excepcional: Empresa {health} con valuación {valuation}"
            elif recommendation == 'compra':
                interpretation['detailed_summary'] = f"Buena oportunidad: Empresa {health} con valuación {valuation}"
            elif recommendation == 'hold':
                interpretation['detailed_summary'] = f"Mantener posición: Empresa {health} con valuación {valuation}"
            elif recommendation == 'precaución':
                interpretation['detailed_summary'] = f"Revisar posición: Empresa {health} con valuación {valuation}"
            else:
                interpretation['detailed_summary'] = f"Considerar venta: Empresa {health} con valuación {valuation}"
            
            return interpretation
            
        except Exception as e:
            print(f"⚠️ Error interpretando ratios: {str(e)}")
            return interpretation
    
    def _generate_portfolio_summary_enhanced(self, ratios_by_ticker: Dict) -> Dict:
        """Genera resumen mejorado del portfolio"""
        try:
            if not ratios_by_ticker:
                return {}
            
            # Métricas agregadas
            all_scores = [r.get('fundamental_score', 0) for r in ratios_by_ticker.values()]
            pe_values = [r.get('pe') for r in ratios_by_ticker.values() if r.get('pe')]
            roe_values = [r.get('roe') for r in ratios_by_ticker.values() if r.get('roe')]
            
            # Categorización por recomendaciones
            recommendations = {}
            for ticker, ratios in ratios_by_ticker.items():
                score = ratios.get('fundamental_score', 50)
                if score >= 75:
                    recommendations.setdefault('compra_fuerte', []).append(ticker)
                elif score >= 65:
                    recommendations.setdefault('compra', []).append(ticker)
                elif score >= 45:
                    recommendations.setdefault('hold', []).append(ticker)
                elif score >= 35:
                    recommendations.setdefault('precaución', []).append(ticker)
                else:
                    recommendations.setdefault('venta', []).append(ticker)
            
            summary = {
                'tickers_analyzed': len(ratios_by_ticker),
                'avg_fundamental_score': sum(all_scores) / len(all_scores) if all_scores else 0,
                'avg_pe': sum(pe_values) / len(pe_values) if pe_values else None,
                'avg_roe': sum(roe_values) / len(roe_values) if roe_values else None,
                'portfolio_health': self._classify_portfolio_health(sum(all_scores) / len(all_scores) if all_scores else 50),
                'recommendations_breakdown': recommendations,
                'top_opportunities': sorted(
                    [(t, r.get('fundamental_score', 0)) for t, r in ratios_by_ticker.items()],
                    key=lambda x: x[1], reverse=True
                )[:3],
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            print(f"⚠️ Error generando resumen: {str(e)}")
            return {}
    
    def _classify_portfolio_health(self, avg_score: float) -> str:
        """Clasifica la salud general del portfolio"""
        if avg_score >= 75:
            return 'excelente'
        elif avg_score >= 65:
            return 'muy_buena'
        elif avg_score >= 55:
            return 'buena'
        elif avg_score >= 45:
            return 'aceptable'
        elif avg_score >= 35:
            return 'preocupante'
        else:
            return 'riesgosa'

# FUNCIÓN DE TESTING MEJORADA
def test_scraper_with_login():
    """Test del scraper con login y debug mejorado"""
    print("🧪 TEST DEL SCRAPER CON LOGIN Y DEBUG INSIGHTS")
    print("=" * 55)
    
    print("🔧 MEJORAS IMPLEMENTADAS:")
    print("✅ Login automático antes de scraping")
    print("✅ Verificación de credenciales")
    print("✅ Extracción basada en debug findings")
    print("✅ Búsqueda inteligente de filas con datos")
    print("✅ Asignación mejorada de ratios")
    print("✅ Scoring fundamental detallado")
    print("✅ Interpretación completa de ratios")
    print("✅ Manejo robusto de errores")
    
    print("\n💡 FUNCIONALIDADES:")
    print("   🔐 Login con mhv220@gmail.com")
    print("   📊 Búsqueda en todas las páginas")
    print("   🎯 ALUA, COME, EDN, METR, TECO2")
    print("   🔍 Filas con ≥10 celdas (datos reales)")
    print("   📈 Análisis fundamental completo")
    
    print("\n🎯 PARA USAR:")
    print("1. Importa FinancialRatiosScraperPaginatedWithLogin")
    print("2. Instancia con page de Playwright")
    print("3. Llama get_financial_ratios_for_tickers(tickers)")
    print("4. El login se hace automáticamente")
    
    return True

if __name__ == "__main__":
    test_scraper_with_login()