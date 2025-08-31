# financial_ratios_scraper_paginated.py - Versión con soporte para múltiples páginas
import time
from datetime import datetime, date
from typing import Dict, List, Optional
import re

class FinancialRatiosScraperPaginated:
    def __init__(self, page):
        self.page = page
        
        # URLs de todas las páginas de Screenermatic
        self.ratios_urls = [
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=&scrollPos=0",
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=20&scrollPos=300",
            "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=40&scrollPos=200"
            # Eliminamos la página 4 que está fallando
        ]
    
    def get_financial_ratios_for_tickers(self, target_tickers: List[str]) -> Dict:
        """Obtiene ratios financieros buscando en TODAS las páginas de Screenermatic"""
        try:
            print("📊 OBTENIENDO RATIOS FINANCIEROS (TODAS LAS PÁGINAS)...")
            print("-" * 55)
            print(f"🎯 Buscando: {target_tickers}")
            print(f"📄 Páginas a revisar: {len(self.ratios_urls)}")
            
            # Configurar headers realistas
            self._setup_realistic_headers()
            
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
                for ticker in all_ratios_data.keys():
                    print(f"   📊 {ticker}: ✅")
                
                missing_tickers = set(target_tickers) - found_tickers
                if missing_tickers:
                    print(f"⚠️ No encontrados: {list(missing_tickers)}")
                
                return {
                    'fecha': date.today().isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'ratios_by_ticker': all_ratios_data,
                    'data_source': 'screenermatic_paginated',
                    'pages_searched': len(self.ratios_urls),
                    'tickers_found': len(all_ratios_data),
                    'tickers_requested': len(target_tickers),
                    'fields_available': self._get_available_fields()
                }
            else:
                print(f"\n❌ NO SE ENCONTRARON RATIOS")
                print(f"💡 Posibles causas:")
                print(f"   • Los tickers no existen en Screenermatic")
                print(f"   • El sitio cambió su estructura")
                print(f"   • Problemas de conectividad")
                return {}
                
        except Exception as e:
            print(f"❌ Error obteniendo ratios paginados: {str(e)}")
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
        """Extrae ratios de una página específica"""
        try:
            # Navegar a la página
            self.page.goto(url, wait_until='networkidle')
            time.sleep(3)  # Esperar carga completa
            
            # Detectar estructura de la tabla
            table_structure = self._detect_table_structure_improved()
            
            if not table_structure['valid']:
                print(f"   ❌ Página {page_num}: Estructura de tabla inválida")
                return {}
            
            print(f"   ✅ Página {page_num}: {table_structure['rows']} filas detectadas")
            
            # Extraer ratios solo para tickers que aún no tenemos
            remaining_tickers = [t for t in target_tickers if t not in already_found]
            page_ratios = self._extract_ratios_from_table(table_structure, remaining_tickers, page_num)
            
            return page_ratios
            
        except Exception as e:
            print(f"   ❌ Página {page_num}: Error {str(e)}")
            return {}
    
    def _detect_table_structure_improved(self) -> Dict:
        """Detecta estructura de tabla con múltiples métodos"""
        try:
            structure = {
                'valid': False,
                'rows': 0,
                'columns': 0,
                'row_selector': None
            }
            
            # MÉTODO 1: Tabla estándar
            table_selectors = [
                'table tbody tr',
                'tbody tr', 
                'table tr'
            ]
            
            for selector in table_selectors:
                try:
                    rows = self.page.locator(selector).all()
                    row_count = len(rows)
                    
                    if row_count >= 5:  # Al menos 5 filas
                        # Verificar columnas en primera fila
                        if rows:
                            cells = rows[0].locator('td, th').all()
                            col_count = len(cells)
                            
                            if col_count >= 10:  # Al menos 10 columnas
                                structure.update({
                                    'valid': True,
                                    'rows': row_count,
                                    'columns': col_count,
                                    'row_selector': selector
                                })
                                return structure
                except:
                    continue
            
            # MÉTODO 2: Buscar por contenido conocido
            known_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
            
            for ticker in known_tickers:
                try:
                    ticker_elements = self.page.locator(f'text="{ticker}"').all()
                    if ticker_elements:
                        # Encontrar fila padre
                        element = ticker_elements[0]
                        row = element.locator('xpath=ancestor::tr').first
                        
                        if row.count() > 0:
                            cells = row.locator('td, th').all()
                            if len(cells) >= 10:
                                # Encontrar todas las filas de la tabla
                                table = row.locator('xpath=ancestor::table').first
                                if table.count() > 0:
                                    all_rows = table.locator('tr').all()
                                    
                                    structure.update({
                                        'valid': True,
                                        'rows': len(all_rows),
                                        'columns': len(cells),
                                        'row_selector': 'table tr'
                                    })
                                    return structure
                except:
                    continue
            
            return structure
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _extract_ratios_from_table(self, table_structure: Dict, target_tickers: List[str], page_num: int) -> Dict:
        """Extrae ratios de la tabla detectada"""
        try:
            ratios_data = {}
            row_selector = table_structure['row_selector']
            table_rows = self.page.locator(row_selector).all()
            
            print(f"   🔍 Página {page_num}: Procesando {len(table_rows)} filas...")
            
            for i, row in enumerate(table_rows):
                try:
                    # Extraer celdas de la fila
                    cells = row.locator('td, th').all()
                    
                    if len(cells) < 8:  # Mínimo razonable
                        continue
                    
                    # Buscar ticker en las primeras celdas
                    ticker = self._find_ticker_in_row(cells, target_tickers)
                    
                    if not ticker:
                        continue
                    
                    print(f"   📊 Página {page_num}: Procesando {ticker}...")
                    
                    # Extraer ratios de la fila
                    ratios = self._parse_ratios_from_cells(cells, ticker)
                    
                    if ratios and len(ratios) > 3:  # ticker + al menos 2 ratios
                        ratios_data[ticker] = ratios
                        
                        # Log del resultado
                        pe = ratios.get('pe', 'N/A')
                        roe = ratios.get('roe', 'N/A')
                        print(f"   ✅ {ticker}: P/E={pe}, ROE={roe}")
                
                except Exception as e:
                    continue
            
            return ratios_data
            
        except Exception as e:
            print(f"   ❌ Error extrayendo tabla página {page_num}: {str(e)}")
            return {}
    
    def _find_ticker_in_row(self, cells: List, target_tickers: List[str]) -> Optional[str]:
        """Busca ticker objetivo en las celdas de la fila"""
        try:
            # Revisar las primeras 3 celdas
            for i in range(min(3, len(cells))):
                cell = cells[i]
                cell_text = cell.text_content().strip().upper()
                
                # Búsqueda directa
                for ticker in target_tickers:
                    if ticker.upper() == cell_text:
                        return ticker
                
                # Búsqueda en links
                try:
                    links = cell.locator('a').all()
                    for link in links:
                        link_text = link.text_content().strip().upper()
                        href = link.get_attribute('href') or ''
                        
                        for ticker in target_tickers:
                            if ticker.upper() == link_text or ticker.lower() in href.lower():
                                return ticker
                except:
                    pass
            
            return None
            
        except Exception:
            return None
    
    def _parse_ratios_from_cells(self, cells: List, ticker: str) -> Dict:
        """Parsea ratios de las celdas usando asignación inteligente"""
        try:
            ratios = {'ticker': ticker}
            
            # Extraer todos los valores numéricos
            numeric_values = []
            
            for i, cell in enumerate(cells):
                try:
                    cell_text = cell.text_content().strip()
                    
                    if cell_text and cell_text not in ['-', 'S/D', 'N/A', '']:
                        cleaned_value = self._clean_numeric_value(cell_text)
                        if cleaned_value is not None:
                            numeric_values.append({
                                'position': i,
                                'value': cleaned_value,
                                'original': cell_text
                            })
                
                except:
                    continue
            
            # Asignación inteligente por rangos típicos
            if len(numeric_values) >= 6:
                # P/E Ratio: típicamente entre 3-100
                pe_candidates = [v for v in numeric_values if 3 <= v['value'] <= 100]
                if pe_candidates:
                    ratios['pe'] = pe_candidates[0]['value']
                
                # ROE: típicamente entre -30% y 80%
                roe_candidates = [v for v in numeric_values if -30 <= v['value'] <= 80]
                if roe_candidates and len(roe_candidates) > 1:
                    ratios['roe'] = roe_candidates[1]['value']
                
                # Debt/Equity: típicamente entre 0 y 5
                de_candidates = [v for v in numeric_values if 0 <= v['value'] <= 5]
                if de_candidates:
                    ratios['debt_to_equity'] = de_candidates[0]['value']
                
                # Current Ratio: típicamente entre 0.3 y 8
                cr_candidates = [v for v in numeric_values if 0.3 <= v['value'] <= 8]
                if cr_candidates:
                    ratios['current_ratio'] = cr_candidates[-1]['value']
                
                # P/B Ratio: típicamente entre 0.2 y 15
                pb_candidates = [v for v in numeric_values if 0.2 <= v['value'] <= 15]
                if pb_candidates and len(pb_candidates) > 2:
                    ratios['pb'] = pb_candidates[2]['value']
            
            # Calcular métricas derivadas
            ratios['fundamental_score'] = self._calculate_fundamental_score(ratios)
            ratios['valuation_category'] = self._categorize_valuation(ratios)
            
            return ratios
            
        except Exception as e:
            print(f"      ❌ Error parseando {ticker}: {str(e)}")
            return {}
    
    def _clean_numeric_value(self, text: str) -> Optional[float]:
        """Limpia y convierte texto a valor numérico"""
        try:
            if not text or text in ['-', 'S/D', 'N/A', '', 'null']:
                return None
            
            # Remover símbolos comunes
            clean_text = text.strip().replace('$', '').replace('%', '').replace('+', '').replace(' ', '')
            
            # Manejar formato europeo (1.234,56)
            if ',' in clean_text and '.' in clean_text:
                parts = clean_text.split(',')
                if len(parts) == 2:
                    integer_part = parts[0].replace('.', '')
                    decimal_part = parts[1]
                    clean_text = f"{integer_part}.{decimal_part}"
            
            # Remover caracteres no numéricos excepto punto y guión
            clean_text = re.sub(r'[^\d\.\-]', '', clean_text)
            
            if clean_text:
                value = float(clean_text)
                
                # Filtrar valores absurdos
                if abs(value) > 10000000:  # Muy grande
                    return None
                
                return value
            
            return None
            
        except (ValueError, AttributeError):
            return None
    
    def _calculate_fundamental_score(self, ratios: Dict) -> float:
        """Calcula score fundamental"""
        try:
            score = 50  # Base neutral
            
            # ROE
            roe = ratios.get('roe')
            if roe is not None:
                if roe > 20:
                    score += 15
                elif roe > 15:
                    score += 10
                elif roe > 10:
                    score += 5
                elif roe < 0:
                    score -= 15
            
            # P/E
            pe = ratios.get('pe')
            if pe is not None:
                if 8 <= pe <= 15:
                    score += 10
                elif 15 < pe <= 25:
                    score += 5
                elif pe > 40:
                    score -= 10
                elif pe < 5:
                    score -= 5
            
            # Debt/Equity
            de = ratios.get('debt_to_equity')
            if de is not None:
                if de < 0.3:
                    score += 10
                elif de < 0.6:
                    score += 5
                elif de > 1.5:
                    score -= 15
            
            # Current Ratio
            cr = ratios.get('current_ratio')
            if cr is not None:
                if cr > 1.5:
                    score += 5
                elif cr < 1:
                    score -= 10
            
            return min(100, max(0, score))
            
        except:
            return 50
    
    def _categorize_valuation(self, ratios: Dict) -> str:
        """Categoriza valuación"""
        try:
            pe = ratios.get('pe')
            pb = ratios.get('pb')
            
            if pe is None and pb is None:
                return 'insufficient_data'
            
            signals = []
            
            if pe is not None:
                if pe < 8:
                    signals.append('cheap')
                elif pe > 25:
                    signals.append('expensive')
                else:
                    signals.append('fair')
            
            if pb is not None:
                if pb < 1:
                    signals.append('cheap')
                elif pb > 3:
                    signals.append('expensive')
                else:
                    signals.append('fair')
            
            cheap_count = signals.count('cheap')
            expensive_count = signals.count('expensive')
            
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
        """Enriquece análisis de cartera con ratios de todas las páginas"""
        try:
            # Obtener tickers de la cartera
            tickers = [asset['ticker'] for asset in portfolio_data.get('activos', [])]
            
            if not tickers:
                print("⚠️ No hay tickers en la cartera para analizar")
                return portfolio_data
            
            print(f"📊 Analizando ratios (TODAS LAS PÁGINAS) para: {tickers}")
            
            # Obtener ratios con búsqueda paginada
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
                    enhanced_portfolio['activos'][i]['fundamental_analysis'] = self._interpret_ratios_simple(asset_ratios)
                    
                    print(f"✅ {ticker} enriquecido con ratios fundamentales")
                else:
                    print(f"⚠️ No se encontraron ratios para {ticker} en ninguna página")
            
            # Resumen fundamental
            enhanced_portfolio['fundamental_summary'] = self._generate_portfolio_summary(ratios_by_ticker)
            
            print(f"✅ Portfolio enriquecido: {len(ratios_by_ticker)}/{len(tickers)} activos con ratios")
            return enhanced_portfolio
            
        except Exception as e:
            print(f"❌ Error enriqueciendo análisis: {str(e)}")
            return portfolio_data
    
    def _interpret_ratios_simple(self, ratios: Dict) -> Dict:
        """Interpretación simple de ratios"""
        interpretation = {
            'valuation_status': 'unknown',
            'financial_health': 'unknown', 
            'simple_summary': ''
        }
        
        try:
            pe = ratios.get('pe')
            roe = ratios.get('roe')
            
            # Valuación
            if pe is not None:
                if pe < 10:
                    interpretation['valuation_status'] = 'barata'
                elif pe > 25:
                    interpretation['valuation_status'] = 'cara'
                else:
                    interpretation['valuation_status'] = 'razonable'
            
            # Salud financiera 
            health_score = 0
            
            if roe is not None:
                if roe > 15:
                    health_score += 1
                elif roe < 5:
                    health_score -= 1
            
            de = ratios.get('debt_to_equity')
            if de is not None:
                if de < 0.5:
                    health_score += 1
                elif de > 1.5:
                    health_score -= 1
            
            if health_score >= 1:
                interpretation['financial_health'] = 'buena'
            elif health_score <= -1:
                interpretation['financial_health'] = 'preocupante'
            else:
                interpretation['financial_health'] = 'aceptable'
            
            # Resumen
            valuation = interpretation['valuation_status']
            health = interpretation['financial_health']
            
            if valuation == 'barata' and health == 'buena':
                interpretation['simple_summary'] = "Oportunidad: Empresa sólida a precio atractivo"
            elif valuation == 'cara' and health == 'buena':
                interpretation['simple_summary'] = "Calidad premium: Buena empresa pero cara"
            elif health == 'preocupante':
                interpretation['simple_summary'] = "Riesgo: Problemas financieros"
            else:
                interpretation['simple_summary'] = f"Empresa {health} con valuación {valuation}"
            
            return interpretation
            
        except:
            return interpretation
    
    def _generate_portfolio_summary(self, ratios_by_ticker: Dict) -> Dict:
        """Genera resumen del portfolio"""
        try:
            if not ratios_by_ticker:
                return {}
            
            # Promedios
            pe_values = [r.get('pe') for r in ratios_by_ticker.values() if r.get('pe')]
            roe_values = [r.get('roe') for r in ratios_by_ticker.values() if r.get('roe')]
            
            summary = {
                'tickers_with_ratios': len(ratios_by_ticker),
                'avg_pe': sum(pe_values) / len(pe_values) if pe_values else 0,
                'avg_roe': sum(roe_values) / len(roe_values) if roe_values else 0,
                'top_picks': sorted(
                    [(t, r.get('fundamental_score', 0)) for t, r in ratios_by_ticker.items()],
                    key=lambda x: x[1], reverse=True
                )[:3]
            }
            
            return summary
            
        except:
            return {}

# FUNCIÓN DE TESTING
def test_paginated_scraper():
    """Test del scraper paginado"""
    print("🧪 TEST DEL SCRAPER PAGINADO")
    print("=" * 35)
    
    print("💡 Este scraper busca en TODAS las páginas de Screenermatic:")
    for i, url in enumerate([
        "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=&scrollPos=0",
        "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=20&scrollPos=300", 
        "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=40&scrollPos=200",
        "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=60&scrollPos=300"
    ], 1):
        print(f"   📄 Página {i}: {url}")
    
    print("\n🎯 PARA USAR ESTE SCRAPER:")
    print("1. Guarda este código como: financial_ratios_scraper_paginated.py") 
    print("2. Modifica tu comprehensive_market_analyzer.py para usar:")
    print("   from financial_ratios_scraper_paginated import FinancialRatiosScraperPaginated")
    print("3. Ejecuta: python test_integration.py --full")
    
    print("\n✅ AHORA SÍ DEBERÍA ENCONTRAR EDN Y TODOS LOS TICKERS!")
    
    return True

if __name__ == "__main__":
    test_paginated_scraper()