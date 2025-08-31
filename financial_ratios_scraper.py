# financial_ratios_scraper.py - Scraper para ratios financieros de Screenermatic
import time
from datetime import datetime, date
from typing import Dict, List, Optional
import re

class FinancialRatiosScraper:
    def __init__(self, page):
        self.page = page
        self.ratios_url = "https://www.screenermatic.com/general_ratios.php?variable=&variable2=art_ticker&tipo=asc&ini=&scrollPos=0"
    
    def get_financial_ratios_for_tickers(self, target_tickers: List[str]) -> Dict:
        """Obtiene ratios financieros para tickers específicos"""
        try:
            print("📊 OBTENIENDO RATIOS FINANCIEROS...")
            print("-" * 40)
            
            # 1. Navegar a la página de ratios
            print(f"🌐 Navegando a: {self.ratios_url}")
            self.page.goto(self.ratios_url, wait_until='networkidle')
            time.sleep(3)
            
            # 2. Extraer datos de la tabla
            ratios_data = self._extract_ratios_table(target_tickers)
            
            if ratios_data:
                print(f"✅ Ratios extraídos para {len(ratios_data)} activos")
                return {
                    'fecha': date.today().isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'ratios_by_ticker': ratios_data,
                    'data_source': 'screenermatic',
                    'fields_available': self._get_available_fields()
                }
            else:
                print("❌ No se pudieron extraer ratios")
                return {}
                
        except Exception as e:
            print(f"❌ Error obteniendo ratios: {str(e)}")
            return {}
    
    def _extract_ratios_table(self, target_tickers: List[str]) -> Dict:
        """Extrae ratios de la tabla HTML"""
        try:
            ratios_data = {}
            
            # Buscar filas de la tabla
            table_rows = self.page.locator('tbody tr').all()
            
            print(f"📊 Procesando {len(table_rows)} filas de ratios...")
            
            for i, row in enumerate(table_rows):
                try:
                    # Extraer ticker de la primera columna
                    ticker_cell = row.locator('td').first
                    if ticker_cell.count() == 0:
                        continue
                    
                    # Buscar el ticker en el link o texto
                    ticker_links = ticker_cell.locator('a.btn.btn-dark').all()
                    ticker = None
                    
                    for link in ticker_links:
                        link_text = link.text_content().strip()
                        if link_text and len(link_text) <= 6 and link_text.isalpha():
                            ticker = link_text
                            break
                    
                    # Solo procesar si es uno de nuestros tickers objetivo
                    if ticker not in target_tickers:
                        continue
                    
                    print(f"📊 Extrayendo ratios para {ticker}...")
                    
                    # Extraer todas las celdas de la fila
                    cells = row.locator('td').all()
                    
                    if len(cells) >= 18:  # Verificar que tenga suficientes columnas
                        ratios = self._parse_ratio_cells(cells, ticker)
                        if ratios:
                            ratios_data[ticker] = ratios
                            print(f"✅ {ticker}: P/E={ratios.get('pe', 'N/A')}, ROE={ratios.get('roe', 'N/A')}")
                    
                except Exception as e:
                    print(f"⚠️ Error procesando fila {i}: {str(e)}")
                    continue
            
            return ratios_data
            
        except Exception as e:
            print(f"❌ Error extrayendo tabla de ratios: {str(e)}")
            return {}
    
    def _parse_ratio_cells(self, cells: List, ticker: str) -> Dict:
        """Parsea las celdas individuales para extraer ratios"""
        try:
            ratios = {'ticker': ticker}
            
            # Mapeo de posiciones de columnas según la tabla que mostraste
            column_mapping = {
                1: 'current_ratio',      # Current R
                2: 'quick_ratio',        # Quick R
                3: 'cash_ratio',         # Cash R
                4: 'debt_to_equity',     # D/E
                5: 'interest_coverage',  # Int. Cov
                6: 'asset_to_equity',    # A/E
                7: 'roa',               # ROA
                8: 'roe',               # ROE
                9: 'roic',              # ROIC
                10: 'pe',               # P/E
                11: 'ps',               # P/S
                12: 'pb',               # P/B
                13: 'pb_tangible',      # P/B tan
                14: 'price_to_cfo',     # P/CFO
                15: 'dividend_yield',   # Div. Yield
                16: 'market_cap',       # Mkt. Cap.
                17: 'price',            # Precio
                18: 'change_pct'        # Variación
            }
            
            for position, field_name in column_mapping.items():
                if position < len(cells):
                    cell_text = cells[position].text_content().strip()
                    
                    # Limpiar y convertir valores
                    cleaned_value = self._clean_ratio_value(cell_text, field_name)
                    if cleaned_value is not None:
                        ratios[field_name] = cleaned_value
            
            # Calcular ratios derivados útiles
            ratios['fundamental_score'] = self._calculate_fundamental_score(ratios)
            ratios['valuation_category'] = self._categorize_valuation(ratios)
            
            return ratios
            
        except Exception as e:
            print(f"❌ Error parseando ratios para {ticker}: {str(e)}")
            return {}
    
    def _clean_ratio_value(self, text: str, field_name: str) -> Optional[float]:
        """Limpia y convierte valores de ratios"""
        try:
            if not text or text in ['-', 'S/D', 'N/A', '']:
                return None
            
            # Remover caracteres especiales pero preservar números y decimales
            if field_name == 'market_cap':
                # Market cap puede tener 'B' para billones
                clean_text = text.replace('B', '').replace(',', '').strip()
            elif field_name in ['change_pct']:
                # Porcentajes
                clean_text = text.replace('%', '').replace('+', '').strip()
            else:
                # Otros ratios
                clean_text = text.replace(',', '').strip()
            
            return float(clean_text)
            
        except (ValueError, AttributeError):
            return None
    
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
    
    def _get_available_fields(self) -> List[str]:
        """Retorna lista de campos disponibles"""
        return [
            'current_ratio', 'quick_ratio', 'cash_ratio',
            'debt_to_equity', 'interest_coverage', 'asset_to_equity',
            'roa', 'roe', 'roic',
            'pe', 'ps', 'pb', 'pb_tangible', 'price_to_cfo', 'dividend_yield',
            'market_cap', 'price', 'change_pct',
            'fundamental_score', 'valuation_category'
        ]
    
    def enhance_portfolio_analysis_with_ratios(self, portfolio_data: Dict) -> Dict:
        """Enriquece el análisis de cartera con ratios fundamentales"""
        try:
            # Obtener tickers de la cartera
            tickers = [asset['ticker'] for asset in portfolio_data.get('activos', [])]
            
            if not tickers:
                print("⚠️ No hay tickers en la cartera para analizar")
                return portfolio_data
            
            print(f"📊 Analizando ratios fundamentales para: {tickers}")
            
            # Obtener ratios
            ratios_data = self.get_financial_ratios_for_tickers(tickers)
            
            if not ratios_data:
                print("⚠️ No se pudieron obtener ratios - usando análisis técnico solamente")
                return portfolio_data
            
            # Enriquecer cada activo con sus ratios
            enhanced_portfolio = portfolio_data.copy()
            
            for i, asset in enumerate(enhanced_portfolio.get('activos', [])):
                ticker = asset['ticker']
                
                if ticker in ratios_data.get('ratios_by_ticker', {}):
                    asset_ratios = ratios_data['ratios_by_ticker'][ticker]
                    enhanced_portfolio['activos'][i]['fundamental_ratios'] = asset_ratios
                    
                    # Agregar interpretación simple
                    enhanced_portfolio['activos'][i]['fundamental_analysis'] = self._interpret_ratios_simple(asset_ratios)
                    
                    print(f"✅ {ticker} enriquecido con ratios fundamentales")
            
            # Agregar resumen fundamental de la cartera
            enhanced_portfolio['fundamental_summary'] = self._generate_portfolio_fundamental_summary(
                ratios_data.get('ratios_by_ticker', {})
            )
            
            return enhanced_portfolio
            
        except Exception as e:
            print(f"❌ Error enriqueciendo análisis con ratios: {str(e)}")
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
        appeal = interpretation['investment_appeal']
        
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
            
            # Distribución de valuaciones
            valuations = {}
            healths = {}
            
            for ticker, ratios in ratios_by_ticker.items():
                valuation = ratios.get('valuation_category', 'unknown')
                valuations[valuation] = valuations.get(valuation, 0) + 1
                
                fundamental_analysis = ratios.get('fundamental_analysis', {})
                health = fundamental_analysis.get('financial_health', 'unknown')
                healths[health] = healths.get(health, 0) + 1
            
            summary['valuation_distribution'] = valuations
            summary['health_distribution'] = healths
            
            # Top picks fundamentales
            scored_tickers = [
                (ticker, ratios.get('fundamental_score', 0))
                for ticker, ratios in ratios_by_ticker.items()
            ]
            scored_tickers.sort(key=lambda x: x[1], reverse=True)
            
            summary['top_fundamental_picks'] = scored_tickers[:3]
            
            # Concerns fundamentales
            for ticker, ratios in ratios_by_ticker.items():
                fundamental_analysis = ratios.get('fundamental_analysis', {})
                concerns = fundamental_analysis.get('key_concerns', [])
                if concerns:
                    summary['concerns'].extend([f"{ticker}: {concern}" for concern in concerns[:2]])
            
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

