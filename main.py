# main.py - Script principal para extraer cotizaciones de Balanz
"""
Script principal para extraer cotizaciones de Balanz y administrador de cartera

FLUJO COMPLETO:
1. Descarga precios de mercado (acciones + CEDEARs) 
2. Inserta precios en BD (fecha = ayer)
3. Descarga cartera personal (activos + dinero disponible)
4. Analiza activos de cartera para decisiones de venta
5. Busca oportunidades de compra en el mercado
6. Genera recomendaciones completas
7. NUEVO: Análisis integral con reporte de mercado y ratios fundamentales

Uso:
    python main.py                 # Proceso completo
    python main.py --headless      # Sin interfaz gráfica
    python main.py --verbose       # Información detallada
"""

import sys
import argparse
from datetime import date
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from scraper.web_scraper import WebScraperPlaywright
from database.database_manager import procesar_y_guardar_datos, SupabaseManager
from config import LOGIN_CONFIG

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Extractor de cotizaciones y administrador de cartera completo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flujo completo del script:
  1. 📊 Descarga precios de mercado (acciones + CEDEARs)
  2. 💾 Inserta precios en BD (fecha = ayer)
  3. 💼 Descarga tu cartera personal
  4. 🔍 Analiza tus activos para venta
  5. 🎯 Busca oportunidades de compra
  6. 📋 Genera recomendaciones
  7. 🌍 Análisis integral con contexto de mercado

