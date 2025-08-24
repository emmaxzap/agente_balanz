# main.py - Script principal para extraer cotizaciones de Balanz
"""
Script principal para extraer cotizaciones de Balanz y guardar en Supabase

Uso:
    python main.py                 # Ejecución normal
    python main.py --headless      # Ejecución sin interfaz gráfica
    python main.py --help          # Mostrar ayuda
"""

import sys
import argparse
from datetime import date
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scraper.web_scraper import WebScraperPlaywright
from database.database_manager import procesar_y_guardar_datos
from config import LOGIN_CONFIG

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Extractor de cotizaciones de Balanz',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    # Ejecutar con interfaz gráfica
  python main.py --headless         # Ejecutar sin interfaz
  python main.py --date 2025-01-15  # Especificar fecha de datos
  python main.py --only-acciones    # Solo extraer acciones
  python main.py --only-cedears     # Solo extraer CEDEARs
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
        help='Fecha de los datos (formato: YYYY-MM-DD). Por defecto: hoy'
    )
    
    parser.add_argument(
        '--only-acciones',
        action='store_true',
        help='Extraer solo acciones'
    )
    
    parser.add_argument(
        '--only-cedears',
        action='store_true',
        help='Extraer solo CEDEARs'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar información detallada de debug'
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
    print(f"📅 Fecha de datos: {fecha_datos or date.today()}")
    print(f"🖥️ Modo headless: {'Sí' if args.headless else 'No'}")
    print(f"📈 Extraer acciones: {'Sí' if not args.only_cedears else 'No'}")
    print(f"🏛️ Extraer CEDEARs: {'Sí' if not args.only_acciones else 'No'}")
    print(f"🔍 Modo verbose: {'Sí' if args.verbose else 'No'}")

def main():
    """Función principal del script"""
    print("🚀 BALANZ SCRAPER v2.0")
    print("="*60)
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Validar fecha
    fecha_datos = validate_date(args.date) if args.date else None
    if args.date and not fecha_datos:
        return False
    
    # Configurar qué extraer
    extract_acciones = not args.only_cedears
    extract_cedears = not args.only_acciones
    
    # Mostrar configuración
    show_config_info(args, fecha_datos)
    
    # Inicializar scraper
    scraper = WebScraperPlaywright(headless=args.headless)
    
    try:
        # Iniciar navegador
        scraper.start_browser()
        
        # Realizar login
        print(f"\n🔐 INICIANDO LOGIN")
        print("-" * 40)
        
        login_success = scraper.login(
            url=LOGIN_CONFIG['url'],
            username=LOGIN_CONFIG['username'],
            password=LOGIN_CONFIG['password']
        )
        
        if not login_success:
            print("❌ Login falló - terminando ejecución")
            return False
        
        print("🎉 Login exitoso!")
        
        # Extraer datos
        df_acciones, df_cedears = extract_data(
            scraper, extract_acciones, extract_cedears, args.verbose
        )
        
        # Mostrar resumen
        has_data = show_extraction_summary(df_acciones, df_cedears)
        
        if not has_data:
            print("⚠️ No se extrajeron datos - terminando")
            return False
        
        # Guardar en base de datos
        print(f"\n💾 GUARDANDO EN BASE DE DATOS")
        print("-" * 40)
        
        resultado = procesar_y_guardar_datos(
            df_acciones=df_acciones if df_acciones is not None and not df_acciones.empty else None,
            df_cedears=df_cedears if df_cedears is not None and not df_cedears.empty else None,
            fecha_datos=fecha_datos
        )
        
        # Resultado final
        print(f"\n{'='*60}")
        if resultado:
            print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
            print("✅ Todos los datos fueron extraídos y guardados")
        else:
            print("⚠️ PROCESO COMPLETADO CON ERRORES")
            print("❌ Hubo problemas guardando en la base de datos")
        
        print("="*60)
        return resultado
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Proceso interrumpido por el usuario")
        return False
        
    except Exception as e:
        print(f"\n❌ Error general: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False
    
    finally:
        scraper.close()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
        sys.exit(130)  # Código estándar para interrupción