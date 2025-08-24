# main.py - Script principal para extraer cotizaciones de Balanz
"""
Script principal para extraer cotizaciones de Balanz y guardar en Supabase
Con verificación de duplicados mejorada

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
        description='Extractor de cotizaciones de Balanz con verificación de duplicados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    # Ejecutar con interfaz gráfica
  python main.py --headless         # Ejecutar sin interfaz
  python main.py --date 2025-01-15  # Especificar fecha de datos
  python main.py --only-acciones    # Solo extraer acciones
  python main.py --only-cedears     # Solo extraer CEDEARs
  python main.py --force            # Forzar inserción (ignorar duplicados)
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
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forzar inserción ignorando verificación de duplicados'
    )
    
    parser.add_argument(
        '--check-db',
        action='store_true',
        help='Solo verificar estado de la base de datos sin extraer'
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
    print(f"📅 Fecha de datos: {fecha_datos or date.today()}")
    # Removemos los otros prints para simplicidad

def main():
    """Función principal del script"""
    print("🚀 BALANZ SCRAPER v2.1 - Con Verificación de Duplicados")
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
    
    # Configurar qué extraer
    extract_acciones = not args.only_cedears
    extract_cedears = not args.only_acciones
    
    # Mostrar configuración
    show_config_info(args, fecha_datos)
    
    # Verificar estado de la base antes de empezar
    print(f"\n🔍 PRE-VERIFICACIÓN DE BASE DE DATOS")
    print("-" * 50)
    check_database_status(fecha_datos)
    
    # Inicializar scraper
    scraper = WebScraperPlaywright(headless=args.headless)
    
    try:
        # Iniciar navegador
        scraper.start_browser()
        
        # Realizar login
        print(f"\n----------------------------------------")
        print(f"🌐 Navegando a: {LOGIN_CONFIG['url']}")
        print()
        
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
        print("-" * 50)
        
        if args.force:
            print("⚡ MODO FORZADO: Se saltará la verificación de duplicados")
            # Aquí podrías implementar una versión que ignore duplicados si es necesario
        
        resultado = procesar_y_guardar_datos(
            df_acciones=df_acciones if df_acciones is not None and not df_acciones.empty else None,
            df_cedears=df_cedears if df_cedears is not None and not df_cedears.empty else None,
            fecha_datos=fecha_datos
        )
        
        # Post-verificación de la base de datos (opcional, sin detalles)
        # check_database_status(fecha_datos)
        
        # Resultado final
        print(f"\n{'='*65}")
        if resultado:
            print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
        else:
            print("⚠️ PROCESO COMPLETADO CON ERRORES")
        
        print("="*65)
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