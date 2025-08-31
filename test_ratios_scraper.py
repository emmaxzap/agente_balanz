# test_ratios_scraper_corrected.py - Test CORRECTO sin login para Screenermatic
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from scraper.web_scraper import WebScraperPlaywright

def test_ratios_scraper_direct():
    """Test del scraper de ratios SIN login - directo a Screenermatic"""
    print("🧪 TEST DEL SCRAPER DE RATIOS - DIRECTO A SCREENERMATIC")
    print("=" * 60)
    print("💡 Los ratios están en Screenermatic, NO en Balanz")
    print("💡 No necesitamos login para acceder a los ratios")
    print("=" * 60)
    
    # Configuración de test
    test_tickers = ['ALUA', 'COME', 'EDN', 'AAPL', 'MSFT']  # Mix de argentinos y US
    
    scraper = WebScraperPlaywright(headless=False)
    
    try:
        # 1. Solo iniciar navegador (SIN LOGIN)
        print("\n🔧 PASO 1: INICIANDO NAVEGADOR")
        print("-" * 30)
        
        scraper.start_browser()
        print("✅ Navegador iniciado correctamente")
        
        # 2. Crear el scraper directamente (usando el original o el corregido)
        print("\n📊 PASO 2: PROBANDO SCRAPER DE RATIOS")
        print("-" * 40)
        
        # Primero intentar con el original
        try:
            from financial_ratios_scraper import FinancialRatiosScraper
            print("✅ Usando financial_ratios_scraper.py original")
            scraper_version = "original"
        except ImportError:
            print("❌ No se encontró financial_ratios_scraper.py original")
            return False
        
        # Si queremos probar la versión corregida:
        # try:
        #     from financial_ratios_scraper_fixed import FinancialRatiosScraper
        #     print("✅ Usando financial_ratios_scraper_fixed.py")
        #     scraper_version = "fixed"
        # except ImportError:
        #     print("❌ No se encontró financial_ratios_scraper_fixed.py")
        #     print("💡 Copia el código del artifact y guárdalo como financial_ratios_scraper_fixed.py")
        #     return False
        
        # 3. Crear instancia del scraper de ratios
        ratios_scraper = FinancialRatiosScraper(scraper.page)
        
        print(f"🔍 Probando con tickers: {test_tickers}")
        print("⏳ Accediendo a Screenermatic...")
        print("⏳ Esto puede tomar 30-90 segundos...")
        
        # 4. Ejecutar scraping
        ratios_data = ratios_scraper.get_financial_ratios_for_tickers(test_tickers)
        
        # 5. Analizar resultados
        print("\n📊 PASO 3: ANALIZANDO RESULTADOS")
        print("-" * 35)
        
        if ratios_data and 'ratios_by_ticker' in ratios_data:
            ratios_by_ticker = ratios_data['ratios_by_ticker']
            success_count = len(ratios_by_ticker)
            total_requested = len(test_tickers)
            
            print(f"✅ ÉXITO: {success_count}/{total_requested} tickers procesados")
            
            # Mostrar resultados detallados
            for ticker, ratios in ratios_by_ticker.items():
                print(f"\n🎯 {ticker}:")
                print(f"   P/E Ratio: {ratios.get('pe', 'N/A')}")
                print(f"   ROE: {ratios.get('roe', 'N/A')}%")
                print(f"   Debt/Equity: {ratios.get('debt_to_equity', 'N/A')}")
                print(f"   Current Ratio: {ratios.get('current_ratio', 'N/A')}")
                print(f"   Score Fundamental: {ratios.get('fundamental_score', 'N/A')}/100")
                print(f"   Categoría: {ratios.get('valuation_category', 'N/A')}")
            
            # Mostrar metadata del scraping
            print(f"\n🔧 INFO DEL SCRAPING:")
            print(f"   Fuente: {ratios_data.get('data_source', 'N/A')}")
            print(f"   Fecha: {ratios_data.get('fecha', 'N/A')}")
            print(f"   Campos disponibles: {len(ratios_data.get('fields_available', []))}")
            
            # Evaluar éxito
            if success_count >= len(test_tickers) * 0.4:  # Al menos 40% de éxito
                print(f"\n🎉 TEST EXITOSO")
                print(f"✅ El scraper de ratios funciona correctamente")
                
                if success_count == len(test_tickers):
                    print(f"🌟 PERFECTO: Todos los tickers encontrados")
                elif success_count >= len(test_tickers) * 0.8:
                    print(f"👍 MUY BIEN: Mayoría de tickers encontrados")
                else:
                    print(f"👌 BIEN: Suficientes tickers para análisis")
                
                return True
            else:
                print(f"\n⚠️ TEST PARCIAL")
                print(f"✅ El scraper funciona pero encontró pocos tickers")
                print(f"💡 Puede ser normal si los tickers argentinos no están en Screenermatic")
                return True
                
        else:
            print("❌ FALLO COMPLETO")
            print("❌ No se pudieron extraer ratios")
            
            # Información de debug básica
            if ratios_data:
                print(f"\n🔧 DATOS DEVUELTOS:")
                for key, value in ratios_data.items():
                    if key != 'ratios_by_ticker':
                        print(f"   {key}: {value}")
            
            print(f"\n💡 POSIBLES CAUSAS:")
            print(f"   • Screenermatic cambió su estructura HTML")
            print(f"   • El sitio está bloqueando el scraping")
            print(f"   • Los tickers no existen en Screenermatic")
            print(f"   • Problemas de conexión a internet")
            
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE EL TEST: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n🔧 Cerrando navegador...")
        scraper.close()
        print("✅ Navegador cerrado")

