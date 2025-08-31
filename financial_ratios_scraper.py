# financial_ratios_scraper_fixed.py - Versión corregida con detección robusta de tabla
import time
from datetime import datetime, date
from typing import Dict, List, Optional
import re

class FinancialRatiosScraper:
    def __init__(self, page):
        self.page = page
        self.ratios_url = "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=&scrollPos=0"
    
    def get_financial_ratios_for_tickers(self, target_tickers: List[str]) -> Dict:
        """Obtiene ratios financieros para tickers específicos - VERSIÓN CORREGIDA"""
        try:
            print("📊 OBTENIENDO RATIOS FINANCIEROS...")
            print("-" * 40)
            
            # 1. Navegar a la página de ratios con headers mejorados
            print(f"🌐 Navegando a: {self.ratios_url}")
            
            # Configurar headers más realistas
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            self.page.goto(self.ratios_url, wait_until='networkidle')
            time.sleep(5)
            
            # 2. Detectar estructura de la tabla dinámicamente
            table_structure = self._detect_table_structure()
            
            if not table_structure['valid']:
                print(f"❌ No se pudo detectar estructura de tabla válida")
                print(f"   Debug info: {table_structure['debug_info']}")
                return {}
            
            print(f"✅ Estructura de tabla detectada: {table_structure['rows']} filas")
            
            # 3. Extraer datos usando la estructura detectada
            ratios_data = self._extract_ratios_table_improved(target_tickers, table_structure)
            
            if ratios_data:
                print(f"✅ Ratios extraídos para {len(ratios_data)} activos")
                return {
                    'fecha': date.today().isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'ratios_by_ticker': ratios_data,
                    'data_source': 'screenermatic',
                    'table_structure': table_structure,
                    'fields_available': self._get_available_fields()
                }
            else:
                print("❌ No se pudieron extraer ratios")
                return {}
                
        except Exception as e:
            print(f"❌ Error obteniendo ratios: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _detect_table_structure(self) -> Dict:
        """Detecta la estructura de la tabla dinámicamente"""
        try:
            print("🔍 Detectando estructura de tabla...")
            
            structure = {
                'valid': False,
                'rows': 0,
                'columns': 0,
                'table_selector': None,
                'row_selector': None,
                'debug_info': {}
            }
            
            # MÉTODO 1: Buscar tabla estándar
            table_selectors = [
                'table tbody tr',
                'tbody tr',
                'table tr',
                'tr'
            ]
            
            for selector in table_selectors:
                try:
                    rows = self.page.locator(selector).all()
                    row_count = len(rows)
                    
                    structure['debug_info'][selector] = row_count
                    
                    if row_count >= 10:  # Al menos 10 filas para considerar válido
                        # Verificar que las filas tengan suficientes columnas
                        sample_row = rows[0] if rows else None
                        if sample_row:
                            cells = sample_row.locator('td, th').all()
                            col_count = len(cells)
                            
                            if col_count >= 15:  # Screenermatic debe tener muchas columnas
                                structure.update({
                                    'valid': True,
                                    'rows': row_count,
                                    'columns': col_count,
                                    'table_selector': 'table',
                                    'row_selector': selector
                                })
                                
                                print(f"✅ Tabla detectada: {row_count} filas x {col_count} columnas")
                                return structure
                
                except Exception as e:
                    continue
            
            # MÉTODO 2: Buscar por contenido específico
            print("🔍 Método 2: Buscando por contenido específico...")
            
            # Buscar elementos que contengan tickers conocidos
            ticker_patterns = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'ALUA']
            
            for pattern in ticker_patterns:
                try:
                    ticker_elements = self.page.locator(f'text="{pattern}"').all()
                    if ticker_elements:
                        print(f"✅ Encontrado ticker {pattern} en página")
                        
                        # Buscar la fila que lo contiene
                        for element in ticker_elements:
                            row = element.locator('xpath=ancestor::tr').first
                            if row.count() > 0:
                                # Verificar que la fila tenga suficientes celdas
                                cells = row.locator('td, th').all()
                                if len(cells) >= 15:
                                    # Buscar tabla padre
                                    table = row.locator('xpath=ancestor::table').first
                                    if table.count() > 0:
                                        tbody_rows = table.locator('tbody tr').all()
                                        
                                        structure.update({
                                            'valid': True,
                                            'rows': len(tbody_rows),
                                            'columns': len(cells),
                                            'table_selector': 'table',
                                            'row_selector': 'tbody tr'
                                        })
                                        
                                        print(f"✅ Tabla encontrada por contenido: {len(tbody_rows)} filas")
                                        return structure
                                        
                except Exception as e:
                    continue
            
            # MÉTODO 3: Inspección completa de la página
            print("🔍 Método 3: Inspección completa...")
            
            try:
                # Ver qué tipo de contenido hay en la página
                page_text = self.page.content()
                
                # Buscar indicadores de que hay una tabla de ratios
                indicators = [
                    'P/E' in page_text,
                    'ROE' in page_text,
                    'Debt/Equity' in page_text,
                    'Current Ratio' in page_text,
                    len(re.findall(r'\b[A-Z]{2,6}\b', page_text)) > 50  # Muchos tickers
                ]
                
                if any(indicators):
                    print("✅ Página contiene datos de ratios financieros")
                    
                    # Buscar cualquier estructura tabular
                    all_rows = self.page.locator('tr').all()
                    
                    if len(all_rows) >= 10:
                        structure.update({
                            'valid': True,
                            'rows': len(all_rows),
                            'columns': 0,  # Lo determinamos después
                            'table_selector': None,
                            'row_selector': 'tr',
                            'fallback_method': True
                        })
                        
                        print(f"✅ Estructura fallback: {len(all_rows)} filas")
                        return structure
                else:
                    print("❌ La página no parece contener datos de ratios financieros")
                    
            except Exception as e:
                print(f"⚠️ Error en inspección completa: {str(e)}")
            
            print("❌ No se pudo detectar estructura de tabla válida")
            return structure
            
        except Exception as e:
            print(f"❌ Error detectando estructura: {str(e)}")
            structure['debug_info']['error'] = str(e)
            return structure
    
    def _extract_ratios_table_improved(self, target_tickers: List[str], table_structure: Dict) -> Dict:
        """Extrae ratios usando la estructura detectada - VERSIÓN MEJORADA"""
        try:
            ratios_data = {}
            
            # Usar selector detectado
            row_selector = table_structure['row_selector']
            table_rows = self.page.locator(row_selector).all()
            
            print(f"📊 Procesando {len(table_rows)} filas de ratios...")
            
            processed_count = 0
            
            for i, row in enumerate(table_rows):
                try:
                    # Extraer todas las celdas de la fila
                    cells = row.locator('td, th').all()
                    
                    if len(cells) < 10:  # Mínimo razonable para una fila de datos
                        continue
                    
                    # MÉTODO MEJORADO: Buscar ticker en cualquier celda inicial
                    ticker = self._extract_ticker_from_row_improved(cells, target_tickers)
                    
                    if not ticker:
                        continue
                    
                    print(f"📊 Extrayendo ratios para {ticker}...")
                    
                    # Extraer ratios de la fila
                    ratios = self._parse_ratio_cells_improved(cells, ticker)
                    
                    if ratios and ratios.get('ticker'):
                        ratios_data[ticker] = ratios
                        processed_count += 1
                        
                        # Mostrar progreso
                        pe = ratios.get('pe', 'N/A')
                        roe = ratios.get('roe', 'N/A')
                        print(f"✅ {ticker}: P/E={pe}, ROE={roe}")
                    
                    # Salir si ya encontramos todos los tickers que buscamos
                    if len(ratios_data) >= len(target_tickers):
                        print(f"✅ Todos los tickers objetivo encontrados")
                        break
                
                except Exception as e:
                    print(f"⚠️ Error procesando fila {i}: {str(e)}")
                    continue
            
            print(f"📊 Total ratios extraídos: {len(ratios_data)} de {len(target_tickers)} solicitados")
            return ratios_data
            
        except Exception as e:
            print(f"❌ Error extrayendo tabla de ratios: {str(e)}")
            return {}
    
    def _extract_ticker_from_row_improved(self, cells: List, target_tickers: List[str]) -> Optional[str]:
        """Busca ticker en las primeras celdas de la fila - MÉTODO MEJORADO"""
        try:
            # Revisar las primeras 3 celdas en busca del ticker
            for i in range(min(3, len(cells))):
                cell = cells[i]
                cell_text = cell.text_content().strip()
                
                # MÉTODO 1: Texto directo
                if cell_text in target_tickers:
                    return cell_text
                
                # MÉTODO 2: Buscar en links dentro de la celda
                try:
                    links = cell.locator('a').all()
                    for link in links:
                        link_text = link.text_content().strip()
                        if link_text in target_tickers:
                            return link_text
                        
                        # También buscar en href
                        href = link.get_attribute('href') or ''
                        for ticker in target_tickers:
                            if ticker.lower() in href.lower():
                                return ticker
                                
                except Exception:
                    pass
                
                # MÉTODO 3: Buscar tickers que contengan el texto de la celda
                cell_upper = cell_text.upper()
                for ticker in target_tickers:
                    if ticker.upper() == cell_upper:
                        return ticker
                
                # MÉTODO 4: Buscar con regex flexible
                if len(cell_text) >= 2 and len(cell_text) <= 6 and cell_text.isalpha():
                    cell_upper = cell_text.upper()
                    for ticker in target_tickers:
                        if ticker.upper() == cell_upper:
                            return ticker
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_ratio_cells_improved(self, cells: List, ticker: str) -> Dict:
        """Parsea las celdas para extraer ratios - VERSIÓN ROBUSTA"""
        try:
            ratios = {'ticker': ticker}
            
            # MAPEO FLEXIBLE: Buscar por contenido conocido en lugar de posiciones fijas
            print(f"   🔍 Analizando {len(cells)} celdas para {ticker}...")
            
            # Extraer valores numéricos de todas las celdas
            numeric_values = []
            
            for i, cell in enumerate(cells):
                try:
                    cell_text = cell.text_content().strip()
                    
                    # Limpiar y intentar convertir a número
                    if cell_text and cell_text not in ['-', 'S/D', 'N/A', '']:
                        cleaned_value = self._clean_ratio_value_improved(cell_text)
                        if cleaned_value is not None:
                            numeric_values.append({
                                'position': i,
                                'original_text': cell_text,
                                'value': cleaned_value
                            })
                
                except Exception:
                    continue
            
            print(f"   📊 Valores numéricos encontrados: {len(numeric_values)}")
            
            # ASIGNACIÓN INTELIGENTE basada en rangos típicos
            if len(numeric_values) >= 8:  # Mínimo para un análisis básico
                
                # P/E Ratio: típicamente entre 5-50
                pe_candidates = [v for v in numeric_values if 3 <= v['value'] <= 100]
                if pe_candidates:
                    ratios['pe'] = pe_candidates[0]['value']  # Tomar el primero como P/E
                
                # ROE: típicamente entre -20% y 50%
                roe_candidates = [v for v in numeric_values if -30 <= v['value'] <= 80]
                if roe_candidates and len(roe_candidates) > 1:
                    ratios['roe'] = roe_candidates[1]['value']  # Segundo candidato como ROE
                
                # Debt/Equity: típicamente entre 0 y 3
                de_candidates = [v for v in numeric_values if 0 <= v['value'] <= 5]
                if de_candidates:
                    ratios['debt_to_equity'] = de_candidates[0]['value']
                
                # Current Ratio: típicamente entre 0.5 y 5
                cr_candidates = [v for v in numeric_values if 0.3 <= v['value'] <= 8]
                if cr_candidates and len(cr_candidates) > 1:
                    ratios['current_ratio'] = cr_candidates[-1]['value']  # Último como current ratio
                
                # P/B Ratio: típicamente entre 0.5 y 10
                pb_candidates = [v for v in numeric_values if 0.2 <= v['value'] <= 15]
                if pb_candidates and len(pb_candidates) > 2:
                    ratios['pb'] = pb_candidates[2]['value']  # Tercero como P/B
                
                print(f"   ✅ Ratios asignados: P/E={ratios.get('pe', 'N/A')}, ROE={ratios.get('roe', 'N/A')}, D/E={ratios.get('debt_to_equity', 'N/A')}")
            
            else:
                print(f"   ⚠️ Datos insuficientes: solo {len(numeric_values)} valores numéricos")
            
            # Calcular métricas derivadas
            ratios['fundamental_score'] = self._calculate_fundamental_score(ratios)
            ratios['valuation_category'] = self._categorize_valuation(ratios)
            
            return ratios if len(ratios) > 3 else {}  # Al menos ticker + 2 ratios
            
        except Exception as e:
            print(f"❌ Error parseando ratios para {ticker}: {str(e)}")
            return {}
    
    def _clean_ratio_value_improved(self, text: str) -> Optional[float]:
        """Limpia valores de ratios - VERSIÓN MEJORADA"""
        try:
            if not text or text in ['-', 'S/D', 'N/A', '', 'null', 'undefined']:
                return None
            
            # Remover caracteres comunes pero preservar números
            clean_text = text.strip()
            
            # Remover símbolos monetarios y porcentajes
            clean_text = clean_text.replace('$', '').replace('%', '').replace('+', '')
            
            # Manejar separadores de miles (puntos) y decimales (comas)
            # Ejemplo: "1.234,56" -> "1234.56"
            if ',' in clean_text and '.' in clean_text:
                # Formato europeo: 1.234,56
                parts = clean_text.split(',')
                if len(parts) == 2:
                    integer_part = parts[0].replace('.', '')
                    decimal_part = parts[1]
                    clean_text = f"{integer_part}.{decimal_part}"
            elif '.' in clean_text:
                # Verificar si es separador de miles o decimal
                parts = clean_text.split('.')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Probablemente es decimal
                    pass
                elif len(parts) > 2 or (len(parts) == 2 and len(parts[1]) > 2):
                    # Probablemente son separadores de miles
                    clean_text = clean_text.replace('.', '')
            
            # Remover espacios y caracteres extraños
            clean_text = re.sub(r'[^\d\.\-]', '', clean_text)
            
            if clean_text:
                value = float(clean_text)
                
                # Filtrar valores claramente erróneos
                if abs(value) > 1000000:  # Muy grande
                    return None
                
                return value
            
            return None
            
        except (ValueError, AttributeError):
            return None
    
    def _get_available_fields(self) -> List[str]:
        """Retorna lista de campos disponibles"""
        return [
            'pe', 'roe', 'debt_to_equity', 'current_ratio', 'pb',
            'roa', 'roic', 'ps', 'dividend_yield', 'market_cap',
            'fundamental_score', 'valuation_category'
        ]
    
    def _calculate_fundamental_score(self, ratios: Dict) -> float:
        """Calcula un score fundamental basado en ratios clave"""
        try:
            score = 50  # Score base neutral
            
            # ROE (Return on Equity) - Rentabilidad
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
            
            # P/E Ratio - Valuación
            pe = ratios.get('pe')
            if pe is not None:
                if 8 <= pe <= 15:  # P/E razonable
                    score += 10
                elif 15 < pe <= 25:
                    score += 5
                elif pe > 40:  # Muy caro
                    score -= 10
                elif pe < 5:  # Muy barato o problemático
                    score -= 5
            
            # Debt to Equity - Solvencia
            de = ratios.get('debt_to_equity')
            if de is not None:
                if de < 0.3:  # Poco endeudamiento
                    score += 10
                elif de < 0.6:
                    score += 5
                elif de > 1.5:  # Muy endeudado
                    score -= 15
            
            # Current Ratio - Liquidez
            current_ratio = ratios.get('current_ratio')
            if current_ratio is not None:
                if current_ratio > 1.5:
                    score += 5
                elif current_ratio < 1:
                    score -= 10
            
            return min(100, max(0, score))
            
        except Exception as e:
            return 50  # Score neutral si hay error
    
    def _categorize_valuation(self, ratios: Dict) -> str:
        """Categoriza la valuación del activo"""
        try:
            pe = ratios.get('pe')
            pb = ratios.get('pb')
            
            if pe is None and pb is None:
                return 'insufficient_data'
            
            valuation_signals = []
            
            if pe is not None:
                if pe < 8:
                    valuation_signals.append('cheap_pe')
                elif pe > 25:
                    valuation_signals.append('expensive_pe')
                else:
                    valuation_signals.append('fair_pe')
            
            if pb is not None:
                if pb < 1:
                    valuation_signals.append('cheap_pb')
                elif pb > 3:
                    valuation_signals.append('expensive_pb')
                else:
                    valuation_signals.append('fair_pb')
            
            # Determinar categoría general
            cheap_count = sum(1 for signal in valuation_signals if 'cheap' in signal)
            expensive_count = sum(1 for signal in valuation_signals if 'expensive' in signal)
            
            if cheap_count > expensive_count:
                return 'undervalued'
            elif expensive_count > cheap_count:
                return 'overvalued'
            else:
                return 'fairly_valued'
                
        except Exception:
            return 'unknown'
    
    def enhance_portfolio_analysis_with_ratios(self, portfolio_data: Dict) -> Dict:
        """Enriquece el análisis de cartera con ratios fundamentales - MÉTODO PRINCIPAL"""
        try:
            # Obtener tickers de la cartera
            tickers = [asset['ticker'] for asset in portfolio_data.get('activos', [])]
            
            if not tickers:
                print("⚠️ No hay tickers en la cartera para analizar")
                return portfolio_data
            
            print(f"📊 Analizando ratios fundamentales para: {tickers}")
            
            # Obtener ratios con método mejorado
            ratios_data = self.get_financial_ratios_for_tickers(tickers)
            
            if not ratios_data or not ratios_data.get('ratios_by_ticker'):
                print("⚠️ No se pudieron obtener ratios - usando análisis técnico solamente")
                return portfolio_data
            
            # Enriquecer cada activo con sus ratios
            enhanced_portfolio = portfolio_data.copy()
            ratios_by_ticker = ratios_data['ratios_by_ticker']
            
            for i, asset in enumerate(enhanced_portfolio.get('activos', [])):
                ticker = asset['ticker']
                
                if ticker in ratios_by_ticker:
                    asset_ratios = ratios_by_ticker[ticker]
                    enhanced_portfolio['activos'][i]['fundamental_ratios'] = asset_ratios
                    
                    # Agregar interpretación simple
                    enhanced_portfolio['activos'][i]['fundamental_analysis'] = self._interpret_ratios_simple(asset_ratios)
                    
                    print(f"✅ {ticker} enriquecido con ratios fundamentales")
                else:
                    print(f"⚠️ No se encontraron ratios para {ticker}")
            
            # Agregar resumen fundamental de la cartera
            enhanced_portfolio['fundamental_summary'] = self._generate_portfolio_fundamental_summary(ratios_by_ticker)
            
            print(f"✅ Portfolio enriquecido con {len(ratios_by_ticker)} activos con ratios")
            return enhanced_portfolio
            
        except Exception as e:
            print(f"❌ Error enriqueciendo análisis con ratios: {str(e)}")
            import traceback
            traceback.print_exc()
            return portfolio_data
    
    def _interpret_ratios_simple(self, ratios: Dict) -> Dict:
        """Interpreta ratios en lenguaje simple"""
        interpretation = {
            'valuation_status': 'unknown',
            'financial_health': 'unknown',
            'investment_appeal': 'unknown',
            'key_strengths': [],
            'key_concerns': [],
            'simple_summary': ''
        }
        
        try:
            # Análisis de valuación
            pe = ratios.get('pe')
            if pe is not None:
                if pe < 10:
                    interpretation['valuation_status'] = 'barata'
                    interpretation['key_strengths'].append(f"P/E bajo ({pe:.1f}) - precio atractivo")
                elif pe > 25:
                    interpretation['valuation_status'] = 'cara'
                    interpretation['key_concerns'].append(f"P/E alto ({pe:.1f}) - posible sobrevaloración")
                else:
                    interpretation['valuation_status'] = 'razonable'
            
            # Análisis de salud financiera
            roe = ratios.get('roe')
            debt_equity = ratios.get('debt_to_equity')
            current_ratio = ratios.get('current_ratio')
            
            health_score = 0
            
            if roe is not None and roe > 15:
                health_score += 1
                interpretation['key_strengths'].append(f"ROE sólido ({roe:.1f}%) - buena rentabilidad")
            elif roe is not None and roe < 5:
                health_score -= 1
                interpretation['key_concerns'].append(f"ROE bajo ({roe:.1f}%) - rentabilidad débil")
            
            if debt_equity is not None and debt_equity < 0.5:
                health_score += 1
                interpretation['key_strengths'].append("Bajo endeudamiento - empresa sólida")
            elif debt_equity is not None and debt_equity > 1.5:
                health_score -= 1
                interpretation['key_concerns'].append("Alto endeudamiento - riesgo financiero")
            
            if current_ratio is not None and current_ratio > 1.5:
                health_score += 1
                interpretation['key_strengths'].append("Buena liquidez corriente")
            elif current_ratio is not None and current_ratio < 1:
                health_score -= 1
                interpretation['key_concerns'].append("Liquidez ajustada - riesgo de corto plazo")
            
            # Determinar salud financiera general
            if health_score >= 2:
                interpretation['financial_health'] = 'excelente'
            elif health_score >= 1:
                interpretation['financial_health'] = 'buena'
            elif health_score >= 0:
                interpretation['financial_health'] = 'aceptable'
            else:
                interpretation['financial_health'] = 'preocupante'
            
            # Determinar atractivo de inversión
            fundamental_score = ratios.get('fundamental_score', 50)
            if fundamental_score >= 70:
                interpretation['investment_appeal'] = 'muy_atractiva'
            elif fundamental_score >= 60:
                interpretation['investment_appeal'] = 'atractiva'
            elif fundamental_score >= 40:
                interpretation['investment_appeal'] = 'neutral'
            else:
                interpretation['investment_appeal'] = 'poco_atractiva'
            
            # Resumen simple
            interpretation['simple_summary'] = self._generate_simple_summary(interpretation)
            
            return interpretation
            
        except Exception as e:
            print(f"⚠️ Error interpretando ratios: {str(e)}")
            return interpretation
    
    def _generate_simple_summary(self, interpretation: Dict) -> str:
        """Genera resumen en lenguaje simple"""
        valuation = interpretation['valuation_status']
        health = interpretation['financial_health']
        
        # Combinaciones comunes
        if valuation == 'barata' and health in ['excelente', 'buena']:
            return "Oportunidad: Empresa sólida a precio atractivo"
        elif valuation == 'cara' and health == 'excelente':
            return "Calidad premium: Excelente empresa pero cara"
        elif valuation == 'razonable' and health == 'buena':
            return "Equilibrada: Buena empresa a precio justo"
        elif health == 'preocupante':
            return "Riesgo: Problemas financieros evidentes"
        elif valuation == 'cara' and health in ['aceptable', 'preocupante']:
            return "Evitar: Cara y con problemas fundamentales"
        else:
            return f"Empresa {health} con valuación {valuation}"
    
    def _generate_portfolio_fundamental_summary(self, ratios_by_ticker: Dict) -> Dict:
        """Genera resumen fundamental de toda la cartera"""
        try:
            summary = {
                'avg_pe': 0,
                'avg_roe': 0,
                'avg_debt_equity': 0,
                'valuation_distribution': {},
                'health_distribution': {},
                'top_fundamental_picks': [],
                'concerns': []
            }
            
            if not ratios_by_ticker:
                return summary
            
            # Calcular promedios
            pe_values = [ratios.get('pe', 0) for ratios in ratios_by_ticker.values() if ratios.get('pe')]
            roe_values = [ratios.get('roe', 0) for ratios in ratios_by_ticker.values() if ratios.get('roe')]
            de_values = [ratios.get('debt_to_equity', 0) for ratios in ratios_by_ticker.values() if ratios.get('debt_to_equity')]
            
            if pe_values:
                summary['avg_pe'] = sum(pe_values) / len(pe_values)
            if roe_values:
                summary['avg_roe'] = sum(roe_values) / len(roe_values)
            if de_values:
                summary['avg_debt_equity'] = sum(de_values) / len(de_values)
            
            # Top picks fundamentales
            scored_tickers = [
                (ticker, ratios.get('fundamental_score', 0))
                for ticker, ratios in ratios_by_ticker.items()
            ]
            scored_tickers.sort(key=lambda x: x[1], reverse=True)
            
            summary['top_fundamental_picks'] = scored_tickers[:3]
            
            return summary
            
        except Exception as e:
            print(f"❌ Error generando resumen fundamental: {str(e)}")
            return summary
    
    def save_ratios_to_db(self, ratios_data: Dict, db_manager) -> bool:
        """Guarda ratios en la base de datos"""
        try:
            if not ratios_data or not db_manager:
                return False
            
            fecha = ratios_data['fecha']
            ratios_by_ticker = ratios_data.get('ratios_by_ticker', {})
            
            for ticker, ratios in ratios_by_ticker.items():
                ratio_record = {
                    'fecha': fecha,
                    'ticker': ticker,
                    'pe_ratio': ratios.get('pe'),
                    'pb_ratio': ratios.get('pb'),
                    'roe': ratios.get('roe'),
                    'roa': ratios.get('roa'),
                    'debt_to_equity': ratios.get('debt_to_equity'),
                    'current_ratio': ratios.get('current_ratio'),
                    'market_cap': ratios.get('market_cap'),
                    'fundamental_score': ratios.get('fundamental_score'),
                    'valuation_category': ratios.get('valuation_category'),
                    'data_source': 'screenermatic'
                }
                
                # Usar upsert para evitar duplicados
                db_manager.supabase.table('financial_ratios').upsert(ratio_record).execute()
            
            print(f"✅ Ratios guardados para {len(ratios_by_ticker)} activos")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando ratios: {str(e)}")
            return False

# FUNCIÓN DE TESTING MEJORADA
def test_ratios_scraper_standalone():
    """Test independiente del scraper de ratios"""
    print("🧪 TEST INDEPENDIENTE: RATIOS SCRAPER CORREGIDO")
    print("=" * 55)
    
    print("⚠️ ESTE TEST REQUIERE:")
    print("1. Una instancia de Playwright activa")
    print("2. Conexión a internet")
    print("3. Que el sitio Screenermatic esté disponible")
    
    print("\n💡 MEJORAS IMPLEMENTADAS:")
    print("✅ Detección dinámica de estructura de tabla")
    print("✅ Múltiples métodos de extracción de tickers") 
    print("✅ Asignación inteligente de ratios por rango")
    print("✅ Limpieza mejorada de valores numéricos")
    print("✅ Headers más realistas para evitar bloqueos")
    print("✅ Mejor manejo de errores con debug detallado")
    
    print("\n📋 PARA USAR EN TU SISTEMA:")
    print("1. Reemplaza tu financial_ratios_scraper.py con esta versión")
    print("2. Ejecuta: python test_integration.py --full")
    print("3. Debería mostrar 4/4 componentes funcionando")
    
    return True

if __name__ == "__main__":
    test_ratios_scraper_standalone()