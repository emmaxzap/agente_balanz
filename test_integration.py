# test_integration.py - Para probar la integración completa
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from scraper.web_scraper import WebScraperPlaywright
from config import LOGIN_CONFIG
from database.database_manager import SupabaseManager

def test_complete_integration():
    """Prueba la integración completa del nuevo sistema"""
    
    print("🧪 PROBANDO INTEGRACIÓN COMPLETA v3.0")
    print("=" * 60)
    print("📋 Tests: Login → Reporte → Ratios → Análisis integral")
    print("=" * 60)
    
    scraper = WebScraperPlaywright(headless=False)
    test_results = {
        'login': False,
        'daily_report': False,
        'financial_ratios': False,
        'comprehensive_analysis': False,
        'overall_success': False
    }
    
    try:
        # 1. INICIAR NAVEGADOR Y LOGIN
        print("\n🔧 PASO 1: INICIANDO NAVEGADOR Y LOGIN")
        print("-" * 45)
        
        scraper.start_browser()
        print("✅ Navegador iniciado")
        
        login_success = scraper.login(
            LOGIN_CONFIG['url'],
            LOGIN_CONFIG['username'], 
            LOGIN_CONFIG['password']
        )
        
        if not login_success:
            print("❌ Login falló - no se puede continuar con tests")
            return test_results
        
        print("✅ Login exitoso - continuando con tests...")
        test_results['login'] = True
        
        # 2. PROBAR REPORTE DIARIO
        print("\n📊 PASO 2: PROBANDO REPORTE DIARIO DE BALANZ")
        print("-" * 50)
        
        try:
            from balanz_daily_report_scraper import BalanzDailyReportScraper
            
            report_scraper = BalanzDailyReportScraper(scraper.page)
            daily_report = report_scraper.get_daily_market_report()
            
            if daily_report and 'full_text' in daily_report:
                print("✅ Reporte diario extraído exitosamente")
                print(f"   📊 Texto extraído: {len(daily_report['full_text'])} caracteres")
                print(f"   📊 Secciones: {len(daily_report.get('structured_content', {}))}")
                
                # Verificar insights de cartera
                portfolio_insights = daily_report.get('portfolio_insights', {})
                tickers_mencionados = portfolio_insights.get('tickers_mencionados', {})
                
                if tickers_mencionados:
                    print(f"   🎯 Insights de tu cartera:")
                    for ticker, info in tickers_mencionados.items():
                        if info.get('mencionado'):
                            print(f"      • {ticker}: {info.get('performance_reportada', 'Sin performance')}")
                
                test_results['daily_report'] = True
            else:
                print("❌ No se pudo obtener reporte diario")
                print("   📋 Estructura obtenida:", list(daily_report.keys()) if daily_report else "Vacío")
                
        except ImportError:
            print("❌ BalanzDailyReportScraper no disponible")
        except Exception as e:
            print(f"❌ Error probando reporte diario: {str(e)}")
        
        # 3. PROBAR RATIOS FINANCIEROS
        print("\n📊 PASO 3: PROBANDO RATIOS FINANCIEROS")
        print("-" * 45)
        
        try:
            from financial_ratios_scraper import FinancialRatiosScraper
            
            ratios_scraper = FinancialRatiosScraper(scraper.page)
            
            # Probar con algunos tickers de tu cartera
            test_tickers = ['ALUA', 'COME', 'EDN', 'METR', 'TECO2']
            ratios_data = ratios_scraper.get_financial_ratios_for_tickers(test_tickers)
            
            if ratios_data and 'ratios_by_ticker' in ratios_data:
                ratios_found = len(ratios_data['ratios_by_ticker'])
                print(f"✅ Ratios financieros extraídos: {ratios_found} activos")
                
                # Mostrar muestra de ratios
                for ticker, ratios in list(ratios_data['ratios_by_ticker'].items())[:3]:
                    pe = ratios.get('pe', 'N/A')
                    roe = ratios.get('roe', 'N/A')
                    score = ratios.get('fundamental_score', 'N/A')
                    print(f"   📊 {ticker}: P/E={pe}, ROE={roe}, Score={score}")
                
                test_results['financial_ratios'] = True
            else:
                print("❌ No se pudieron obtener ratios financieros")
                
        except ImportError:
            print("❌ FinancialRatiosScraper no disponible")
        except Exception as e:
            print(f"❌ Error probando ratios: {str(e)}")
        
        # 4. PROBAR ANÁLISIS INTEGRAL COMPLETO
        print("\n🌍 PASO 4: PROBANDO ANÁLISIS INTEGRAL")
        print("-" * 45)
        
        try:
            # Crear datos de cartera simulados para test
            test_portfolio_data = create_test_portfolio_data()
            
            from comprehensive_market_analyzer import ComprehensiveMarketAnalyzer
            
            comprehensive_analyzer = ComprehensiveMarketAnalyzer(scraper.page, SupabaseManager())
            
            print("🔍 Ejecutando análisis integral...")
            integral_result = comprehensive_analyzer.run_comprehensive_analysis(test_portfolio_data)
            
            if integral_result:
                print("✅ Análisis integral ejecutado")
                
                # Verificar componentes
                has_market_report = bool(integral_result.get('market_report'))
                has_enhanced_portfolio = bool(integral_result.get('portfolio_data'))
                has_analysis = bool(integral_result.get('comprehensive_analysis'))
                
                print(f"   📰 Reporte de mercado: {'✅' if has_market_report else '❌'}")
                print(f"   📊 Portfolio enriquecido: {'✅' if has_enhanced_portfolio else '❌'}")
                print(f"   🤖 Análisis Claude: {'✅' if has_analysis else '❌'}")
                
                if has_market_report and has_enhanced_portfolio and has_analysis:
                    test_results['comprehensive_analysis'] = True
                    print("✅ Análisis integral COMPLETO")
                else:
                    print("⚠️ Análisis integral PARCIAL")
                
            else:
                print("❌ Análisis integral falló completamente")
                
        except ImportError as e:
            print(f"❌ ComprehensiveMarketAnalyzer no disponible: {str(e)}")
        except Exception as e:
            print(f"❌ Error probando análisis integral: {str(e)}")
        
        # 5. EVALUACIÓN FINAL
        print(f"\n📊 RESUMEN DE TESTS")
        print("=" * 30)
        
        tests_passed = sum(test_results.values())
        total_tests = len(test_results) - 1  # Excluir 'overall_success'
        
        for test_name, result in test_results.items():
            if test_name != 'overall_success':
                status = "✅" if result else "❌"
                print(f"{status} {test_name.replace('_', ' ').title()}: {'Funcionando' if result else 'Con problemas'}")
        
        success_rate = tests_passed / total_tests
        test_results['overall_success'] = success_rate >= 0.5
        
        print(f"\n🎯 RESULTADO GENERAL:")
        if success_rate >= 0.75:
            print(f"🎉 EXCELENTE: {tests_passed}/{total_tests} tests funcionando")
            print("✅ Sistema integral listo para usar")
        elif success_rate >= 0.5:
            print(f"✅ BUENO: {tests_passed}/{total_tests} tests funcionando")
            print("⚠️ Sistema funcional con algunos componentes limitados")
        else:
            print(f"⚠️ LIMITADO: {tests_passed}/{total_tests} tests funcionando")
            print("🔧 Requiere ajustes antes de usar modo integral")
        
        return test_results
        
    except Exception as e:
        print(f"\n❌ Error general en testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return test_results
    
    finally:
        print("\n🔧 Cerrando navegador...")
        scraper.close()
        print("✅ Navegador cerrado")

def create_test_portfolio_data():
    """Crea datos de cartera simulados para testing"""
    return {
        'dinero_disponible': 50000.0,
        'valor_total_cartera': 150000.0,
        'total_invertido': 140000.0,
        'ganancia_perdida_total': 10000.0,
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
            },
            {
                'ticker': 'COME',
                'cantidad': 200,
                'valor_actual_total': 60000.0,
                'valor_inicial_total': 55000.0,
                'precio_actual_unitario': 300.0,
                'precio_inicial_unitario': 275.0,
                'ganancia_perdida_total': 5000.0,
                'ganancia_perdida_porcentaje': 9.1,
                'dias_tenencia': 8
            },
            {
                'ticker': 'EDN',
                'cantidad': 150,
                'valor_actual_total': 45000.0,
                'valor_inicial_total': 45000.0,
                'precio_actual_unitario': 300.0,
                'precio_inicial_unitario': 300.0,
                'ganancia_perdida_total': 0.0,
                'ganancia_perdida_porcentaje': 0.0,
                'dias_tenencia': 3
            }
        ]
    }

