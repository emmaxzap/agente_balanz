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

Uso:
    python main.py                 # Proceso completo
    python main.py --headless      # Sin interfaz gráfica
    python main.py --verbose       # Información detallada
"""

import sys
import argparse
from datetime import date
from pathlib import Path
from balanz_daily_report_scraper import ComprehensiveMarketAnalyzer
sys.path.append(str(Path(__file__).parent))

from scraper.web_scraper import WebScraperPlaywright
from database.database_manager import procesar_y_guardar_datos
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

Ejemplos de uso:
  python main.py                    # Proceso completo (precios + cartera)
  python main.py --headless         # Sin interfaz gráfica
  python main.py --date 2025-01-15  # Especificar fecha de datos
  python main.py --verbose          # Información detallada
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

def main():
    """Función principal del script"""
    print("🚀 BALANZ SCRAPER v2.1 - Con Administrador de Cartera")
    print("="*65)
    print("📋 FLUJO: Precios → BD → Cartera → Análisis → Recomendaciones")
    print("="*65)
    
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
        
        # PASO 3-6: ANÁLISIS COMPLETO DE CARTERA
        print(f"\n💼 PASO 3-6: ANÁLISIS COMPLETO DE CARTERA")
        print("=" * 55)
        print("🎯 Objetivo: Analizar cartera y generar recomendaciones")
        
        try:
            from portfolio_manager import PortfolioManager
            
            # Crear manager de cartera
            portfolio_manager = PortfolioManager(scraper.page)
            
            # Ejecutar análisis completo (incluye extracción de cartera + análisis)
            portfolio_success = portfolio_manager.run_complete_analysis()
            
            if not portfolio_success:
                print("⚠️ Errores en análisis de cartera")
                
        except ImportError as e:
            print(f"❌ Error importando PortfolioManager: {str(e)}")
            print("⚠️ Asegúrate de que portfolio_manager.py existe")
            print("⚠️ Asegúrate de que la carpeta analysis/ existe con technical_analyzer.py")
            print("⚠️ Asegúrate de que scraper/cartera_extractor.py existe")
            portfolio_success = False
        except Exception as e:
            print(f"❌ Error en análisis de cartera: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            portfolio_success = False
        
        # RESULTADO FINAL
        print(f"\n{'='*65}")
        print("🏁 RESUMEN FINAL DEL PROCESO")
        print("="*65)
        
        if has_market_data and portfolio_success:
            print("🎉 PROCESO COMPLETO EXITOSO")
            print("✅ 1-2: Precios extraídos y guardados en BD")
            print("✅ 3-6: Cartera analizada y recomendaciones generadas")
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
        
        print("="*65)
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