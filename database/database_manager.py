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
        print("✅ Conexión con Supabase establecida")
    
    def test_connection(self):
        """Prueba la conexión con Supabase"""
        try:
            # Intentar hacer una consulta simple
            result = self.supabase.table('activos').select('count').execute()
            print("🔗 Conexión con Supabase funcionando correctamente")
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return False
    
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
                # Insertar todos los activos
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
        """
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            precios_data = []
            insertados = 0
            errores = 0
            
            print(f"\n📊 Insertando precios para fecha: {fecha_datos}")
            print(f"📋 Total de registros a procesar: {len(df_precios)}")
            
            for _, row in df_precios.iterrows():
                try:
                    # Determinar el nombre de la columna del ticker
                    ticker_col = 'accion' if 'accion' in df_precios.columns else 'cedear'
                    ticker = row[ticker_col]
                    
                    precio_data = {
                        'ticker': ticker,
                        'fecha': fecha_datos.isoformat(),
                        'precio_actual': float(row['precio']),
                        'precio_cierre_anterior': float(row['precio_cierre_anterior']) if 'precio_cierre_anterior' in df_precios.columns and pd.notna(row['precio_cierre_anterior']) else None
                    }
                    
                    precios_data.append(precio_data)
                    insertados += 1
                    
                except Exception as e:
                    print(f"⚠️ Error procesando {ticker}: {str(e)}")
                    errores += 1
                    continue
            
            if precios_data:
                # Inserción masiva
                result = self.supabase.table('precios_historico').upsert(precios_data).execute()
                print(f"✅ {len(precios_data)} precios insertados exitosamente")
                print(f"📊 Resumen: {insertados} procesados, {errores} errores")
                return len(precios_data)
            else:
                print("⚠️ No hay datos para insertar")
                return 0
                
        except Exception as e:
            print(f"❌ Error en inserción masiva de precios: {str(e)}")
            return 0
    
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
                .order('tipo', 'ticker')\
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
            return pd.DataFrame()

def procesar_y_guardar_datos(df_acciones=None, df_cedears=None, fecha_datos=None):
    """
    Función principal que procesa y guarda los datos extraídos en Supabase
    """
    print("\n" + "="*60)
    print("🗄️ INICIANDO GUARDADO EN BASE DE DATOS")
    print("="*60)
    
    # Crear instancia del manager
    db = SupabaseManager()
    
    # Probar conexión
    if not db.test_connection():
        print("❌ No se pudo conectar a la base de datos")
        return False
    
    try:
        # 1. Crear/actualizar activos en el maestro
        print("\n📋 Paso 1: Actualizando maestro de activos...")
        activos_creados = db.crear_activos_desde_dataframes(df_acciones, df_cedears)
        
        # 2. Insertar precios históricos
        print("\n💰 Paso 2: Insertando precios históricos...")
        
        precios_insertados = 0
        
        # Insertar acciones
        if df_acciones is not None and not df_acciones.empty:
            print("\n📈 Insertando precios de ACCIONES...")
            insertados = db.insertar_precios_masivo(df_acciones, fecha_datos)
            precios_insertados += insertados
        
        # Insertar CEDEARs
        if df_cedears is not None and not df_cedears.empty:
            print("\n🏛️ Insertando precios de CEDEARS...")
            insertados = db.insertar_precios_masivo(df_cedears, fecha_datos)
            precios_insertados += insertados
        
        # 3. Mostrar resumen
        print("\n📊 Paso 3: Resumen final...")
        db.obtener_resumen_activos()
        
        print(f"\n🎯 RESUMEN DE LA OPERACIÓN:")
        print(f"   📋 Activos procesados: {activos_creados}")
        print(f"   💰 Precios insertados: {precios_insertados}")
        print(f"   📅 Fecha de datos: {fecha_datos or date.today()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en el proceso: {str(e)}")
        return False