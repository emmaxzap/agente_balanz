# balanz_daily_report_scraper.py - Scraper para el reporte diario de Balanz
import time
from datetime import datetime, date
from typing import Dict, Optional
import re

class BalanzDailyReportScraper:
    def __init__(self, page):
        self.page = page
        self.report_url = "https://balanz.com/reportes/daily/"
    
    def get_daily_market_report(self) -> Dict:
        """Obtiene el reporte diario completo de Balanz"""
        try:
            print("📊 OBTENIENDO REPORTE DIARIO DE BALANZ...")
            print("-" * 50)
            
            # 1. Navegar al reporte
            print(f"🌐 Navegando a: {self.report_url}")
            self.page.goto(self.report_url, wait_until='networkidle')
            time.sleep(3)
            
            # 2. Buscar y expandir el reporte completo
            full_report_text = self._expand_and_extract_report()
            
            if not full_report_text:
                print("❌ No se pudo obtener el texto del reporte")
                return {}
            
            # 3. Procesar y estructurar el contenido
            structured_report = self._parse_report_content(full_report_text)
            
            # 4. Extraer insights específicos para tu cartera
            portfolio_insights = self._extract_portfolio_specific_insights(structured_report)
            
            print(f"✅ Reporte diario extraído: {len(full_report_text)} caracteres")
            print(f"📊 Secciones identificadas: {len(structured_report)}")
            
            return {
                'fecha': date.today().isoformat(),
                'timestamp': datetime.now().isoformat(),
                'full_text': full_report_text,
                'structured_content': structured_report,
                'portfolio_insights': portfolio_insights,
                'data_source': 'balanz_daily_report'
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo reporte de Balanz: {str(e)}")
            return {}
    
    def _expand_and_extract_report(self) -> str:
        """Expande el reporte y extrae el texto completo"""
        try:
            # Buscar el botón "Ver más" o "Síntesis de mercado"
            print("🔍 Buscando botón de expansión...")
            
            # Método 1: Buscar "Ver más"
            ver_mas_selectors = [
                'a:has-text("Ver más")',
                'button:has-text("Ver más")',
                '.ver-mas',
                '[class*="ver-mas"]'
            ]
            
            expand_button = None
            for selector in ver_mas_selectors:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    expand_button = elements.first
                    print(f"✅ Botón 'Ver más' encontrado: {selector}")
                    break
            
            # Método 2: Buscar "Síntesis de mercado"
            if not expand_button:
                print("🔍 Buscando botón 'Síntesis de mercado'...")
                
                sintesis_selectors = [
                    'button:has-text("Síntesis de mercado")',
                    '.btn-custom:has-text("Síntesis de mercado")',
                    '.download-report:has-text("Síntesis de mercado")'
                ]
                
                for selector in sintesis_selectors:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        expand_button = elements.first
                        print(f"✅ Botón 'Síntesis de mercado' encontrado: {selector}")
                        break
            
            # Método 3: Buscar por la estructura específica que mencionaste
            if not expand_button:
                print("🔍 Buscando por estructura específica...")
                try:
                    # <div class="py-3 row"><button type="button" id="" class="btn-custom btn btn-secondary download-report">Síntesis de mercado</button></div>
                    specific_button = self.page.locator('div.py-3.row button.btn-custom.btn.btn-secondary.download-report')
                    if specific_button.count() > 0:
                        expand_button = specific_button.first
                        print("✅ Botón encontrado por estructura específica")
                except Exception as e:
                    print(f"⚠️ Error buscando estructura específica: {str(e)}")
            
            # Si encontramos el botón, hacer click
            if expand_button:
                print("🖱️ Haciendo click para expandir reporte...")
                expand_button.click()
                time.sleep(3)  # Esperar que se expanda el contenido
                print("✅ Reporte expandido")
            else:
                print("⚠️ No se encontró botón de expansión - extrayendo contenido visible")
            
            # Extraer todo el texto del reporte
            report_text = self._extract_full_report_text()
            return report_text
            
        except Exception as e:
            print(f"❌ Error expandiendo reporte: {str(e)}")
            return ""
    
    def _extract_full_report_text(self) -> str:
        """Extrae el texto completo del reporte expandido"""
        try:
            # Buscar contenedores típicos de contenido de reportes
            content_selectors = [
                '.blnz-article',  # Estructura que viste en tus documentos
                '.article-content',
                '.report-content',
                '.daily-report',
                'article',
                '.content'
            ]
            
            report_text = ""
            
            for selector in content_selectors:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    for i in range(elements.count()):
                        element = elements.nth(i)
                        if element.is_visible():
                            text = element.text_content().strip()
                            if len(text) > 200:  # Solo contenido sustancial
                                report_text += text + "\n\n"
                                print(f"✅ Texto extraído de {selector}: {len(text)} caracteres")
            
            # Si no encontramos contenido específico, extraer de body general
            if not report_text:
                print("🔍 Extrayendo contenido general...")
                body_text = self.page.locator('body').text_content()
                
                # Filtrar para quedarnos solo con contenido relevante del reporte
                lines = body_text.split('\n')
                relevant_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Filtrar líneas que parecen contenido del reporte
                    if (len(line) > 50 and 
                        any(keyword in line.lower() for keyword in 
                            ['merval', 'renta', 'bonos', 'dólar', 'acciones', 'sector', '%']) and
                        not any(nav_word in line.lower() for nav_word in 
                               ['navegación', 'menú', 'copyright', 'cookies', 'política'])):
                        relevant_lines.append(line)
                
                report_text = '\n'.join(relevant_lines)
            
            # Limpiar texto
            report_text = self._clean_report_text(report_text)
            
            return report_text
            
        except Exception as e:
            print(f"❌ Error extrayendo texto del reporte: {str(e)}")
            return ""
    
    def _clean_report_text(self, text: str) -> str:
        """Limpia y mejora el formato del texto del reporte"""
        if not text:
            return ""
        
        # Remover elementos no deseados
        text = re.sub(r'Ver menos.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Descargar.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s+', ' ', text)  # Normalizar espacios
        
        # Mejorar formato
        text = text.replace('. ', '.\n')  # Un párrafo por oración para mejor análisis
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalizar saltos de línea
        
        return text.strip()
    
    def _parse_report_content(self, report_text: str) -> Dict:
        """Parsea el contenido del reporte en secciones estructuradas"""
        try:
            sections = {}
            
            # Identificar secciones principales basadas en el reporte que compartiste
            section_patterns = {
                'renta_variable': r'(?i)(renta variable.*?)(?=renta fija|macroeconomía|internacional|$)',
                'renta_fija_soberana': r'(?i)(renta fija soberana.*?)(?=renta fija corporativa|renta fija en pesos|$)',
                'renta_fija_corporativa': r'(?i)(renta fija corporativa.*?)(?=renta fija en pesos|tipos de cambio|$)',
                'tipos_cambio': r'(?i)(tipos de cambio.*?)(?=macroeconomía|internacional|$)',
                'macroeconomia': r'(?i)(macroeconomía.*?)(?=internacional|$)',
                'internacional': r'(?i)(internacional.*?)$'
            }
            
            for section_name, pattern in section_patterns.items():
                match = re.search(pattern, report_text, re.DOTALL)
                if match:
                    sections[section_name] = match.group(1).strip()
                    print(f"📋 Sección '{section_name}' identificada: {len(match.group(1))} caracteres")
            
            # Si no se pudieron identificar secciones, usar texto completo
            if not sections:
                sections['contenido_completo'] = report_text
                print("📋 Usando contenido completo como sección única")
            
            return sections
            
        except Exception as e:
            print(f"❌ Error parseando contenido: {str(e)}")
            return {'contenido_completo': report_text}
    
    def _extract_portfolio_specific_insights(self, structured_report: Dict) -> Dict:
        """Extrae insights específicos para tu cartera actual"""
        insights = {
            'tickers_mencionados': {},
            'sectores_destacados': {},
            'sentiment_general': 'neutral',
            'market_drivers': [],
            'risk_factors': []
        }
        
        try:
            # Tickers de tu cartera actual
            your_tickers = ['ALUA', 'COME', 'EDN', 'METR', 'TECO2']
            
            full_text = ' '.join(structured_report.values()).lower()
            
            # Buscar menciones específicas de tus activos
            for ticker in your_tickers:
                ticker_pattern = rf'{ticker.lower()}.*?([+-]?\d+\.?\d*%)'
                matches = re.findall(ticker_pattern, full_text)
                
                if matches:
                    insights['tickers_mencionados'][ticker] = {
                        'mencionado': True,
                        'performance_reportada': matches[0] if matches else None,
                        'contexto': self._extract_ticker_context(ticker, full_text)
                    }
                    print(f"📊 {ticker} mencionado en reporte: {matches[0] if matches else 'Sin performance específica'}")
            
            # Análisis de sentiment general
            positive_words = ['avanzó', 'subas', 'recuperaron', 'positivo', 'buena', 'destacadas']
            negative_words = ['retrocedió', 'bajas', 'cayó', 'negativo', 'deterioro', 'déficit']
            
            positive_count = sum(full_text.count(word) for word in positive_words)
            negative_count = sum(full_text.count(word) for word in negative_words)
            
            if positive_count > negative_count * 1.3:
                insights['sentiment_general'] = 'positivo'
            elif negative_count > positive_count * 1.3:
                insights['sentiment_general'] = 'negativo'
            else:
                insights['sentiment_general'] = 'mixto'
            
            print(f"📊 Sentiment general del reporte: {insights['sentiment_general']}")
            
            # Extraer drivers principales del mercado
            drivers = []
            if 'merval avanzó' in full_text:
                drivers.append('Merval positivo')
            if 'contexto regional positivo' in full_text:
                drivers.append('Contexto regional favorable')
            if 'bonos' in full_text and 'recuperaron' in full_text:
                drivers.append('Recuperación en bonos')
            
            insights['market_drivers'] = drivers
            
            return insights
            
        except Exception as e:
            print(f"❌ Error extrayendo insights: {str(e)}")
            return insights
    
    def _extract_ticker_context(self, ticker: str, full_text: str) -> str:
        """Extrae el contexto específico de un ticker en el reporte"""
        try:
            # Buscar oraciones que mencionen el ticker
            sentences = full_text.split('.')
            
            for sentence in sentences:
                if ticker.lower() in sentence:
                    # Limpiar y retornar la oración completa
                    clean_sentence = sentence.strip()
                    if len(clean_sentence) > 10:
                        return clean_sentence[:200] + "..." if len(clean_sentence) > 200 else clean_sentence
            
            return "Mencionado sin contexto específico"
            
        except Exception as e:
            return f"Error extrayendo contexto: {str(e)}"
    
    def generate_enhanced_prompt_with_report(self, portfolio_data: Dict, report_data: Dict) -> str:
        """Genera prompt enriquecido con el reporte diario"""
        if not report_data:
            return ""
        
        enhanced_prompt = f"""CONTEXTO DE MERCADO ACTUAL (Reporte Balanz de hoy):

ANÁLISIS DIARIO DE BALANZ - {report_data.get('fecha', 'N/A')}:
{'-' * 60}

"""
        
        # Agregar secciones del reporte
        structured_content = report_data.get('structured_content', {})
        
        if 'renta_variable' in structured_content:
            enhanced_prompt += f"RENTA VARIABLE:\n{structured_content['renta_variable']}\n\n"
        
        if 'tipos_cambio' in structured_content:
            enhanced_prompt += f"TIPOS DE CAMBIO:\n{structured_content['tipos_cambio']}\n\n"
        
        if 'macroeconomia' in structured_content:
            enhanced_prompt += f"MACROECONOMÍA:\n{structured_content['macroeconomia']}\n\n"
        
        # Insights específicos para tu cartera
        portfolio_insights = report_data.get('portfolio_insights', {})
        
        if portfolio_insights.get('tickers_mencionados'):
            enhanced_prompt += "IMPACTO EN TU CARTERA:\n"
            enhanced_prompt += "-" * 30 + "\n"
            
            for ticker, info in portfolio_insights['tickers_mencionados'].items():
                if info['mencionado']:
                    performance = info.get('performance_reportada', 'N/A')
                    contexto = info.get('contexto', 'Sin contexto')
                    enhanced_prompt += f"• {ticker}: {performance} - {contexto}\n"
            
            enhanced_prompt += "\n"
        
        enhanced_prompt += f"SENTIMENT GENERAL DEL MERCADO: {portfolio_insights.get('sentiment_general', 'neutral').upper()}\n"
        enhanced_prompt += f"DRIVERS PRINCIPALES: {', '.join(portfolio_insights.get('market_drivers', []))}\n\n"
        
        enhanced_prompt += """INSTRUCCIONES:
Usa este contexto de mercado REAL de hoy para:
1. Ajustar tus recomendaciones técnicas según el ambiente actual
2. Considerar el sentiment general del mercado argentino
3. Tomar en cuenta menciones específicas de activos de la cartera
4. Evaluar si el contexto regional/internacional afecta tus decisiones

"""
        
        return enhanced_prompt
    
    def save_report_to_db(self, report_data: Dict, db_manager) -> bool:
        """Guarda el reporte en la base de datos"""
        try:
            if not report_data or not db_manager:
                return False
            
            report_record = {
                'fecha': report_data['fecha'],
                'full_text': report_data['full_text'][:2000],  # Limitar tamaño
                'sentiment_general': report_data['portfolio_insights'].get('sentiment_general', 'neutral'),
                'tickers_mencionados': list(report_data['portfolio_insights'].get('tickers_mencionados', {}).keys()),
                'market_drivers': report_data['portfolio_insights'].get('market_drivers', []),
                'sections_count': len(report_data.get('structured_content', {})),
                'data_quality': 'complete' if len(report_data['full_text']) > 1000 else 'partial'
            }
            
            # Crear tabla si no existe
            # CREATE TABLE daily_reports (
            #     id SERIAL PRIMARY KEY,
            #     fecha DATE NOT NULL UNIQUE,
            #     full_text TEXT,
            #     sentiment_general VARCHAR(20),
            #     tickers_mencionados TEXT[],
            #     market_drivers TEXT[],
            #     sections_count INTEGER,
            #     data_quality VARCHAR(20),
            #     created_at TIMESTAMP DEFAULT NOW()
            # );
            
            result = db_manager.supabase.table('daily_reports').upsert(report_record).execute()
            
            print("✅ Reporte diario guardado en BD")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando reporte: {str(e)}")
            return False

# INTEGRACIÓN CON TU ANÁLISIS EXISTENTE
class EnhancedPortfolioAnalyzerWithReport:
    def __init__(self, page, db_manager):
        self.page = page
        self.db = db_manager
        self.report_scraper = BalanzDailyReportScraper(page)
    
    def run_enhanced_analysis_with_market_context(self, portfolio_data: Dict) -> Dict:
        """Ejecuta análisis enriquecido con contexto del reporte diario"""
        try:
            print("🚀 ANÁLISIS ENRIQUECIDO CON REPORTE DE MERCADO")
            print("=" * 60)
            
            # 1. Obtener reporte diario actual
            daily_report = self.report_scraper.get_daily_market_report()
            
            # 2. Tu análisis técnico existente
            from claude_portfolio_agent import ClaudePortfolioAgent
            claude_agent = ClaudePortfolioAgent(self.db, self.page)
            
            # 3. Generar análisis con contexto de mercado
            if daily_report:
                print("📊 Integrando reporte de mercado con análisis técnico...")
                
                # Crear prompt enriquecido
                market_context_prompt = self.report_scraper.generate_enhanced_prompt_with_report(
                    portfolio_data, daily_report
                )
                
                # Agregar el contexto al análisis
                enhanced_analysis = self._run_claude_analysis_with_market_context(
                    claude_agent, portfolio_data, market_context_prompt
                )
                
                return {
                    'base_analysis': enhanced_analysis,
                    'market_report': daily_report,
                    'enhanced_with_market_context': True,
                    'context_quality': 'high'
                }
            else:
                print("⚠️ Sin reporte de mercado - usando análisis estándar")
                standard_analysis = claude_agent.analyze_portfolio_with_expert_agent(
                    portfolio_data, portfolio_data.get('dinero_disponible', 0)
                )
                
                return {
                    'base_analysis': standard_analysis,
                    'market_report': {},
                    'enhanced_with_market_context': False,
                    'context_quality': 'standard'
                }
                
        except Exception as e:
            print(f"❌ Error en análisis enriquecido: {str(e)}")
            return {}
    
    def _run_claude_analysis_with_market_context(self, claude_agent, portfolio_data: Dict, market_context: str) -> Dict:
        """Ejecuta Claude con contexto de mercado adicional"""
        try:
            # Modificar temporalmente el prompt de Claude para incluir contexto
            original_method = claude_agent._create_expert_prompt_improved
            
            def enhanced_prompt_method(data):
                original_prompt = original_method(data)
                return market_context + "\n\n" + original_prompt
            
            # Reemplazar método temporalmente
            claude_agent._create_expert_prompt_improved = enhanced_prompt_method
            
            # Ejecutar análisis con contexto
            enhanced_analysis = claude_agent.analyze_portfolio_with_expert_agent(
                portfolio_data, portfolio_data.get('dinero_disponible', 0)
            )
            
            # Restaurar método original
            claude_agent._create_expert_prompt_improved = original_method
            
            return enhanced_analysis
            
        except Exception as e:
            print(f"❌ Error ejecutando análisis con contexto: {str(e)}")
            return {}

# FUNCIÓN DE TESTING
def test_balanz_report_scraper():
    """Función para probar el scraper del reporte"""
    print("🧪 PROBANDO SCRAPER DE REPORTE BALANZ")
    print("=" * 50)
    
    # Necesitarías una instancia de página de Playwright
    print("⚠️ Para probar necesitas:")
    print("1. Una sesión activa de Playwright")
    print("2. Modificar tu main.py para incluir este scraper")
    print("3. O crear un script independiente con navegador")
    
    print("\n💡 IMPLEMENTACIÓN SUGERIDA:")
    print("Agregar al final de tu login exitoso en main.py:")
    print("""
    # Después del login exitoso
    from balanz_daily_report_scraper import BalanzDailyReportScraper
    
    report_scraper = BalanzDailyReportScraper(scraper.page)
    daily_report = report_scraper.get_daily_market_report()
    
    # Usar en tu análisis
    if daily_report:
        print("✅ Reporte de mercado obtenido - análisis mejorado")
    """)

if __name__ == "__main__":
    test_balanz_report_scraper()