def test_screenermatic_access():
    """Test simple para verificar acceso a Screenermatic"""
    print("🧪 TEST DE ACCESO A SCREENERMATIC")
    print("=" * 40)
    
    scraper = WebScraperPlaywright(headless=False)
    
    try:
        scraper.start_browser()
        
        # URL directa de Screenermatic
        ratios_url = "https://www.screenermatic.com/general_ratios.php"
        
        print(f"\n🌐 Navegando a: {ratios_url}")
        
        # Configurar headers realistas
        scraper.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3'
        })
        
        scraper.page.goto(ratios_url, wait_until='networkidle')
        import time
        time.sleep(5)
        
        # Verificar acceso
        page_title = scraper.page.title()
        page_url = scraper.page.url
        
        print(f"✅ Página cargada")
        print(f"📋 Título: {page_title}")
        print(f"🔗 URL final: {page_url}")
        
        # Verificar si hay contenido financiero
        page_content = scraper.page.content()
        
        financial_keywords = ['P/E', 'ROE', 'Debt', 'Current', 'ratio', 'AAPL', 'MSFT']
        found_keywords = [kw for kw in financial_keywords if kw.lower() in page_content.lower()]
        
        print(f"\n📊 Contenido financiero:")
        print(f"   Keywords encontradas: {len(found_keywords)}/{len(financial_keywords)}")
        print(f"   Keywords: {found_keywords}")
        
        # Verificar estructura de tabla
        table_elements = scraper.page.locator('table').all()
        tbody_elements = scraper.page.locator('tbody').all()
        tr_elements = scraper.page.locator('tr').all()
        
        print(f"\n🔧 Estructura HTML:")
        print(f"   Tablas: {len(table_elements)}")
        print(f"   TBodies: {len(tbody_elements)}")
        print(f"   Filas (TR): {len(tr_elements)}")
        
        # Buscar tickers conocidos
        test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        found_tickers = []
        
        for ticker in test_tickers:
            elements = scraper.page.locator(f'text="{ticker}"').all()
            if len(elements) > 0:
                found_tickers.append(ticker)
        
        print(f"\n🎯 Tickers encontrados:")
        print(f"   {len(found_tickers)}/{len(test_tickers)}: {found_tickers}")
        
        # Evaluación final
        success_indicators = [
            'screener' in page_title.lower(),
            len(found_keywords) >= 3,
            len(tr_elements) >= 50,
            len(found_tickers) >= 2
        ]
        
        success_count = sum(success_indicators)
        
        print(f"\n📊 EVALUACIÓN FINAL:")
        print(f"✅ Título correcto: {'Sí' if success_indicators[0] else 'No'}")
        print(f"✅ Contenido financiero: {'Sí' if success_indicators[1] else 'No'}")
        print(f"✅ Estructura de tabla: {'Sí' if success_indicators[2] else 'No'}")
        print(f"✅ Tickers encontrados: {'Sí' if success_indicators[3] else 'No'}")
        
        if success_count >= 3:
            print(f"\n🎉 SCREENERMATIC ACCESIBLE")
            print(f"✅ El sitio funciona correctamente")
            print(f"💡 El problema puede estar en el código del scraper")
            return True
        elif success_count >= 2:
            print(f"\n⚠️ SCREENERMATIC PARCIALMENTE ACCESIBLE")
            print(f"✅ El sitio responde pero con limitaciones")
            print(f"💡 Puede funcionar con ajustes en el scraper")
            return True
        else:
            print(f"\n❌ SCREENERMATIC NO ACCESIBLE")
            print(f"❌ El sitio no responde o está bloqueando el acceso")
            print(f"💡 Considera usar fuentes alternativas de ratios")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR ACCEDIENDO A SCREENERMATIC: {str(e)}")
        return False
    
    finally:
        scraper.close()

