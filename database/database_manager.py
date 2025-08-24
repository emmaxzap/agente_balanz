# database/database_manager.py - Gestión de base de datos con Supabase
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
import os
from dotenv import load_dotenv
from config import SUPABASE_CONFIG

class SupabaseManager:
    def __init__(self):
        """Inicializa la conexión con Supabase"""
        # Cargar variables de entorno si existen
        load_dotenv()
        
        # Credenciales de Supabase desde config
        self.url = SUPABASE_CONFIG['url']
        self.key = SUPABASE_CONFIG['key']
        
        # Crear cliente de Supabase
        self.supabase: Client = create_client(self.url, self.key)
        # Removemos el print de conexión establecida
    
    def test_connection(self):
        """Prueba la conexión con Supabase"""
        try:
            # Intentar hacer una consulta simple
            result = self.supabase.table('activos').select('count').execute()
            print("✅ Conexión con Supabase establecida")
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return False
    
    def verificar_registros_existentes(self, df_precios, fecha_datos):
        """
        Verifica qué registros ya existen en la base de datos para evitar duplicados
        
        Args:
            df_precios: DataFrame con los precios a insertar
            fecha_datos: Fecha de los datos (date object)
        
        Returns:
            tuple: (registros_existentes_set, df_filtrado)
        """
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            # Determinar el nombre de la columna del ticker
            ticker_col = 'accion' if 'accion' in df_precios.columns else 'cedear'
            tickers_a_insertar = df_precios[ticker_col].tolist()
            
            # Consultar registros existentes para esta fecha
            result = self.supabase.table('precios_historico')\
                .select('ticker')\
                .eq('fecha', fecha_datos.isoformat())\
                .in_('ticker', tickers_a_insertar)\
                .execute()
            
            # Crear set con los tickers que ya existen
            registros_existentes = set()
            if result.data:
                registros_existentes = {record['ticker'] for record in result.data}
            
            # Filtrar DataFrame para excluir registros existentes
            df_filtrado = df_precios[~df_precios[ticker_col].isin(registros_existentes)]
            
            return registros_existentes, df_filtrado
            
        except Exception as e:
            print(f"❌ Error verificando registros existentes: {str(e)}")
            # En caso de error, devolver DataFrame original para no bloquear la inserción
            return set(), df_precios
    
    def crear_activos_desde_dataframes(self, df_acciones=None, df_cedears=None):
        """
        Crea activos en la tabla maestro desde los DataFrames extraídos
        """
        try:
            activos_nuevos = []
            
            # Procesar acciones
            if df_acciones is not None and not df_acciones.empty:
                for _, row in df_acciones.iterrows():
                    activos_nuevos.append({
                        'ticker': row['accion'],
                        'nombre': f"Empresa {row['accion']}",  # Nombre genérico por ahora
                        'tipo': 'ACCION'
                    })
            
            # Procesar CEDEARs
            if df_cedears is not None and not df_cedears.empty:
                for _, row in df_cedears.iterrows():
                    activos_nuevos.append({
                        'ticker': row['cedear'],
                        'nombre': f"Empresa {row['cedear']}",  # Nombre genérico por ahora
                        'tipo': 'CEDEAR'
                    })
            
            if activos_nuevos:
                # Insertar todos los activos (upsert maneja duplicados automáticamente)
                result = self.supabase.table('activos').upsert(activos_nuevos).execute()
                print(f"✅ {len(activos_nuevos)} activos creados/actualizados en el maestro")
                return len(activos_nuevos)
            else:
                print("⚠️ No hay activos nuevos para crear")
                return 0
                
        except Exception as e:
            print(f"❌ Error creando activos: {str(e)}")
            return 0
    
    def insertar_precios_masivo(self, df_precios, fecha_datos=None):
        """
        Inserta múltiples precios desde DataFrames (acciones y/o CEDEARs)
        con verificación de duplicados
        
        IMPORTANTE: Usa precio_cierre_anterior como el precio histórico definitivo
        y fecha debe ser del día anterior (fecha real del precio de cierre)
        """
        try:
            # Si no se especifica fecha, usar AYER (fecha del precio de cierre)
            if fecha_datos is None:
                from datetime import timedelta
                fecha_datos = date.today() - timedelta(days=1)
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            # Verificar registros existentes (sin prints)
            registros_existentes, df_filtrado = self.verificar_registros_existentes(df_precios, fecha_datos)
            
            # Si no hay nada nuevo que insertar
            if df_filtrado.empty:
                return 0
            
            # Procesar solo los registros nuevos
            precios_data = []
            registros_sin_precio_cierre = 0
            
            # Determinar el nombre de la columna del ticker
            ticker_col = 'accion' if 'accion' in df_filtrado.columns else 'cedear'
            
            for _, row in df_filtrado.iterrows():
                try:
                    ticker = row[ticker_col]
                    
                    # VALIDACIÓN CRÍTICA: Debe tener precio_cierre_anterior
                    if 'precio_cierre_anterior' not in df_filtrado.columns or pd.isna(row['precio_cierre_anterior']):
                        registros_sin_precio_cierre += 1
                        continue
                    
                    # Usar precio_cierre_anterior como precio histórico definitivo
                    precio_historico = float(row['precio_cierre_anterior'])
                    
                    precio_data = {
                        'ticker': ticker,
                        'fecha': fecha_datos.isoformat(),
                        'precio_actual': float(row['precio']) if 'precio' in df_filtrado.columns and pd.notna(row['precio']) else precio_historico,
                        'precio_cierre_anterior': precio_historico,
                        'precio_cierre': precio_historico
                    }
                    
                    precios_data.append(precio_data)
                    
                except Exception as e:
                    continue
            
            if precios_data:
                # Inserción masiva de solo registros nuevos
                result = self.supabase.table('precios_historico').insert(precios_data).execute()
                return len(precios_data)
            else:
                return 0
                
        except Exception as e:
            print(f"❌ Error en inserción masiva de precios: {str(e)}")
            return 0
    
    def obtener_registros_fecha(self, fecha_datos=None):
        """
        Obtiene todos los registros de una fecha específica para debug/verificación
        
        Args:
            fecha_datos: Fecha a consultar (date object o string)
        
        Returns:
            DataFrame con los registros de esa fecha
        """
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            result = self.supabase.table('precios_historico')\
                .select('*')\
                .eq('fecha', fecha_datos.isoformat())\
                .order('ticker')\
                .execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                print(f"📋 Registros encontrados para {fecha_datos}: {len(df)}")
                return df
            else:
                print(f"📋 No hay registros para la fecha {fecha_datos}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error obteniendo registros de fecha: {str(e)}")
            return pd.DataFrame()
    
    def obtener_ultimo_precio(self, ticker):
        """Obtiene el último precio registrado de un activo"""
        try:
            result = self.supabase.table('precios_historico')\
                .select('*')\
                .eq('ticker', ticker)\
                .order('fecha', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error obteniendo último precio de {ticker}: {str(e)}")
            return None
    
    def obtener_historico(self, ticker, dias=30):
        """Obtiene el histórico de precios de un activo"""
        try:
            result = self.supabase.table('precios_historico')\
                .select('*')\
                .eq('ticker', ticker)\
                .order('fecha', desc=True)\
                .limit(dias)\
                .execute()
            
            if result.data:
                return pd.DataFrame(result.data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error obteniendo histórico de {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def obtener_resumen_activos(self):
        """Obtiene un resumen de todos los activos"""
        try:
            result = self.supabase.table('activos')\
                .select('*')\
                .order('tipo', desc=False)\
                .order('ticker', desc=False)\
                .execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                print(f"\n📊 Resumen de activos en la base:")
                print(f"   📈 Acciones: {len(df[df['tipo'] == 'ACCION'])}")
                print(f"   🏛️ CEDEARs: {len(df[df['tipo'] == 'CEDEAR'])}")
                print(f"   📊 Total: {len(df)}")
                return df
            else:
                print("⚠️ No hay activos en la base de datos")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error obteniendo resumen: {str(e)}")
            # Fallback: intentar sin ordenamiento
            try:
                print("🔄 Intentando consulta simplificada...")
                result = self.supabase.table('activos')\
                    .select('*')\
                    .execute()
                
                if result.data:
                    df = pd.DataFrame(result.data)
                    print(f"\n📊 Resumen de activos en la base:")
                    print(f"   📈 Acciones: {len(df[df['tipo'] == 'ACCION'])}")
                    print(f"   🏛️ CEDEARs: {len(df[df['tipo'] == 'CEDEAR'])}")
                    print(f"   📊 Total: {len(df)}")
                    return df
                else:
                    print("⚠️ No hay activos en la base de datos")
                    return pd.DataFrame()
            except Exception as e2:
                print(f"❌ Error en consulta fallback: {str(e2)}")
                return pd.DataFrame()
    
    def obtener_estadisticas_fecha(self, fecha_datos=None):
        """
        Obtiene estadísticas detalladas de una fecha específica
        
        Args:
            fecha_datos: Fecha a analizar
        
        Returns:
            dict con estadísticas
        """
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            # Consultar todos los registros de la fecha
            result = self.supabase.table('precios_historico')\
                .select('ticker')\
                .eq('fecha', fecha_datos.isoformat())\
                .execute()
            
            if result.data:
                # Obtener los tickers para determinar el tipo
                tickers = [record['ticker'] for record in result.data]
                
                # Consultar tipos de activos para estos tickers
                activos_result = self.supabase.table('activos')\
                    .select('ticker, tipo')\
                    .in_('ticker', tickers)\
                    .execute()
                
                # Crear diccionario ticker -> tipo
                ticker_tipos = {}
                if activos_result.data:
                    ticker_tipos = {row['ticker']: row['tipo'] for row in activos_result.data}
                
                # Contar por tipo
                acciones = sum(1 for ticker in tickers if ticker_tipos.get(ticker) == 'ACCION')
                cedears = sum(1 for ticker in tickers if ticker_tipos.get(ticker) == 'CEDEAR')
                
                stats = {
                    'fecha': fecha_datos.isoformat(),
                    'total_registros': len(result.data),
                    'acciones': acciones,
                    'cedears': cedears
                }
                
                print(f"\n📊 Estadísticas para {fecha_datos}:")
                print(f"   📈 Acciones: {stats['acciones']}")
                print(f"   🏛️ CEDEARs: {stats['cedears']}")
                print(f"   📊 Total: {stats['total_registros']}")
                
                return stats
            else:
                stats = {
                    'fecha': fecha_datos.isoformat(),
                    'total_registros': 0,
                    'acciones': 0,
                    'cedears': 0
                }
                print(f"\n📊 Estadísticas para {fecha_datos}:")
                print(f"   📊 No hay datos para esta fecha")
                return stats
                
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {str(e)}")
            return None

def procesar_y_guardar_datos(df_acciones=None, df_cedears=None, fecha_datos=None):
    """
    Función principal que procesa y guarda los datos extraídos en Supabase
    con verificación de duplicados mejorada
    
    LÓGICA CORREGIDA:
    - Si no se especifica fecha_datos, usa AYER (fecha real del precio de cierre)
    - Guarda precio_cierre_anterior como precio histórico definitivo
    - Ignora precio_actual (es dinámico del día actual)
    """
    print("\n" + "="*60)
    print("🗄️ INICIANDO GUARDADO EN BASE DE DATOS")
    print("="*60)
    
    # Crear instancia del manager
    db = SupabaseManager()
    
    # Probar conexión (sin print extra)
    if not db.test_connection():
        print("❌ No se pudo conectar a la base de datos")
        return False
    
    try:
        # Establecer fecha correcta si no se especifica
        if fecha_datos is None:
            from datetime import timedelta
            fecha_datos = date.today() - timedelta(days=1)
        
        # Insertar precios históricos con verificación de duplicados
        precios_insertados = 0
        
        # Insertar acciones
        if df_acciones is not None and not df_acciones.empty:
            insertados = db.insertar_precios_masivo(df_acciones, fecha_datos)
            precios_insertados += insertados
        
        # Insertar CEDEARs
        if df_cedears is not None and not df_cedears.empty:
            insertados = db.insertar_precios_masivo(df_cedears, fecha_datos)
            precios_insertados += insertados
        
        print(f"\n🎯 RESUMEN:")
        print(f"   💰 Precios de cierre insertados: {precios_insertados}")
        print(f"   📅 Fecha de los precios: {fecha_datos}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en el proceso: {str(e)}")
        return False