# FUNCIÓN DE TESTING SIMPLE
def test_report_scraper_simple():
    """Test básico sin Playwright para verificar lógica"""
    print("🧪 TEST BÁSICO DE LÓGICA DE REPORTE")
    print("=" * 40)
    
    # Simular datos del reporte que mostraste
    sample_report_text = """
    Renta variable: El Merval avanzó 2.0% en dólares ayer, en un día positivo en EE.UU.
    A nivel de acciones, ALUA (-4.6%) tuvo el peor desempeño, mientras que EDN (5.4%), 
    TECO2 (4.8%), BMA (4.5%) concentraron los mejores retornos.
    """
    
    # Test de extracción de insights
    from balanz_daily_report_scraper import BalanzDailyReportScraper
    scraper = BalanzDailyReportScraper(None)  # Sin página para test
    
    # Simular portfolio insights
    your_tickers = ['ALUA', 'COME', 'EDN', 'METR', 'TECO2']
    insights = {'tickers_mencionados': {}}
    
    text_lower = sample_report_text.lower()
    
    for ticker in your_tickers:
        if ticker.lower() in text_lower:
            # Extraer performance si está disponible
            pattern = rf'{ticker.lower()}.*?([+-]?\d+\.?\d*%)'
            matches = re.findall(pattern, text_lower)
            
            insights['tickers_mencionados'][ticker] = {
                'mencionado': True,
                'performance_reportada': matches[0] if matches else None
            }
            print(f"✅ {ticker} encontrado: {matches[0] if matches else 'Sin performance'}")
    
    print(f"\nInsights extraídos: {insights}")
    
    return True

if __name__ == "__main__":
    test_report_scraper_simple()