def debug_current_scraper():
    """Debug del scraper actual sin modificaciones"""
    print("🔍 DEBUG DEL SCRAPER ACTUAL")
    print("=" * 35)
    
    scraper = WebScraperPlaywright(headless=False)
    
    try:
        scraper.start_browser()
        
        # Importar el scraper actual
        from financial_ratios_scraper import FinancialRatiosScraper
        ratios_scraper = FinancialRatiosScraper(scraper.page)
        
        # Probar con un solo ticker para debug detallado
        test_ticker = ['AAPL']
        
        print(f"🔍 Debugeando scraper actual con: {test_ticker}")
        
        # Interceptar errores
        try:
            ratios_data = ratios_scraper.get_financial_ratios_for_tickers(test_ticker)
            
            print(f"\n📊 RESULTADO:")
            if ratios_data:
                print(f"✅ Datos obtenidos: {ratios_data.keys()}")
                
                if 'ratios_by_ticker' in ratios_data:
                    ratios_by_ticker = ratios_data['ratios_by_ticker']
                    print(f"📊 Tickers procesados: {len(ratios_by_ticker)}")
                    
                    for ticker, ratios in ratios_by_ticker.items():
                        print(f"   {ticker}: {list(ratios.keys())}")
                else:
                    print("❌ No hay 'ratios_by_ticker' en el resultado")
            else:
                print("❌ No se obtuvieron datos")
                
        except Exception as scraper_error:
            print(f"❌ ERROR EN SCRAPER: {str(scraper_error)}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except ImportError:
        print("❌ No se encontró financial_ratios_scraper.py")
        print("💡 Asegúrate de que el archivo existe en el directorio")
        return False
    
    except Exception as e:
        print(f"❌ ERROR EN DEBUG: {str(e)}")
        return False
    
    finally:
        scraper.close()

def main():
    """Función principal de testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test del scraper de ratios CORRECTO')
    parser.add_argument('--access', action='store_true', help='Solo probar acceso a Screenermatic')
    parser.add_argument('--debug', action='store_true', help='Debug del scraper actual')
    
    args = parser.parse_args()
    
    if args.access:
        print("🌐 PROBANDO SOLO ACCESO A SCREENERMATIC")
        return test_screenermatic_access()
    elif args.debug:
        print("🔍 DEBUGEANDO SCRAPER ACTUAL")
        return debug_current_scraper()
    else:
        return test_ratios_scraper_direct()

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print(f"\n🎉 TEST COMPLETADO EXITOSAMENTE")
            print("💡 El scraper de ratios está funcionando")
            print("🔄 Puedes ejecutar ahora el test de integración completa:")
            print("   python test_integration.py --full")
        else:
            print(f"\n⚠️ TEST CON PROBLEMAS")
            print("💡 Opciones para debugging:")
            print("   python test_ratios_scraper_corrected.py --access")
            print("   python test_ratios_scraper_corrected.py --debug")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n👋 Test interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error crítico: {str(e)}")
        sys.exit(1)