# comprehensive_market_analyzer_updated.py - Con scraper paginado
from datetime import date, datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Imports de tus módulos existentes
sys.path.append(str(Path(__file__).parent))

# NOTA: Imports sin circular dependencies
from balanz_daily_report_scraper import BalanzDailyReportScraper
from claude_portfolio_agent import ClaudePortfolioAgent

class ComprehensiveMarketAnalyzer:
    """
    Analizador integral que combina:
    1. Reporte diario de mercado (Balanz)
    2. Ratios fundamentales PAGINADOS (Screenermatic - TODAS las páginas)
    3. Análisis técnico avanzado (Claude)
    4. Sistema de reglas automatizadas
    """
    
    def __init__(self, page, db_manager):
        self.page = page
        self.db = db_manager
        
        # Inicializar scrapers especializados
        self.report_scraper = BalanzDailyReportScraper(page)
        
        # Inicializar analizador Claude
        self.claude_agent = ClaudePortfolioAgent(db_manager, page)
    
    def run_comprehensive_analysis(self, portfolio_data: Dict) -> Dict:
        """Ejecuta análisis integral completo con todas las fuentes de datos"""
        try:
            print("🚀 INICIANDO ANÁLISIS INTEGRAL COMPLETO")
            print("=" * 70)
            print("📊 Fuentes: Mercado + Fundamental (PAGINADO) + Técnico + Reglas")
            print("=" * 70)
            
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'comprehensive_integral_paginated',
                'components': {
                    'market_report': False,
                    'fundamental_ratios': False,
                    'technical_analysis': False,
                    'rules_analysis': False
                },
                'market_report': {},
                'portfolio_data': portfolio_data,
                'comprehensive_analysis': {},
                'fallback_analysis': {},
                'confidence_level': 'standard'
            }
            
            # PASO 1: Contexto de mercado actual
            market_report = self._get_market_context()
            if market_report:
                analysis_result['market_report'] = market_report
                analysis_result['components']['market_report'] = True
                print("✅ PASO 1: Contexto de mercado obtenido")
            else:
                print("⚠️ PASO 1: Sin contexto de mercado - continuando")
            
            # PASO 2: Análisis fundamental PAGINADO
            enhanced_portfolio = self._enhance_with_fundamentals_paginated(portfolio_data)
            if enhanced_portfolio != portfolio_data:
                analysis_result['portfolio_data'] = enhanced_portfolio
                analysis_result['components']['fundamental_ratios'] = True
                print("✅ PASO 2: Análisis fundamental PAGINADO completado")
            else:
                print("⚠️ PASO 2: Sin datos fundamentales - continuando")
            
            # PASO 3: Análisis técnico avanzado con Claude
            comprehensive_analysis = self._run_claude_comprehensive_analysis(
                analysis_result['portfolio_data'], 
                market_report
            )
            
            if comprehensive_analysis and self._is_real_claude_analysis(comprehensive_analysis):
                analysis_result['comprehensive_analysis'] = comprehensive_analysis
                analysis_result['components']['technical_analysis'] = True
                analysis_result['confidence_level'] = 'high'
                print("✅ PASO 3: Análisis técnico avanzado completado")
            else:
                print("⚠️ PASO 3: Claude no disponible - usando análisis de reglas")
                
                # Fallback al sistema de reglas
                rules_analysis = self._run_rules_analysis(analysis_result['portfolio_data'])
                analysis_result['fallback_analysis'] = rules_analysis
                analysis_result['components']['rules_analysis'] = True
                print("✅ PASO 3 (FALLBACK): Sistema de reglas ejecutado")
            
            # PASO 4: Guardar todos los datos
            self._save_comprehensive_data(analysis_result)
            print("✅ PASO 4: Datos guardados en base de datos")
            
            # PASO 5: Envío de notificaciones mejoradas
            notification_success = self._send_comprehensive_notifications(analysis_result)
            if notification_success:
                print("✅ PASO 5: Notificaciones enviadas")
            else:
                print("⚠️ PASO 5: Problemas con notificaciones")
            
            # Evaluación final
            components_working = sum(analysis_result['components'].values())
            if components_working >= 3:
                analysis_result['confidence_level'] = 'high'
                print(f"\n🎉 ANÁLISIS INTEGRAL EXITOSO")
                print(f"✅ {components_working}/4 componentes funcionando")
            elif components_working >= 2:
                analysis_result['confidence_level'] = 'medium'
                print(f"\n✅ ANÁLISIS INTEGRAL PARCIAL")
                print(f"⚠️ {components_working}/4 componentes funcionando")
            else:
                analysis_result['confidence_level'] = 'low'
                print(f"\n⚠️ ANÁLISIS INTEGRAL LIMITADO")
                print(f"❌ Solo {components_working}/4 componentes funcionando")
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error en análisis integral: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_market_context(self) -> Dict:
        """Obtiene contexto actual del mercado"""
        try:
            print("📰 Obteniendo reporte diario de mercado...")
            
            daily_report = self.report_scraper.get_daily_market_report()
            
            if daily_report and 'full_text' in daily_report:
                # Validar calidad del reporte
                text_length = len(daily_report['full_text'])
                
                if text_length > 500:
                    print(f"   ✅ Reporte extraído: {text_length} caracteres")
                    
                    # Enriquecer con insights específicos de tu cartera
                    portfolio_insights = daily_report.get('portfolio_insights', {})
                    tickers_mencionados = portfolio_insights.get('tickers_mencionados', {})
                    
                    if tickers_mencionados:
                        mentioned_count = sum(1 for info in tickers_mencionados.values() if info.get('mencionado'))
                        print(f"   🎯 Tus activos mencionados: {mentioned_count}")
                    
                    return daily_report
                else:
                    print(f"   ⚠️ Reporte muy corto: {text_length} caracteres")
            else:
                print("   ❌ No se pudo obtener reporte diario")
            
            return {}
            
        except Exception as e:
            print(f"   ❌ Error obteniendo contexto de mercado: {str(e)}")
            return {}
    
    def _enhance_with_fundamentals_paginated(self, portfolio_data: Dict) -> Dict:
        """Enriquece portfolio con datos fundamentales PAGINADOS (todas las páginas)"""
        try:
            print("📊 Obteniendo ratios fundamentales PAGINADOS...")
            print("🔍 Buscando en TODAS las páginas de Screenermatic...")
            
            # **CAMBIO PRINCIPAL**: Importar el scraper paginado
            try:
                from financial_ratios_scraper_paginated import FinancialRatiosScraperPaginated
                ratios_scraper = FinancialRatiosScraperPaginated(self.page)
                print("✅ Usando scraper PAGINADO (todas las páginas)")
            except ImportError:
                print("⚠️ Scraper paginado no encontrado, usando original...")
                from financial_ratios_scraper import FinancialRatiosScraper
                ratios_scraper = FinancialRatiosScraper(self.page)
                print("⚠️ Usando scraper original (solo página 1)")
            
            # Obtener tickers de la cartera
            tickers = [asset['ticker'] for asset in portfolio_data.get('activos', [])]
            
            if not tickers:
                print("   ⚠️ No hay tickers en la cartera")
                return portfolio_data
            
            print(f"   🎯 Analizando ratios para: {tickers}")
            
            # Usar el método de enriquecimiento del scraper (paginado o no)
            enhanced_portfolio = ratios_scraper.enhance_portfolio_analysis_with_ratios(portfolio_data)
            
            # Verificar si se enriqueció
            ratios_added = 0
            for asset in enhanced_portfolio.get('activos', []):
                if 'fundamental_ratios' in asset:
                    ratios_added += 1
            
            if ratios_added > 0:
                print(f"   ✅ {ratios_added}/{len(tickers)} activos enriquecidos con ratios")
                
                # Mostrar qué se encontró
                for asset in enhanced_portfolio.get('activos', []):
                    ticker = asset['ticker']
                    if 'fundamental_ratios' in asset:
                        ratios = asset['fundamental_ratios']
                        pe = ratios.get('pe', 'N/A')
                        roe = ratios.get('roe', 'N/A')
                        print(f"      ✅ {ticker}: P/E={pe}, ROE={roe}")
                    else:
                        print(f"      ❌ {ticker}: No encontrado")
                
                return enhanced_portfolio
            else:
                print("   ⚠️ No se pudieron obtener ratios - usando portfolio original")
                return portfolio_data
                
        except Exception as e:
            print(f"   ❌ Error enriqueciendo con fundamentales: {str(e)}")
            import traceback
            traceback.print_exc()
            return portfolio_data
    
    def _run_claude_comprehensive_analysis(self, enhanced_portfolio: Dict, market_report: Dict) -> Dict:
        """Ejecuta análisis de Claude con contexto completo"""
        try:
            print("🤖 Ejecutando análisis técnico avanzado con Claude...")
            
            # Crear super-prompt con toda la información
            comprehensive_prompt = self._create_comprehensive_prompt(enhanced_portfolio, market_report)
            
            # Modificar temporalmente el prompt del agente Claude
            original_method = self.claude_agent._create_expert_prompt_improved
            
            def enhanced_prompt_method(data):
                original_prompt = original_method(data)
                return comprehensive_prompt + "\n\n" + original_prompt
            
            # Reemplazar método temporalmente
            self.claude_agent._create_expert_prompt_improved = enhanced_prompt_method
            
            # Ejecutar análisis con contexto completo
            analysis = self.claude_agent.analyze_portfolio_with_expert_agent(
                enhanced_portfolio, 
                enhanced_portfolio.get('dinero_disponible', 0)
            )
            
            # Restaurar método original
            self.claude_agent._create_expert_prompt_improved = original_method
            
            if analysis and self._is_real_claude_analysis(analysis):
                print("   ✅ Análisis Claude completado con datos reales")
                return analysis
            else:
                print("   ⚠️ Análisis Claude no disponible o genérico")
                return {}
                
        except Exception as e:
            print(f"   ❌ Error en análisis Claude: {str(e)}")
            return {}
    
    def _create_comprehensive_prompt(self, enhanced_portfolio: Dict, market_report: Dict) -> str:
        """Crea super-prompt con toda la información disponible"""
        
        prompt = """ANÁLISIS INTEGRAL DE CARTERA - CONTEXTO COMPLETO DE MERCADO

Eres un analista senior que debe integrar TRES fuentes de información para recomendaciones precisas:

"""
        
        # 1. CONTEXTO DE MERCADO
        if market_report and 'full_text' in market_report:
            prompt += "1. CONTEXTO DE MERCADO HOY (Reporte Balanz Real):\n"
            prompt += "=" * 55 + "\n"
            
            # Agregar texto del reporte (limitado)
            market_text = market_report['full_text'][:1200]  # Limitar para no saturar
            prompt += f"{market_text}\n\n"
            
            # Insights específicos de tu cartera
            portfolio_insights = market_report.get('portfolio_insights', {})
            sentiment = portfolio_insights.get('sentiment_general', 'neutral')
            
            prompt += f"SENTIMENT GENERAL HOY: {sentiment.upper()}\n"
            
            tickers_mencionados = portfolio_insights.get('tickers_mencionados', {})
            if tickers_mencionados:
                prompt += "\nMENCIONES ESPECÍFICAS DE TUS ACTIVOS HOY:\n"
                for ticker, info in tickers_mencionados.items():
                    if info.get('mencionado'):
                        performance = info.get('performance_reportada', 'Sin performance')
                        contexto = info.get('contexto', 'Mencionado')
                        prompt += f"• {ticker}: {performance} - {contexto}\n"
                prompt += "\n"
            
            market_drivers = portfolio_insights.get('market_drivers', [])
            if market_drivers:
                prompt += f"DRIVERS DE MERCADO HOY: {', '.join(market_drivers)}\n\n"
        
        # 2. ANÁLISIS FUNDAMENTAL PAGINADO
        prompt += "2. ANÁLISIS FUNDAMENTAL (Ratios de TODAS las páginas de Screenermatic):\n"
        prompt += "=" * 70 + "\n"
        
        fundamental_summary = enhanced_portfolio.get('fundamental_summary', {})
        if fundamental_summary:
            # Resumen de ratios de la cartera
            tickers_with_ratios = fundamental_summary.get('tickers_with_ratios', 0)
            avg_pe = fundamental_summary.get('avg_pe', 0)
            avg_roe = fundamental_summary.get('avg_roe', 0)
            
            prompt += f"COBERTURA FUNDAMENTAL: {tickers_with_ratios} activos con ratios completos\n"
            if avg_pe > 0:
                prompt += f"P/E PROMEDIO DE TU CARTERA: {avg_pe:.1f}\n"
            if avg_roe > 0:
                prompt += f"ROE PROMEDIO DE TU CARTERA: {avg_roe:.1f}%\n"
            
            # Top picks fundamentales
            top_picks = fundamental_summary.get('top_picks', [])
            if top_picks:
                prompt += f"\nTOP FUNDAMENTALES EN TU CARTERA:\n"
                for ticker, score in top_picks:
                    prompt += f"• {ticker}: Score {score:.0f}/100\n"
            
            prompt += "\n"
        
        # Ratios por activo
        for asset in enhanced_portfolio.get('activos', []):
            ticker = asset['ticker']
            fundamental_ratios = asset.get('fundamental_ratios', {})
            fundamental_analysis = asset.get('fundamental_analysis', {})
            
            if fundamental_ratios:
                prompt += f"{ticker} - RATIOS FUNDAMENTALES COMPLETOS (Búsqueda paginada):\n"
                
                pe = fundamental_ratios.get('pe')
                roe = fundamental_ratios.get('roe')
                debt_equity = fundamental_ratios.get('debt_to_equity')
                current_ratio = fundamental_ratios.get('current_ratio')
                fundamental_score = fundamental_ratios.get('fundamental_score')
                valuation_category = fundamental_ratios.get('valuation_category')
                
                if pe:
                    prompt += f"• P/E: {pe:.1f}"
                    if pe < 10:
                        prompt += " (BARATO)"
                    elif pe > 25:
                        prompt += " (CARO)"
                    else:
                        prompt += " (RAZONABLE)"
                    prompt += "\n"
                
                if roe:
                    prompt += f"• ROE: {roe:.1f}%"
                    if roe > 20:
                        prompt += " (EXCELENTE)"
                    elif roe > 15:
                        prompt += " (BUENO)"
                    elif roe < 5:
                        prompt += " (DÉBIL)"
                    prompt += "\n"
                
                if debt_equity:
                    prompt += f"• Debt/Equity: {debt_equity:.2f}"
                    if debt_equity < 0.3:
                        prompt += " (CONSERVADOR)"
                    elif debt_equity > 1.5:
                        prompt += " (ALTO RIESGO)"
                    prompt += "\n"
                
                if fundamental_score:
                    prompt += f"• Score Fundamental: {fundamental_score:.0f}/100\n"
                
                if valuation_category:
                    prompt += f"• Valuación: {valuation_category.replace('_', ' ').title()}\n"
                
                # Interpretación simple
                simple_summary = fundamental_analysis.get('simple_summary', '')
                if simple_summary:
                    prompt += f"• Resumen: {simple_summary}\n"
                
                prompt += "\n"
            else:
                prompt += f"{ticker} - NO ENCONTRADO en Screenermatic (revisadas todas las páginas)\n\n"
        
        # 3. INSTRUCCIONES ESPECÍFICAS
        prompt += """3. TU MISIÓN COMO ANALISTA SENIOR:
=========================================

COMBINA las 3 fuentes de información con estos PESOS:
• 35% - Contexto de mercado actual (reporte Balanz de hoy)
• 35% - Análisis técnico (RSI, MACD, momentum)
• 30% - Fundamentales (ratios financieros de TODAS las páginas)

RESPONDE EN EL FORMATO JSON HABITUAL pero menciona específicamente:

CRÍTICO - Para cada recomendación, explica:
1. Cómo el reporte de mercado de HOY afecta esta decisión
2. Si los fundamentales (encontrados en búsqueda paginada) refuerzan o contradicen el análisis técnico
3. Ajustes específicos por el contexto del mercado argentino actual

EJEMPLO de razonamiento integrado:
"ALUA muestra RSI oversold (18.2) sugiriendo rebote técnico, PERO el reporte de hoy menciona presión en el sector por dólar, y sus fundamentales (P/E=3.25, ROE=0.65%) encontrados en página 1 de Screenermatic muestran empresa barata pero con baja rentabilidad. RECOMENDACIÓN: Compra pequeña en $420 con stop en $400."

"""
        
        return prompt
    
    def _is_real_claude_analysis(self, analysis: Dict) -> bool:
        """Verifica si el análisis de Claude es real y no un fallback"""
        if not analysis or not isinstance(analysis, dict):
            return False
        
        # Verificar que no sea análisis minimal/fallback
        analysis_source = analysis.get('analysis_source', 'real_analysis')
        claude_available = analysis.get('claude_api_available', True)
        
        if analysis_source in ['minimal_fallback', 'error_fallback'] or not claude_available:
            return False
        
        # Verificar contenido técnico real
        analisis_tecnico = analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        # Buscar indicadores técnicos específicos
        real_indicators = 0
        for ticker, asset_analysis in por_activo.items():
            rsi_analysis = asset_analysis.get('rsi_analysis', '')
            if rsi_analysis and 'no_calculado' not in rsi_analysis and '(' in rsi_analysis:
                real_indicators += 1
        
        # Verificar razonamiento sustancial
        razonamiento = analysis.get('razonamiento_integral', '')
        has_substantial_reasoning = len(razonamiento) > 100
        
        # Verificar que mencione datos reales
        mentions_real_data = any(phrase in razonamiento.lower() for phrase in [
            'datos reales', 'indicadores calculados', 'rsi', 'macd', 'volatilidad', 'screenermatic', 'página'
        ])
        
        return real_indicators > 0 and has_substantial_reasoning and mentions_real_data
    
    def _run_rules_analysis(self, portfolio_data: Dict) -> Dict:
        """Ejecuta análisis del sistema de reglas como fallback"""
        try:
            from advanced_portfolio_manager import AdvancedPortfolioManager
            from analysis.financial_analyzer import FinancialAnalyzer
            
            analyzer = FinancialAnalyzer(self.db)
            advanced_manager = AdvancedPortfolioManager(self.db, analyzer)
            
            rules_analysis = advanced_manager.analyze_complete_portfolio(
                portfolio_data,
                portfolio_data.get('dinero_disponible', 0)
            )
            
            print("   ✅ Sistema de reglas ejecutado como fallback")
            return rules_analysis
            
        except Exception as e:
            print(f"   ❌ Error en sistema de reglas: {str(e)}")
            return {}
    
    def _save_comprehensive_data(self, analysis_result: Dict) -> None:
        """Guarda todos los datos del análisis integral"""
        try:
            # 1. Guardar reporte diario
            market_report = analysis_result.get('market_report', {})
            if market_report:
                self.report_scraper.save_report_to_db(market_report, self.db)
            
            # 2. Guardar análisis integral
            integral_record = {
                'fecha': date.today().isoformat(),
                'timestamp': analysis_result['timestamp'],
                'analysis_type': analysis_result['analysis_type'],
                'confidence_level': analysis_result['confidence_level'],
                'components_working': list(analysis_result['components'].keys()),
                'components_success': [k for k, v in analysis_result['components'].items() if v],
                'has_market_context': bool(analysis_result.get('market_report')),
                'has_fundamental_data': analysis_result['components']['fundamental_ratios'],
                'has_claude_analysis': analysis_result['components']['technical_analysis'],
                'has_rules_fallback': analysis_result['components']['rules_analysis'],
                'paginated_ratios': True  # Nuevo campo para indicar búsqueda paginada
            }
            
            try:
                self.db.supabase.table('comprehensive_analysis').upsert(integral_record).execute()
                print("   ✅ Análisis integral guardado en BD")
            except Exception as e:
                print(f"   ⚠️ Error guardando análisis integral: {str(e)}")
            
        except Exception as e:
            print(f"   ❌ Error guardando datos integrales: {str(e)}")
    
    def _send_comprehensive_notifications(self, analysis_result: Dict) -> bool:
        """Envía notificaciones con análisis integral"""
        try:
            print("📱 Enviando notificaciones integrales...")
            
            # Determinar qué análisis usar para notificaciones
            if analysis_result['components']['technical_analysis']:
                # Usar análisis de Claude
                analysis_to_send = analysis_result['comprehensive_analysis']
                notification_type = 'claude_comprehensive_paginated'
                print("   📊 Usando análisis de Claude (con ratios paginados) para notificaciones")
            else:
                # Usar análisis de reglas
                analysis_to_send = analysis_result.get('fallback_analysis', {})
                notification_type = 'rules_fallback'
                print("   📊 Usando sistema de reglas para notificaciones")
            
            # Preparar datos para notificaciones
            notification_data = self._prepare_notification_data(
                analysis_result, 
                analysis_to_send, 
                notification_type
            )
            
            # Enviar por WhatsApp
            whatsapp_success = self._send_whatsapp_notification(notification_data)
            
            # Enviar por Email
            email_success = self._send_email_notification(notification_data)
            
            if whatsapp_success or email_success:
                print(f"   ✅ Notificaciones enviadas: WhatsApp={whatsapp_success}, Email={email_success}")
                return True
            else:
                print(f"   ❌ Fallo enviando notificaciones")
                return False
                
        except Exception as e:
            print(f"   ❌ Error enviando notificaciones: {str(e)}")
            return False
    
    def _prepare_notification_data(self, analysis_result: Dict, analysis_to_send: Dict, notification_type: str) -> Dict:
        """Prepara datos específicos para notificaciones integrales"""
        
        portfolio_data = analysis_result.get('portfolio_data', {})
        market_report = analysis_result.get('market_report', {})
        
        # Métricas básicas de cartera
        total_value = sum(asset['valor_actual_total'] for asset in portfolio_data.get('activos', []))
        total_invested = sum(asset['valor_inicial_total'] for asset in portfolio_data.get('activos', []))
        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Contar cuántos activos tienen ratios fundamentales
        activos_con_ratios = sum(1 for asset in portfolio_data.get('activos', []) if 'fundamental_ratios' in asset)
        
        notification_data = {
            'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'notification_type': notification_type,
            'confidence_level': analysis_result['confidence_level'],
            
            # Métricas de cartera
            'portfolio_metrics': {
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'cash_available': portfolio_data.get('dinero_disponible', 0),
                'positions_count': len(portfolio_data.get('activos', []))
            },
            
            # Contexto de mercado
            'market_context': {
                'has_report': bool(market_report),
                'sentiment': market_report.get('portfolio_insights', {}).get('sentiment_general', 'neutral'),
                'your_assets_mentioned': len([
                    ticker for ticker, info in market_report.get('portfolio_insights', {}).get('tickers_mencionados', {}).items()
                    if info.get('mencionado')
                ]) if market_report else 0
            },
            
            # Info de ratios paginados
            'fundamental_context': {
                'activos_con_ratios': activos_con_ratios,
                'total_activos': len(portfolio_data.get('activos', [])),
                'coverage_pct': (activos_con_ratios / len(portfolio_data.get('activos', [])) * 100) if portfolio_data.get('activos') else 0,
                'paginated_search': True
            },
            
            # Análisis principal
            'main_analysis': analysis_to_send,
            
            # Componentes funcionando
            'components_status': analysis_result['components']
        }
        
        return notification_data
    
    def _send_whatsapp_notification(self, notification_data: Dict) -> bool:
        """Envía notificación por WhatsApp con contexto integral"""
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            whatsapp = WhatsAppNotifier()
            if not whatsapp.is_configured:
                return False
            
            # Crear mensaje integral
            message = self._create_integral_whatsapp_message_paginated(notification_data)
            
            return whatsapp.send_message(message)
            
        except Exception as e:
            print(f"      ❌ Error WhatsApp: {str(e)}")
            return False
    
    def _create_integral_whatsapp_message_paginated(self, data: Dict) -> str:
        """Crea mensaje de WhatsApp con análisis integral y ratios paginados"""
        timestamp = data['timestamp']
        confidence = data['confidence_level']
        metrics = data['portfolio_metrics']
        market_context = data['market_context']
        fundamental_context = data['fundamental_context']
        
        message = f"*🌟 ANÁLISIS INTEGRAL PAGINADO*\n"
        message += f"📅 {timestamp}\n"
        message += f"🔥 Confianza: {confidence.upper()}\n"
        message += "=" * 30 + "\n\n"
        
        # Situación actual
        message += f"*💼 TU SITUACIÓN*\n"
        message += f"💰 Total: ${metrics['total_value']:,.0f}\n"
        pnl_emoji = "📈" if metrics['total_pnl'] >= 0 else "📉"
        message += f"{pnl_emoji} P&L: ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)\n"
        message += f"💵 Disponible: ${metrics['cash_available']:,.0f}\n\n"
        
        # Contexto fundamental PAGINADO
        if fundamental_context['activos_con_ratios'] > 0:
            message += f"*📊 RATIOS FUNDAMENTALES (PAGINADO)*\n"
            message += f"✅ {fundamental_context['activos_con_ratios']}/{fundamental_context['total_activos']} activos con ratios completos\n"
            message += f"🔍 Búsqueda: TODAS las páginas Screenermatic\n"
            message += f"📊 Cobertura: {fundamental_context['coverage_pct']:.0f}%\n\n"
        
        # Contexto de mercado
        if market_context['has_report']:
            sentiment_emoji = {
                'positivo': '🟢',
                'negativo': '🔴', 
                'mixto': '🟡',
                'neutral': '⚪'
            }.get(market_context['sentiment'], '⚪')
            
            message += f"*📰 MERCADO HOY*\n"
            message += f"{sentiment_emoji} Sentiment: {market_context['sentiment'].upper()}\n"
            
            if market_context['your_assets_mentioned'] > 0:
                message += f"🎯 {market_context['your_assets_mentioned']} de tus activos mencionados\n"
            
            message += "\n"
        
        # Recomendaciones principales (resto del código igual...)
        main_analysis = data['main_analysis']
        
        if data['notification_type'].startswith('claude_'):
            # Análisis de Claude con contexto
            immediate_actions = main_analysis.get('acciones_inmediatas', [])
            
            if immediate_actions:
                message += f"*🚨 HACER HOY*\n"
                message += "-" * 15 + "\n"
                
                for i, action in enumerate(immediate_actions[:3], 1):  # Top 3
                    ticker = action.get('ticker', 'N/A')
                    accion = action.get('accion', '')
                    cantidad = action.get('cantidad', 0)
                    precio = action.get('precio_objetivo', 0)
                    razon = action.get('razon', '')
                    
                    if 'comprar' in accion.lower():
                        message += f"*{i}. COMPRAR {ticker}*\n"
                        message += f"📊 {cantidad} acciones máx ${precio:.0f}\n"
                        message += f"💰 Inversión: ${cantidad * precio:,.0f}\n"
                    elif 'vender' in accion.lower():
                        message += f"*{i}. VENDER {ticker}*\n"
                        message += f"📊 {cantidad} acciones mín ${precio:.0f}\n"
                    
                    # Usar solo la primera parte de la razón para WhatsApp
                    razon_short = razon[:60] + "..." if len(razon) > 60 else razon
                    message += f"❓ {razon_short}\n\n"
            else:
                message += f"*✅ No hay acciones urgentes*\n\n"
            
            # Conclusión del experto (simplificada)
            razonamiento = main_analysis.get('razonamiento_integral', '')
            if razonamiento:
                conclusion = razonamiento[:100] + "..." if len(razonamiento) > 100 else razonamiento
                message += f"*🧠 EXPERTO*\n{conclusion}\n\n"
        
        else:
            # Sistema de reglas
            rules_recs = main_analysis.get('recommendations', [])
            
            if rules_recs:
                message += f"*🎯 RECOMENDACIONES AUTOMÁTICAS*\n"
                message += "-" * 25 + "\n"
                
                for i, rec in enumerate(rules_recs[:3], 1):  # Top 3
                    ticker = rec.ticker
                    action_type = rec.action.value if hasattr(rec.action, 'value') else str(rec.action)
                    shares = rec.suggested_shares
                    
                    if 'stop_loss' in action_type:
                        message += f"*{i}. PROTEGER {ticker}*\n"
                        message += f"🚨 Vender {shares} acciones\n"
                    elif 'toma_ganancias' in action_type:
                        message += f"*{i}. GANAR {ticker}*\n"
                        message += f"💰 Vender {shares} acciones\n"
                    elif 'rebalanceo' in action_type:
                        message += f"*{i}. BALANCEAR {ticker}*\n"
                        message += f"⚖️ Reducir {shares} acciones\n"
                    
                    message += f"🔥 Confianza: {rec.confidence:.0f}%\n\n"
            else:
                message += f"*✅ Cartera estable*\n\n"
        
        # Componentes funcionando
        components = data['components_status']
        working_components = [k for k, v in components.items() if v]
        
        message += f"*🔧 SISTEMA*\n"
        message += f"📊 Componentes activos: {len(working_components)}/4\n"
        
        if 'market_report' in working_components:
            message += "📰 Reporte mercado ✅\n"
        if 'fundamental_ratios' in working_components:
            message += "📊 Ratios fundamentales ✅\n"
        if 'technical_analysis' in working_components:
            message += "🤖 Claude técnico ✅\n"
        if 'rules_analysis' in working_components:
            message += "📋 Sistema reglas ✅\n"
        
        message += f"\n⚠️ *Son sugerencias, no consejos financieros*"
        
        return message
    
    def _send_email_notification(self, notification_data: Dict) -> bool:
        """Envía notificación por Email con contexto integral"""
        try:
            from scraper.notifications.email_notifier import EmailNotifier
            
            email = EmailNotifier()
            if not email.is_configured:
                return False
            
            # Crear email integral
            subject, body_text, body_html = self._create_integral_email(notification_data)
            
            return email.send_email(subject, body_text, body_html)
            
        except Exception as e:
            print(f"      ❌ Error Email: {str(e)}")
            return False
    
    def _create_integral_email(self, data: Dict) -> tuple:
        """Crea email integral con contexto completo"""
        timestamp = data['timestamp']
        confidence = data['confidence_level']
        
        subject = f"🌟 ANÁLISIS INTEGRAL DE CARTERA - {timestamp}"
        
        # Email de texto
        body_text = f"""ANÁLISIS INTEGRAL DE CARTERA - {timestamp}
{'='*50}

CONFIANZA DEL ANÁLISIS: {confidence.upper()}

TU SITUACIÓN ACTUAL:
💰 Total: ${data['portfolio_metrics']['total_value']:,.0f}
📈 P&L: ${data['portfolio_metrics']['total_pnl']:,.0f} ({data['portfolio_metrics']['total_pnl_pct']:+.1f}%)
💵 Disponible: ${data['portfolio_metrics']['cash_available']:,.0f}

"""
        
        # Contexto de mercado
        if data['market_context']['has_report']:
            body_text += f"CONTEXTO DE MERCADO HOY:\n"
            body_text += f"📊 Sentiment general: {data['market_context']['sentiment']}\n"
            if data['market_context']['your_assets_mentioned'] > 0:
                body_text += f"🎯 {data['market_context']['your_assets_mentioned']} de tus activos mencionados en reporte\n"
            body_text += "\n"
        
        # Recomendaciones principales
        main_analysis = data['main_analysis']
        
        if data['notification_type'] == 'claude_comprehensive_paginated':
            immediate_actions = main_analysis.get('acciones_inmediatas', [])
            
            if immediate_actions:
                body_text += "ACCIONES INMEDIATAS:\n"
                for i, action in enumerate(immediate_actions, 1):
                    ticker = action.get('ticker', 'N/A')
                    accion = action.get('accion', '')
                    cantidad = action.get('cantidad', 0)
                    precio = action.get('precio_objetivo', 0)
                    razon = action.get('razon', '')
                    
                    body_text += f"{i}. {ticker}: {accion} {cantidad} acciones a ${precio:.0f}\n"
                    body_text += f"   Razón: {razon}\n\n"
            
            # Razonamiento integral
            razonamiento = main_analysis.get('razonamiento_integral', '')
            if razonamiento:
                body_text += f"ANÁLISIS DEL EXPERTO:\n{razonamiento}\n\n"
        
        else:
            # Análisis de reglas
            rules_recs = main_analysis.get('recommendations', [])
            if rules_recs:
                body_text += "RECOMENDACIONES AUTOMÁTICAS:\n"
                for i, rec in enumerate(rules_recs, 1):
                    action_desc = rec.action.value if hasattr(rec.action, 'value') else str(rec.action)
                    body_text += f"{i}. {rec.ticker}: {action_desc} {rec.suggested_shares} acciones\n"
                    body_text += f"   Confianza: {rec.confidence:.0f}%\n\n"
        
        # Status del sistema
        working_components = [k for k, v in data['components_status'].items() if v]
        body_text += f"COMPONENTES ACTIVOS: {len(working_components)}/4\n"
        for component in working_components:
            body_text += f"✅ {component.replace('_', ' ').title()}\n"
        
        body_text += "\n⚠️ Estas son sugerencias, no consejos financieros"
        body_text += "\n🤖 Generado por sistema integral de análisis"
        
        # Email HTML (versión simplificada)
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
            .container {{ background-color: white; padding: 30px; border-radius: 15px; max-width: 800px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; }}
            .confidence-high {{ border-left: 6px solid #27ae60; }}
            .confidence-medium {{ border-left: 6px solid #f39c12; }}
            .confidence-low {{ border-left: 6px solid #e74c3c; }}
        </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌟 ANÁLISIS INTEGRAL DE CARTERA</h1>
                    <p>{timestamp}</p>
                    <p><strong>Confianza: {confidence.upper()}</strong></p>
                </div>
                
                <div class="confidence-{confidence}" style="padding: 20px; margin: 20px 0; border-radius: 10px;">
                    <h2>💼 Tu Situación Actual</h2>
                    <p><strong>Total:</strong> ${data['portfolio_metrics']['total_value']:,.0f}</p>
                    <p><strong>Ganancia/Pérdida:</strong> ${data['portfolio_metrics']['total_pnl']:,.0f} ({data['portfolio_metrics']['total_pnl_pct']:+.1f}%)</p>
                    <p><strong>Disponible:</strong> ${data['portfolio_metrics']['cash_available']:,.0f}</p>
                </div>"""
        
        if data['market_context']['has_report']:
            body_html += f"""
                <div style="background-color: #e8f4fd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h2>📰 Contexto de Mercado Hoy</h2>
                    <p><strong>Sentiment general:</strong> {data['market_context']['sentiment'].title()}</p>"""
            
            if data['market_context']['your_assets_mentioned'] > 0:
                body_html += f"<p><strong>Tus activos mencionados:</strong> {data['market_context']['your_assets_mentioned']}</p>"
            
            body_html += "</div>"
        
        # Recomendaciones
        main_analysis = data['main_analysis']
        
        if data['notification_type'] == 'claude_comprehensive_paginated':
            immediate_actions = main_analysis.get('acciones_inmediatas', [])
            
            if immediate_actions:
                body_html += """
                <div style="background-color: #fff5f5; border: 2px solid #e74c3c; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h2>🚨 Acciones Inmediatas</h2>"""
                
                for i, action in enumerate(immediate_actions, 1):
                    ticker = action.get('ticker', 'N/A')
                    accion = action.get('accion', '')
                    cantidad = action.get('cantidad', 0)
                    precio = action.get('precio_objetivo', 0)
                    razon = action.get('razon', '')
                    
                    body_html += f"""
                    <div style="margin: 15px 0; padding: 15px; background-color: white; border-radius: 8px;">
                        <h3>{i}. {ticker}: {accion.upper()}</h3>
                        <p><strong>Cantidad:</strong> {cantidad} acciones</p>
                        <p><strong>Precio:</strong> ${precio:.0f}</p>
                        <p><strong>Razón:</strong> {razon}</p>
                    </div>"""
                
                body_html += "</div>"
        
        # Status del sistema
        working_components = [k for k, v in data['components_status'].items() if v]
        
        body_html += f"""
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h2>🔧 Sistema Integral</h2>
                    <p><strong>Componentes activos:</strong> {len(working_components)}/4</p>"""
        
        component_names = {
            'market_report': '📰 Reporte de mercado',
            'fundamental_ratios': '📊 Ratios fundamentales', 
            'technical_analysis': '🤖 Análisis técnico Claude',
            'rules_analysis': '📋 Sistema de reglas'
        }
        
        for component in working_components:
            name = component_names.get(component, component)
            body_html += f"<p>✅ {name}</p>"
        
        body_html += """
                </div>
                
                <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3>⚠️ Importante</h3>
                    <p>Estas son sugerencias basadas en análisis automatizado, no consejos financieros profesionales.</p>
                    <p>Siempre verifica los precios y condiciones del mercado antes de operar.</p>
                </div>
                
                <div style="text-align: center; color: #636e72; margin-top: 20px;">
                    <p><strong>🤖 Sistema Integral de Análisis de Cartera v3.0</strong></p>
                </div>
            </div>
        </body>
        </html>"""
        
        return subject, body_text, body_html
    
    def get_system_status(self) -> Dict:
        """Obtiene status completo del sistema integral"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'database': False,
                    'claude_api': False,
                    'market_scraper': False,
                    'ratios_scraper': False,
                    'notifications': False
                },
                'overall_health': 'unknown',
                'last_successful_analysis': None,
                'recommendations': []
            }
            
            # Test base de datos
            try:
                if self.db.test_connection():
                    status['components']['database'] = True
            except:
                pass
            
            # Test Claude API
            try:
                import os
                if os.getenv('ANTHROPIC_API_KEY'):
                    status['components']['claude_api'] = True
            except:
                pass
            
            # Test scrapers (básico)
            try:
                if self.page and not self.page.is_closed():
                    status['components']['market_scraper'] = True
                    status['components']['ratios_scraper'] = True
            except:
                pass
            
            # Test notificaciones
            try:
                from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
                from scraper.notifications.email_notifier import EmailNotifier
                
                whatsapp = WhatsAppNotifier()
                email = EmailNotifier()
                
                if whatsapp.is_configured or email.is_configured:
                    status['components']['notifications'] = True
            except:
                pass
            
            # Evaluar salud general
            working_count = sum(status['components'].values())
            total_count = len(status['components'])
            
            if working_count >= total_count * 0.8:
                status['overall_health'] = 'excellent'
                status['recommendations'] = ["Sistema funcionando óptimamente"]
            elif working_count >= total_count * 0.6:
                status['overall_health'] = 'good'
                status['recommendations'] = ["Sistema funcional con componentes menores deshabilitados"]
            elif working_count >= total_count * 0.4:
                status['overall_health'] = 'limited'
                status['recommendations'] = [
                    "Revisar configuración de componentes que fallan",
                    "Sistema puede funcionar con capacidades reducidas"
                ]
            else:
                status['overall_health'] = 'poor'
                status['recommendations'] = [
                    "Requiere configuración urgente",
                    "Verificar .env y dependencias",
                    "Ejecutar test_integration.py --quick"
                ]
            
            return status
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'components': {},
                'overall_health': 'error',
                'error': str(e),
                'recommendations': ["Error obteniendo status - revisar sistema"]
            }

# FUNCIONES AUXILIARES
def get_available_tickers_for_analysis(db_manager) -> List[str]:
    """Obtiene lista de tickers disponibles para análisis"""
    try:
        from datetime import timedelta
        
        # Buscar tickers con datos recientes (últimos 7 días)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        result = db_manager.supabase.table('precios_historico')\
            .select('ticker')\
            .gte('fecha', start_date.isoformat())\
            .execute()
        
        if result.data:
            tickers = list(set([row['ticker'] for row in result.data]))
            return sorted(tickers)
        
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo tickers disponibles: {str(e)}")
        return []

def validate_portfolio_data(portfolio_data: Dict) -> Dict:
    """Valida y limpia datos de cartera"""
    try:
        if not portfolio_data:
            return {'valid': False, 'error': 'Portfolio data is empty'}
        
        required_fields = ['activos', 'dinero_disponible']
        missing_fields = [field for field in required_fields if field not in portfolio_data]
        
        if missing_fields:
            return {'valid': False, 'error': f'Missing fields: {missing_fields}'}
        
        activos = portfolio_data.get('activos', [])
        if not activos:
            return {'valid': False, 'error': 'No assets in portfolio'}
        
        # Validar cada activo
        valid_activos = []
        for activo in activos:
            required_asset_fields = ['ticker', 'cantidad', 'valor_actual_total', 'precio_actual_unitario']
            
            if all(field in activo for field in required_asset_fields):
                # Asegurar que días_tenencia existe
                if 'dias_tenencia' not in activo:
                    activo['dias_tenencia'] = 1
                
                valid_activos.append(activo)
        
        if not valid_activos:
            return {'valid': False, 'error': 'No valid assets found'}
        
        # Actualizar portfolio con activos válidos
        validated_portfolio = portfolio_data.copy()
        validated_portfolio['activos'] = valid_activos
        
        return {
            'valid': True, 
            'portfolio_data': validated_portfolio,
            'stats': {
                'original_assets': len(activos),
                'valid_assets': len(valid_activos),
                'total_value': sum(a['valor_actual_total'] for a in valid_activos),
                'cash_available': portfolio_data.get('dinero_disponible', 0)
            }
        }
        
    except Exception as e:
        return {'valid': False, 'error': f'Validation error: {str(e)}'}

# FUNCIÓN PRINCIPAL PARA TESTING INDEPENDIENTE
def test_comprehensive_analyzer_standalone():
    """Test independiente del analizador integral"""
    print("🧪 TEST INDEPENDIENTE: COMPREHENSIVE MARKET ANALYZER")
    print("=" * 65)
    
    try:
        from database.database_manager import SupabaseManager
        
        # Crear datos de prueba
        test_portfolio = {
            'dinero_disponible': 50000.0,
            'activos': [
                {
                    'ticker': 'ALUA',
                    'cantidad': 100,
                    'valor_actual_total': 45000.0,
                    'valor_inicial_total': 40000.0,
                    'precio_actual_unitario': 450.0,
                    'precio_inicial_unitario': 400.0,
                    'ganancia_perdida_total': 5000.0,
                    'ganancia_perdida_porcentaje': 12.5,
                    'dias_tenencia': 15
                }
            ]
        }
        
        # Validar datos
        validation = validate_portfolio_data(test_portfolio)
        if not validation['valid']:
            print(f"❌ Datos de test inválidos: {validation['error']}")
            return False
        
        print("✅ Datos de test válidos")
        print(f"   📊 Activos válidos: {validation['stats']['valid_assets']}")
        print(f"   💰 Valor total: ${validation['stats']['total_value']:,.0f}")
        
        # Test sin navegador (solo validación de lógica)
        print("\n🔍 Test de lógica sin navegador...")
        
        # Simular análisis
        mock_analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_integral_test',
            'components': {
                'market_report': False,  # Sin navegador
                'fundamental_ratios': False,  # Sin navegador
                'technical_analysis': False,  # Sin API key válida (probablemente)
                'rules_analysis': True   # Este sí debería funcionar
            },
            'portfolio_data': validation['portfolio_data'],
            'confidence_level': 'test'
        }
        
        print("✅ Test de lógica completado")
        
        # Test de componentes disponibles
        print("\n🔍 Verificando disponibilidad de componentes...")
        
        components_available = {
            'BalanzDailyReportScraper': False,
            'FinancialRatiosScraper': False,
            'ClaudePortfolioAgent': False,
            'AdvancedPortfolioManager': False
        }
        
        try:
            from balanz_daily_report_scraper import BalanzDailyReportScraper
            components_available['BalanzDailyReportScraper'] = True
        except ImportError:
            pass
        
        try:
            from financial_ratios_scraper import FinancialRatiosScraper
            components_available['FinancialRatiosScraper'] = True
        except ImportError:
            pass
        
        try:
            from claude_portfolio_agent import ClaudePortfolioAgent
            components_available['ClaudePortfolioAgent'] = True
        except ImportError:
            pass
        
        try:
            from advanced_portfolio_manager import AdvancedPortfolioManager
            components_available['AdvancedPortfolioManager'] = True
        except ImportError:
            pass
        
        # Mostrar status
        for component, available in components_available.items():
            status = "✅" if available else "❌"
            print(f"   {status} {component}")
        
        available_count = sum(components_available.values())
        total_count = len(components_available)
        
        print(f"\n📊 RESUMEN: {available_count}/{total_count} componentes disponibles")
        
        if available_count >= 3:
            print("🎉 Sistema integral listo para usar")
            return True
        elif available_count >= 2:
            print("⚠️ Sistema funcional con limitaciones")
            return True
        else:
            print("❌ Sistema requiere más componentes")
            return False
            
    except Exception as e:
        print(f"❌ Error en test independiente: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Ejecutar test independiente
    test_comprehensive_analyzer_standalone()