def test_individual_components():
    """Prueba componentes individuales sin necesidad de login"""
    print("\n🧪 PROBANDO COMPONENTES INDIVIDUALES")
    print("=" * 50)
    
    # 1. Test base de datos
    print("\n1️⃣ PROBANDO CONEXIÓN A BASE DE DATOS:")
    try:
        db = SupabaseManager()
        if db.test_connection():
            print("✅ Conexión a Supabase funcionando")
            
            # Probar queries básicas
            activos_df = db.obtener_resumen_activos()
            if not activos_df.empty:
                print(f"✅ Base de datos tiene {len(activos_df)} activos registrados")
            else:
                print("⚠️ Base de datos sin activos - necesita datos iniciales")
                
        else:
            print("❌ Error de conexión a Supabase")
            
    except Exception as e:
        print(f"❌ Error probando BD: {str(e)}")
    
    # 2. Test análisis financiero
    print("\n2️⃣ PROBANDO ANÁLISIS FINANCIERO:")
    try:
        from analysis.financial_analyzer import FinancialAnalyzer
        
        db = SupabaseManager()
        analyzer = FinancialAnalyzer(db)
        
        # Probar análisis de un activo conocido
        test_ticker = 'AAPL'
        analysis = analyzer.analyze_asset_for_decision(test_ticker, 150.0)
        
        if analysis and analysis.get('recommendation'):
            print(f"✅ Análisis financiero funcionando")
            print(f"   📊 {test_ticker}: {analysis['recommendation']} (confianza: {analysis.get('confidence', 0)}%)")
            print(f"   📊 Razones: {analysis.get('reasons', [])[:2]}")
        else:
            print("❌ Análisis financiero no genera resultados")
            
    except Exception as e:
        print(f"❌ Error probando análisis: {str(e)}")
    
    # 3. Test configuración de Claude
    print("\n3️⃣ PROBANDO CONFIGURACIÓN DE CLAUDE:")
    try:
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if api_key:
            print(f"✅ API Key configurada: {api_key[:10]}...")
            
            # Test básico de Claude
            from claude_portfolio_agent import ClaudePortfolioAgent
            
            claude_agent = ClaudePortfolioAgent(SupabaseManager())
            
            # Test con datos mínimos
            test_data = create_test_portfolio_data()
            print("🔍 Probando consulta a Claude...")
            
            # Solo probar si la configuración es correcta
            if hasattr(claude_agent, 'client'):
                print("✅ Cliente de Claude inicializado correctamente")
            else:
                print("❌ Cliente de Claude no inicializado")
                
        else:
            print("❌ ANTHROPIC_API_KEY no configurada")
            print("💡 Agrega tu API key en el archivo .env:")
            print("   ANTHROPIC_API_KEY=sk-ant-...")
            
    except Exception as e:
        print(f"❌ Error probando Claude: {str(e)}")
    
    # 4. Test notificaciones
    print("\n4️⃣ PROBANDO NOTIFICACIONES:")
    try:
        # WhatsApp
        from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
        
        whatsapp = WhatsAppNotifier()
        if whatsapp.is_configured:
            print("✅ WhatsApp configurado correctamente")
        else:
            print("⚠️ WhatsApp no configurado")
        
        # Email
        from scraper.notifications.email_notifier import EmailNotifier
        
        email = EmailNotifier()
        if email.is_configured:
            print("✅ Email configurado correctamente")
        else:
            print("⚠️ Email no configurado")
            
    except Exception as e:
        print(f"❌ Error probando notificaciones: {str(e)}")