Ejemplos de uso:
  python main.py                    # Proceso completo (precios + cartera)
  python main.py --headless         # Sin interfaz gráfica
  python main.py --date 2025-01-15  # Especificar fecha de datos
  python main.py --verbose          # Información detallada
  python main.py --basic            # Solo análisis básico (sin reporte/ratios)
        """
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Ejecutar navegador sin interfaz gráfica'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Fecha de los datos (formato: YYYY-MM-DD). Por defecto: ayer'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar información detallada de debug'
    )
    
    parser.add_argument(
        '--check-db',
        action='store_true',
        help='Solo verificar estado de la base de datos'
    )
    
    parser.add_argument(
        '--basic',
        action='store_true',
        help='Solo análisis básico sin reporte de mercado ni ratios'
    )
    
    return parser.parse_args()

def validate_date(date_string):
    """Valida el formato de fecha"""
    if not date_string:
        return None
    
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        print(f"❌ Formato de fecha inválido: {date_string}")
        print("   Formato esperado: YYYY-MM-DD")
        return None

def check_database_status(fecha_datos=None):
    """Verifica el estado de la base de datos"""
    from database.database_manager import SupabaseManager
    
    print(f"🔍 PRE-VERIFICACIÓN DE BASE DE DATOS")
    print("-" * 50)
    print("🔍 VERIFICANDO ESTADO DE LA BASE DE DATOS")
    print("-" * 50)
    
    db = SupabaseManager()
    if not db.test_connection():
        return False
    
    return True

def extract_data(scraper, extract_acciones=True, extract_cedears=True, verbose=False):
    """Extrae los datos según los parámetros especificados"""
    df_acciones = None
    df_cedears = None
    
    # Extraer acciones
    if extract_acciones:
        print("\n📈 EXTRAYENDO ACCIONES")
        print("-" * 40)
        df_acciones = scraper.extract_stock_prices_to_df()
        
        if not df_acciones.empty:
            print(f"✅ {len(df_acciones)} acciones extraídas")
            if verbose:
                print("📋 Muestra de datos:")
                print(df_acciones[['accion', 'precio', 'precio_cierre_anterior']].head(10))
            else:
                print("📋 Muestra de datos:")
                print(df_acciones[['accion', 'precio', 'precio_cierre_anterior']].head())
        else:
            print("⚠️ No se extrajeron acciones")
    
    # Extraer CEDEARs
    if extract_cedears:
        print("\n🏛️ EXTRAYENDO CEDEARS")
        print("-" * 40)
        df_cedears = scraper.extract_cedears_to_df()
        
        if not df_cedears.empty:
            print(f"✅ {len(df_cedears)} CEDEARs extraídos")
            if verbose:
                print("📋 Muestra de datos:")
                cols = ['cedear', 'precio']
                if 'precio_cierre_anterior' in df_cedears.columns:
                    cols.append('precio_cierre_anterior')
                print(df_cedears[cols].head(10))
            else:
                print("📋 Muestra de datos:")
                cols = ['cedear', 'precio'] 
                if 'precio_cierre_anterior' in df_cedears.columns:
                    cols.append('precio_cierre_anterior')
                print(df_cedears[cols].head())
        else:
            print("⚠️ No se extrajeron CEDEARs")
    
    return df_acciones, df_cedears

def show_extraction_summary(df_acciones, df_cedears):
    """Muestra resumen de la extracción"""
    print(f"\n🎯 RESUMEN DE EXTRACCIÓN")
    print("=" * 40)
    
    acciones_count = len(df_acciones) if df_acciones is not None and not df_acciones.empty else 0
    cedears_count = len(df_cedears) if df_cedears is not None and not df_cedears.empty else 0
    
    print(f"📈 Acciones extraídas: {acciones_count}")
    print(f"🏛️ CEDEARs extraídos: {cedears_count}")
    print(f"📊 Total instrumentos: {acciones_count + cedears_count}")
    
    return acciones_count > 0 or cedears_count > 0

def show_config_info(args, fecha_datos):
    """Muestra información de configuración"""
    print(f"📅 Fecha de datos: {fecha_datos or 'ayer (automático)'}")
    print(f"🖥️ Modo headless: {'Sí' if args.headless else 'No'}")
    print(f"🔍 Modo verbose: {'Sí' if args.verbose else 'No'}")
    print(f"🎯 Análisis básico: {'Sí' if args.basic else 'No (análisis integral)'}")

def run_portfolio_analysis(scraper, portfolio_data, basic_mode=False):
    """Ejecuta el análisis de cartera según el modo especificado"""
    
    if basic_mode:
        print(f"\n💼 MODO BÁSICO: ANÁLISIS ESTÁNDAR")
        print("=" * 45)
        print("🎯 Ejecutando solo análisis técnico estándar")
        
        try:
            from portfolio_manager import PortfolioManager
            
            portfolio_manager = PortfolioManager(scraper.page)
            portfolio_success = portfolio_manager.run_complete_analysis()
            
            return portfolio_success
            
        except Exception as e:
            print(f"❌ Error en análisis básico: {str(e)}")
            return False
    
    else:
        print(f"\n🌍 MODO INTEGRAL: TÉCNICO + FUNDAMENTAL + MERCADO")
        print("=" * 65)
        print("🎯 Análisis completo con reporte de mercado y ratios fundamentales")
        
        try:
            # NUEVO: ANÁLISIS INTEGRAL CON REPORTE Y RATIOS
            from comprehensive_market_analyzer import ComprehensiveMarketAnalyzer
            
            # Crear analizador integral
            comprehensive_analyzer = ComprehensiveMarketAnalyzer(scraper.page, SupabaseManager())
            
            # Ejecutar análisis completo
            integral_result = comprehensive_analyzer.run_comprehensive_analysis(portfolio_data)
            
            if integral_result and integral_result.get('comprehensive_analysis'):
                print("✅ Análisis integral completado con éxito")
                
                # Mostrar resumen del análisis integral
                show_integral_analysis_summary(integral_result)
                
                return True
            else:
                print("⚠️ Análisis integral con problemas - usando análisis estándar")
                # Fallback a tu análisis original
                from portfolio_manager import PortfolioManager
                
                portfolio_manager = PortfolioManager(scraper.page)
                portfolio_success = portfolio_manager.run_complete_analysis()
                
                return portfolio_success

        except ImportError as e:
            print(f"⚠️ Módulos de análisis integral no disponibles: {str(e)}")
            print("🔄 Usando análisis estándar...")
            
            # Fallback a análisis original
            from portfolio_manager import PortfolioManager
            
            portfolio_manager = PortfolioManager(scraper.page)
            portfolio_success = portfolio_manager.run_complete_analysis()
            
            return portfolio_success
            
        except Exception as e:
            print(f"❌ Error en análisis integral: {str(e)}")
            print("🔄 Usando análisis estándar...")
            
            # Fallback a análisis original  
            from portfolio_manager import PortfolioManager
            
            portfolio_manager = PortfolioManager(scraper.page)
            portfolio_success = portfolio_manager.run_complete_analysis()
            
            return portfolio_success

def show_integral_analysis_summary(integral_result):
    """Muestra resumen del análisis integral"""
    print(f"\n📊 RESUMEN DEL ANÁLISIS INTEGRAL")
    print("=" * 45)
    
    # Datos del reporte de mercado
    market_report = integral_result.get('market_report', {})
    if market_report:
        sentiment = market_report.get('portfolio_insights', {}).get('sentiment_general', 'N/A')
        tickers_mencionados = market_report.get('portfolio_insights', {}).get('tickers_mencionados', {})
        
        print(f"📰 Reporte de mercado: ✅ Obtenido")
        print(f"📊 Sentiment general: {sentiment}")
        print(f"🎯 Tus activos mencionados: {len(tickers_mencionados)}")
        
        for ticker, info in tickers_mencionados.items():
            if info.get('mencionado'):
                performance = info.get('performance_reportada', 'N/A')
                print(f"   • {ticker}: {performance}")
    
    # Datos fundamentales
    portfolio_data = integral_result.get('portfolio_data', {})
    activos_con_ratios = 0
    
    for activo in portfolio_data.get('activos', []):
        if 'fundamental_ratios' in activo:
            activos_con_ratios += 1
    
    print(f"📊 Ratios fundamentales: {activos_con_ratios} activos analizados")
    
    # Análisis de Claude
    comprehensive_analysis = integral_result.get('comprehensive_analysis', {})
    if comprehensive_analysis.get('claude_api_available', False):
        print(f"🤖 Análisis de Claude: ✅ Disponible")
        
        acciones_inmediatas = comprehensive_analysis.get('acciones_inmediatas', [])
        acciones_corto_plazo = comprehensive_analysis.get('acciones_corto_plazo', [])
        
        print(f"⚡ Acciones inmediatas: {len(acciones_inmediatas)}")
        print(f"📅 Acciones corto plazo: {len(acciones_corto_plazo)}")
    else:
        print(f"🤖 Análisis de Claude: ❌ No disponible")
    
    print(f"🔥 Nivel de confianza: {integral_result.get('confidence_level', 'estándar')}")

def main():
    """Función principal del script"""
    print("🚀 BALANZ SCRAPER v3.0 - Con Análisis Integral")
    print("="*70)
    print("📋 FLUJO: Precios → BD → Cartera → Análisis Integral → Recomendaciones")
    print("="*70)
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Validar fecha
    fecha_datos = validate_date(args.date) if args.date else None
    if args.date and not fecha_datos:
        return False
    
    # Si solo queremos verificar la base de datos
    if args.check_db:
        return check_database_status(fecha_datos)
    
    # Mostrar configuración
    show_config_info(args, fecha_datos)
    
    # Verificar estado de la base antes de empezar
    check_database_status(fecha_datos)
    
    # Inicializar scraper
    scraper = WebScraperPlaywright(headless=args.headless)
    
    try:
        # Iniciar navegador
        print("\n🔧 Iniciando navegador...")
        scraper.start_browser()
        print("✅ Navegador iniciado correctamente")
        
        # Realizar login
        print(f"\n🔐 INICIANDO LOGIN")
        print("-" * 40)
        print(f"🌐 Navegando a: {LOGIN_CONFIG['url']}")
        
        login_success = scraper.login(
            url=LOGIN_CONFIG['url'],
            username=LOGIN_CONFIG['username'],
            password=LOGIN_CONFIG['password']
        )
        
        if not login_success:
            print("❌ Login falló - terminando ejecución")
            return False
        
        print("🎉 Login exitoso!")
        
        # PASO 1-2: EXTRAER PRECIOS DE MERCADO Y GUARDAR EN BD
        print(f"\n📈 PASO 1-2: EXTRAYENDO PRECIOS DEL MERCADO")
        print("=" * 55)
        print("🎯 Objetivo: Obtener precios actuales para análisis")
        
        # Siempre extraer ambos tipos para análisis completo
        df_acciones, df_cedears = extract_data(
            scraper, extract_acciones=True, extract_cedears=True, verbose=args.verbose
        )
        
        # Mostrar resumen
        has_market_data = show_extraction_summary(df_acciones, df_cedears)
        
        if has_market_data:
            # Guardar en base de datos
            print(f"\n💾 GUARDANDO PRECIOS EN BASE DE DATOS")
            print("-" * 50)
            print("🎯 Guardando precios de cierre de ayer en BD")
            
            resultado_bd = procesar_y_guardar_datos(
                df_acciones=df_acciones if df_acciones is not None and not df_acciones.empty else None,
                df_cedears=df_cedears if df_cedears is not None and not df_cedears.empty else None,
                fecha_datos=fecha_datos
            )
            
            if not resultado_bd:
                print("⚠️ Errores guardando datos de mercado")
        else:
            print("❌ No se pudieron extraer datos del mercado")
            print("❌ No se puede continuar con análisis de cartera")
            return False
        
        # PASO 3: EXTRAER DATOS DE CARTERA
        print(f"\n💼 PASO 3: EXTRAYENDO DATOS DE CARTERA")
        print("=" * 50)
        print("🎯 Objetivo: Obtener tu cartera actual")
        
        try:
            from scraper.cartera_extractor import CarteraExtractor
            
            cartera_extractor = CarteraExtractor(scraper.page)
            portfolio_data = cartera_extractor.extract_portfolio_data()
            
            if not portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False
            
            print("✅ Datos de cartera extraídos correctamente")
            
        except Exception as e:
            print(f"❌ Error extrayendo cartera: {str(e)}")
            return False
        
        # PASO 4-6: ANÁLISIS COMPLETO DE CARTERA
        portfolio_success = run_portfolio_analysis(scraper, portfolio_data, args.basic)
        
        # RESULTADO FINAL
        print(f"\n{'='*70}")
        print("🏁 RESUMEN FINAL DEL PROCESO")
        print("="*70)
        
        if has_market_data and portfolio_success:
            print("🎉 PROCESO COMPLETO EXITOSO")
            print("✅ 1-2: Precios extraídos y guardados en BD")
            print("✅ 3: Cartera extraída correctamente")
            if args.basic:
                print("✅ 4-6: Análisis técnico estándar completado")
            else:
                print("✅ 4-6: Análisis integral completado (técnico + fundamental + mercado)")
            print("\n💡 Revisa las recomendaciones arriba para tomar decisiones")
            final_success = True
            
        elif has_market_data and not portfolio_success:
            print("🎉 PROCESO PARCIALMENTE EXITOSO")
            print("✅ 1-2: Precios extraídos y guardados en BD")
            print("⚠️ 3-6: Problemas con análisis de cartera")
            print("\n💡 Los precios están actualizados, pero no hay análisis de cartera")
            final_success = True
            
        elif not has_market_data and portfolio_success:
            print("⚠️ PROCESO PARCIALMENTE EXITOSO")
            print("❌ 1-2: Problemas extrayendo precios del mercado")
            print("✅ 3-6: Cartera analizada")
            print("\n⚠️ Análisis basado en datos históricos, no precios actuales")
            final_success = False
            
        else:
            print("❌ PROCESO CON ERRORES MÚLTIPLES")
            print("❌ 1-2: Problemas extrayendo precios del mercado")
            print("❌ 3-6: Problemas con análisis de cartera")
            print("\n🔧 Revisa la configuración y conexiones")
            final_success = False
        
        # Mostrar diferencias entre modos
        if not args.basic:
            print("\n🌟 VENTAJAS DEL ANÁLISIS INTEGRAL:")
            print("   📰 Contexto de mercado actual desde reporte Balanz")
            print("   📊 Ratios fundamentales (P/E, ROE, etc.)")
            print("   🤖 Claude combina técnico + fundamental + contexto")
            print("   🎯 Recomendaciones más precisas y contextualizadas")
        
        print("="*70)
        return final_success
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Proceso interrumpido por el usuario")
        return False
        
    except Exception as e:
        print(f"\n❌ Error general del sistema: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False
    
    finally:
        print("\n🔧 Cerrando navegador...")
        scraper.close()
        print("✅ Navegador cerrado")

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n👋 Finalizando script...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
        sys.exit(130)  # Código estándar para interrupción