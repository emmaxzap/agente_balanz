# verify_database.py - Script para verificar datos en la base de datos
"""
Script para verificar y analizar los datos en la base de datos de Supabase

Uso:
    python verify_database.py                    # Resumen general
    python verify_database.py --fecha 2025-01-15 # Datos de fecha específica
    python verify_database.py --ticker AAPL      # Histórico de un ticker específico
    python verify_database.py --stats            # Estadísticas detalladas
"""

import sys
import argparse
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from database.database_manager import SupabaseManager

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Verificador de datos en la base de datos de Balanz',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python verify_database.py                       # Resumen general
  python verify_database.py --fecha 2025-01-15    # Datos de fecha específica
  python verify_database.py --ticker AAPL         # Histórico de AAPL
  python verify_database.py --stats               # Estadísticas detalladas
  python verify_database.py --last-days 7        # Últimos 7 días
        """
    )
    
    parser.add_argument(
        '--fecha',
        type=str,
        help='Verificar datos de fecha específica (formato: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--ticker',
        type=str,
        help='Mostrar histórico de un ticker específico'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas detalladas'
    )
    
    parser.add_argument(
        '--last-days',
        type=int,
        default=7,
        help='Mostrar datos de los últimos N días (default: 7)'
    )
    
    return parser.parse_args()

def validate_date(date_string):
    """Valida el formato de fecha"""
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ Formato de fecha inválido: {date_string}")
        print("   Formato esperado: YYYY-MM-DD")
        return None

def mostrar_resumen_general(db):
    """Muestra un resumen general de la base de datos"""
    print("📊 RESUMEN GENERAL DE LA BASE DE DATOS")
    print("=" * 50)
    
    # Resumen de activos
    df_activos = db.obtener_resumen_activos()
    
    # Estadísticas de hoy
    hoy = date.today()
    print(f"\n📅 Datos de hoy ({hoy}):")
    stats_hoy = db.obtener_estadisticas_fecha(hoy)
    
    # Estadísticas de ayer
    ayer = hoy - timedelta(days=1)
    print(f"\n📅 Datos de ayer ({ayer}):")
    stats_ayer = db.obtener_estadisticas_fecha(ayer)

def mostrar_datos_fecha(db, fecha):
    """Muestra datos de una fecha específica"""
    print(f"📅 DATOS DE LA FECHA: {fecha}")
    print("=" * 50)
    
    # Estadísticas de la fecha
    stats = db.obtener_estadisticas_fecha(fecha)
    
    if stats and stats['total_registros'] > 0:
        # Obtener registros de la fecha
        df_fecha = db.obtener_registros_fecha(fecha)
        
        if not df_fecha.empty:
            print(f"\n📋 Muestra de datos (primeros 10 registros):")
            columns_to_show = ['ticker', 'precio_actual', 'precio_cierre_anterior']
            if 'created_at' in df_fecha.columns:
                columns_to_show.append('created_at')
            
            print(df_fecha[columns_to_show].head(10).to_string(index=False))
            
            # Estadísticas de precios
            print(f"\n📊 Estadísticas de precios:")
            print(f"   💰 Precio promedio: ${df_fecha['precio_actual'].mean():.2f}")
            print(f"   📈 Precio máximo: ${df_fecha['precio_actual'].max():.2f}")
            print(f"   📉 Precio mínimo: ${df_fecha['precio_actual'].min():.2f}")
            
            # Top 5 más caros
            top_caros = df_fecha.nlargest(5, 'precio_actual')
            print(f"\n🔝 Top 5 más caros:")
            for _, row in top_caros.iterrows():
                print(f"   {row['ticker']}: ${row['precio_actual']:,.2f}")
    else:
        print("⚠️ No hay datos para esta fecha")

def mostrar_historico_ticker(db, ticker):
    """Muestra el histórico de un ticker específico"""
    print(f"📈 HISTÓRICO DEL TICKER: {ticker}")
    print("=" * 50)
    
    # Obtener histórico de 30 días
    df_historico = db.obtener_historico(ticker, dias=30)
    
    if not df_historico.empty:
        print(f"\n📊 Últimos {len(df_historico)} registros:")
        
        columns_to_show = ['fecha', 'precio_actual', 'precio_cierre_anterior']
        if 'created_at' in df_historico.columns:
            df_historico['created_at'] = pd.to_datetime(df_historico['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            columns_to_show.append('created_at')
        
        print(df_historico[columns_to_show].to_string(index=False))
        
        # Estadísticas del ticker
        print(f"\n📊 Estadísticas de {ticker}:")
        print(f"   💰 Precio actual: ${df_historico.iloc[0]['precio_actual']:,.2f}")
        print(f"   📈 Precio promedio (30d): ${df_historico['precio_actual'].mean():.2f}")
        print(f"   📊 Máximo (30d): ${df_historico['precio_actual'].max():.2f}")
        print(f"   📊 Mínimo (30d): ${df_historico['precio_actual'].min():.2f}")
        
        # Calcular variación si hay datos anteriores
        if len(df_historico) > 1:
            precio_actual = df_historico.iloc[0]['precio_actual']
            precio_anterior = df_historico.iloc[1]['precio_actual']
            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100
            emoji = "🔺" if variacion > 0 else "🔻" if variacion < 0 else "➡️"
            print(f"   {emoji} Variación: {variacion:+.2f}%")
    else:
        print(f"⚠️ No se encontraron datos para el ticker {ticker}")

def mostrar_estadisticas_detalladas(db, last_days):
    """Muestra estadísticas detalladas de los últimos días"""
    print(f"📊 ESTADÍSTICAS DE LOS ÚLTIMOS {last_days} DÍAS")
    print("=" * 50)
    
    hoy = date.today()
    
    print(f"\n📅 Resumen por día:")
    print("-" * 40)
    
    total_dias = 0
    total_registros = 0
    
    for i in range(last_days):
        fecha = hoy - timedelta(days=i)
        stats = db.obtener_estadisticas_fecha(fecha)
        
        if stats:
            if stats['total_registros'] > 0:
                total_dias += 1
                total_registros += stats['total_registros']
                
            print(f"{fecha} | Total: {stats['total_registros']:3d} | Acciones: {stats['acciones']:3d} | CEDEARs: {stats['cedears']:3d}")
    
    print(f"\n📊 Resumen general ({last_days} días):")
    print(f"   📅 Días con datos: {total_dias}/{last_days}")
    print(f"   📊 Total registros: {total_registros:,}")
    if total_dias > 0:
        print(f"   📈 Promedio por día: {total_registros/total_dias:.1f}")

def main():
    """Función principal del script"""
    print("🔍 VERIFICADOR DE BASE DE DATOS - BALANZ SCRAPER")
    print("="*60)
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Inicializar manager
    db = SupabaseManager()
    
    # Probar conexión
    if not db.test_connection():
        print("❌ No se pudo conectar a la base de datos")
        return False
    
    try:
        if args.ticker:
            # Mostrar histórico de ticker específico
            mostrar_historico_ticker(db, args.ticker.upper())
            
        elif args.fecha:
            # Mostrar datos de fecha específica
            fecha = validate_date(args.fecha)
            if fecha:
                mostrar_datos_fecha(db, fecha)
            else:
                return False
                
        elif args.stats:
            # Mostrar estadísticas detalladas
            mostrar_estadisticas_detalladas(db, args.last_days)
            
        else:
            # Mostrar resumen general
            mostrar_resumen_general(db)
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
        sys.exit(130)