def test_scrapers_with_login():
    """Prueba los scrapers específicos con login"""
    print("\n🧪 PROBANDO SCRAPERS ESPECÍFICOS")
    print("=" * 50)
    
    scraper = WebScraperPlaywright(headless=False)
    
    try:
        # Iniciar y hacer login
        scraper.start_browser()
        
        login_success = scraper.login(
            LOGIN_CONFIG['url'],
            LOGIN_CONFIG['username'], 
            LOGIN_CONFIG['password']
        )
        
        if not login_success:
            print("❌ Login falló")
            return False
        
        print("✅ Login exitoso - probando scrapers...")
        
        # 1. Probar reporte diario
        print("\n📰 PROBANDO REPORTE DIARIO:")
        print("-" * 30)
        
        try:
            from balanz_daily_report_scraper import BalanzDailyReportScraper
            
            report_scraper = BalanzDailyReportScraper(scraper.page)
            daily_report = report_scraper.get_daily_market_report()
            
            if daily_report:
                print("✅ Reporte diario extraído")
                
                # Análisis del contenido
                full_text = daily_report.get('full_text', '')
                if len(full_text) > 500:
                    print(f"✅ Contenido sustancial: {len(full_text)} caracteres")
                    
                    # Buscar menciones de tus activos
                    your_tickers = ['ALUA', 'COME', 'EDN', 'METR', 'TECO2']
                    mentions = []
                    
                    for ticker in your_tickers:
                        if ticker.lower() in full_text.lower():
                            mentions.append(ticker)
                    
                    if mentions:
                        print(f"🎯 Tus activos mencionados: {mentions}")
                    else:
                        print("📊 Ninguno de tus activos mencionado específicamente")
                
                else:
                    print("⚠️ Contenido extraído muy corto")
            else:
                print("❌ No se pudo extraer reporte")
                
        except Exception as e:
            print(f"❌ Error en reporte diario: {str(e)}")
        
        # 2. Probar ratios financieros
        print("\n📊 PROBANDO RATIOS FINANCIEROS:")
        print("-" * 30)
        
        try:
            from financial_ratios_scraper import FinancialRatiosScraper
            
            ratios_scraper = FinancialRatiosScraper(scraper.page)
            
            # Probar con 2-3 tickers para no tardar mucho
            test_tickers = ['ALUA', 'COME']
            print(f"🔍 Probando ratios para: {test_tickers}")
            
            ratios_data = ratios_scraper.get_financial_ratios_for_tickers(test_tickers)
            
            if ratios_data and 'ratios_by_ticker' in ratios_data:
                print("✅ Ratios extraídos exitosamente")
                
                for ticker, ratios in ratios_data['ratios_by_ticker'].items():
                    print(f"📊 {ticker}:")
                    print(f"   P/E: {ratios.get('pe', 'N/A')}")
                    print(f"   ROE: {ratios.get('roe', 'N/A')}%")
                    print(f"   Debt/Equity: {ratios.get('debt_to_equity', 'N/A')}")
                    print(f"   Score fundamental: {ratios.get('fundamental_score', 'N/A')}/100")
                    print(f"   Categoría: {ratios.get('valuation_category', 'N/A')}")
            else:
                print("❌ No se pudieron extraer ratios")
                
        except Exception as e:
            print(f"❌ Error en ratios: {str(e)}")
        
        # 3. Probar cartera
        print("\n💼 PROBANDO EXTRACCIÓN DE CARTERA:")
        print("-" * 30)
        
        try:
            from scraper.cartera_extractor import CarteraExtractor
            
            cartera_extractor = CarteraExtractor(scraper.page)
            portfolio_data = cartera_extractor.extract_portfolio_data()
            
            if portfolio_data:
                print("✅ Cartera extraída exitosamente")
                print(f"   💰 Dinero disponible: ${portfolio_data.get('dinero_disponible', 0):,.2f}")
                print(f"   📊 Activos: {len(portfolio_data.get('activos', []))}")
                
                # Mostrar activos
                for activo in portfolio_data.get('activos', [])[:3]:
                    ticker = activo.get('ticker', 'N/A')
                    dias = activo.get('dias_tenencia', 0)
                    pnl_pct = activo.get('ganancia_perdida_porcentaje', 0)
                    print(f"   📈 {ticker}: {dias} días, {pnl_pct:+.1f}%")
            else:
                print("❌ No se pudo extraer cartera")
                
        except Exception as e:
            print(f"❌ Error extrayendo cartera: {str(e)}")
        
        print("\n🎉 TESTING DE SCRAPERS COMPLETADO")
        return True
        
    except Exception as e:
        print(f"\n❌ Error general: {str(e)}")
        return False
    
    finally:
        scraper.close()

def test_macro_data():
    """Prueba la recolección de datos macroeconómicos"""
    print("\n🌍 PROBANDO DATOS MACROECONÓMICOS")
    print("=" * 45)
    
    try:
        from test_macro_data import MacroDataCollectorFixed
        
        collector = MacroDataCollectorFixed()
        snapshot = collector.get_current_macro_snapshot()
        
        if snapshot:
            print("✅ Datos macro obtenidos")
            
            # Verificar cada componente
            dolar_data = snapshot.get('dolar_data', {})
            if dolar_data:
                blue_price = dolar_data.get('blue_sell', 0)
                brecha = dolar_data.get('brecha', 0)
                print(f"   💵 Dólar blue: ${blue_price:.0f} (brecha: {brecha:+.1f}%)")
            
            riesgo_pais = snapshot.get('riesgo_pais')
            if riesgo_pais:
                print(f"   📈 Riesgo país: {riesgo_pais:.0f} pb")
            
            # Implicaciones para inversión
            print("\n💡 IMPLICACIONES PARA INVERSIÓN:")
            implications = collector.get_macro_investment_implications()
            
            portfolio_adjustments = implications['implications'].get('portfolio_adjustments', [])
            if portfolio_adjustments:
                for adj in portfolio_adjustments[:2]:
                    print(f"   • {adj}")
            
            sector_prefs = implications['implications'].get('sector_preferences', [])
            if sector_prefs:
                for pref in sector_prefs[:2]:
                    print(f"   • {pref}")
            
            return True
        else:
            print("❌ No se pudieron obtener datos macro")
            return False
            
    except Exception as e:
        print(f"❌ Error probando datos macro: {str(e)}")
        return False

def run_quick_test():
    """Test rápido sin login para verificar imports y configuración básica"""
    print("⚡ QUICK TEST - SIN LOGIN")
    print("=" * 30)
    
    issues_found = []
    components_ok = 0
    total_components = 6
    
    # 1. Test imports básicos
    print("1️⃣ Imports básicos...")
    try:
        from database.database_manager import SupabaseManager
        from analysis.financial_analyzer import FinancialAnalyzer
        from advanced_portfolio_manager import AdvancedPortfolioManager
        print("✅ Imports core funcionando")
        components_ok += 1
    except Exception as e:
        print(f"❌ Error imports core: {str(e)}")
        issues_found.append("Imports básicos fallan")
    
    # 2. Test configuración BD
    print("2️⃣ Configuración BD...")
    try:
        db = SupabaseManager()
        if db.test_connection():
            print("✅ Base de datos accesible")
            components_ok += 1
        else:
            print("❌ Base de datos no accesible")
            issues_found.append("Conexión Supabase falla")
    except Exception as e:
        print(f"❌ Error BD: {str(e)}")
        issues_found.append("Configuración Supabase incorrecta")
    
    # 3. Test configuración Claude
    print("3️⃣ Configuración Claude...")
    try:
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key and len(api_key) > 20:
            print("✅ API Key Claude configurada")
            components_ok += 1
        else:
            print("❌ API Key Claude no configurada")
            issues_found.append("ANTHROPIC_API_KEY faltante en .env")
    except Exception as e:
        print(f"❌ Error Claude config: {str(e)}")
        issues_found.append("Error en configuración Claude")
    
    # 4. Test imports nuevos
    print("4️⃣ Nuevos módulos...")
    try:
        from balanz_daily_report_scraper import BalanzDailyReportScraper
        from financial_ratios_scraper import FinancialRatiosScraper
        from comprehensive_market_analyzer import ComprehensiveMarketAnalyzer
        print("✅ Módulos de análisis integral disponibles")
        components_ok += 1
    except Exception as e:
        print(f"❌ Error imports nuevos: {str(e)}")
        issues_found.append("Módulos nuevos no disponibles")
    
    # 5. Test notificaciones
    print("5️⃣ Notificaciones...")
    try:
        from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
        from scraper.notifications.email_notifier import EmailNotifier
        
        whatsapp = WhatsAppNotifier()
        email = EmailNotifier()
        
        notif_count = sum([whatsapp.is_configured, email.is_configured])
        
        if notif_count >= 1:
            print(f"✅ Al menos 1 canal de notificación configurado")
            components_ok += 1
        else:
            print("⚠️ Notificaciones no configuradas")
            issues_found.append("WhatsApp y Email no configurados")
            
    except Exception as e:
        print(f"❌ Error notificaciones: {str(e)}")
        issues_found.append("Módulos de notificación con problemas")
    
    # 6. Test dependencies
    print("6️⃣ Dependencias...")
    try:
        import pandas as pd
        import numpy as np
        import anthropic
        import playwright
        print("✅ Dependencias principales instaladas")
        components_ok += 1
    except Exception as e:
        print(f"❌ Error dependencias: {str(e)}")
        issues_found.append("Dependencias faltantes")
    
    # Resumen
    print(f"\n📊 RESUMEN QUICK TEST:")
    print("=" * 25)
    print(f"✅ Componentes OK: {components_ok}/{total_components}")
    
    if issues_found:
        print(f"❌ Problemas encontrados:")
        for issue in issues_found:
            print(f"   • {issue}")
    
    if components_ok >= total_components * 0.8:
        print(f"\n🎉 SISTEMA LISTO PARA USAR")
        print("💡 Ejecuta: python test_integration.py --full")
    elif components_ok >= total_components * 0.5:
        print(f"\n⚠️ SISTEMA PARCIALMENTE FUNCIONAL")
        print("💡 Soluciona los problemas y vuelve a probar")
    else:
        print(f"\n❌ SISTEMA NECESITA CONFIGURACIÓN")
        print("💡 Revisa el archivo .env y las dependencias")
    
    return components_ok >= total_components * 0.5

def main():
    """Función principal de testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test de integración del sistema Balanz')
    parser.add_argument('--full', action='store_true', help='Test completo con login')
    parser.add_argument('--quick', action='store_true', help='Test rápido sin login')
    parser.add_argument('--scrapers', action='store_true', help='Test solo scrapers')
    parser.add_argument('--macro', action='store_true', help='Test solo datos macro')
    
    args = parser.parse_args()
    
    if args.quick:
        return run_quick_test()
    elif args.scrapers:
        return test_scrapers_with_login()
    elif args.macro:
        return test_macro_data()
    elif args.full:
        return test_complete_integration()
    else:
        # Por defecto: quick test
        print("🚀 EJECUTANDO QUICK TEST (usa --full para test completo)")
        return run_quick_test()

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print(f"\n🎉 Testing completado exitosamente")
            print("💡 El sistema está listo para usar")
        else:
            print(f"\n⚠️ Testing completado con problemas")
            print("💡 Revisa los errores y vuelve a intentar")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error crítico en testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)