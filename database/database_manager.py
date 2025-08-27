# database/database_manager.py - Gestión corregida con mapeo de IDs
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
import os
from dotenv import load_dotenv
from config import SUPABASE_CONFIG

class SupabaseManager:
    def __init__(self):
        """Inicializa la conexión con Supabase"""
        load_dotenv()
        
        self.url = SUPABASE_CONFIG['url']
        self.key = SUPABASE_CONFIG['key']
        
        self.supabase: Client = create_client(self.url, self.key)
        
        # Cache de mapeo ticker -> activo_id para eficiencia
        self._ticker_to_id_cache = {}
        self._load_ticker_cache()
    
    def _load_ticker_cache(self):
        """Carga el mapeo ticker -> activo_id en cache"""
        try:
            result = self.supabase.table('activos').select('id, ticker').execute()
            if result.data:
                self._ticker_to_id_cache = {row['ticker']: row['id'] for row in result.data}
                print(f"🗂️ Cache cargado: {len(self._ticker_to_id_cache)} activos")
        except Exception as e:
            print(f"⚠️ Error cargando cache de activos: {str(e)}")
    
    def _get_activo_id_by_ticker(self, ticker):
        """Obtiene el ID del activo por ticker, usando cache"""
        if ticker in self._ticker_to_id_cache:
            return self._ticker_to_id_cache[ticker]
        
        # Si no está en cache, buscarlo y actualizar cache
        try:
            result = self.supabase.table('activos')\
                .select('id')\
                .eq('ticker', ticker)\
                .single()\
                .execute()
            
            if result.data:
                activo_id = result.data['id']
                self._ticker_to_id_cache[ticker] = activo_id
                return activo_id
        except Exception as e:
            print(f"⚠️ No se encontró ID para ticker {ticker}: {str(e)}")
        
        return None
    
    def test_connection(self):
        """Prueba la conexión con Supabase"""
        try:
            result = self.supabase.table('activos').select('count').execute()
            print("✅ Conexión con Supabase establecida")
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return False
    
    def verificar_registros_existentes(self, df_precios, fecha_datos):
        """Verifica qué registros ya existen para evitar duplicados"""
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            ticker_col = 'accion' if 'accion' in df_precios.columns else 'cedear'
            tickers_a_insertar = df_precios[ticker_col].tolist()
            
            result = self.supabase.table('precios_historico')\
                .select('ticker')\
                .eq('fecha', fecha_datos.isoformat())\
                .in_('ticker', tickers_a_insertar)\
                .execute()
            
            registros_existentes = set()
            if result.data:
                registros_existentes = {record['ticker'] for record in result.data}
            
            df_filtrado = df_precios[~df_precios[ticker_col].isin(registros_existentes)]
            
            return registros_existentes, df_filtrado
            
        except Exception as e:
            print(f"❌ Error verificando registros existentes: {str(e)}")
            return set(), df_precios
    
    def crear_activos_desde_dataframes(self, df_acciones=None, df_cedears=None):
        """Crea activos nuevos y actualiza el cache"""
        try:
            activos_nuevos = []
            
            if df_acciones is not None and not df_acciones.empty:
                for _, row in df_acciones.iterrows():
                    ticker = row['accion']
                    if ticker not in self._ticker_to_id_cache:
                        activos_nuevos.append({
                            'ticker': ticker,
                            'nombre': f"Empresa {ticker}",
                            'tipo': 'ACCION'
                        })
            
            if df_cedears is not None and not df_cedears.empty:
                for _, row in df_cedears.iterrows():
                    ticker = row['cedear']
                    if ticker not in self._ticker_to_id_cache:
                        activos_nuevos.append({
                            'ticker': ticker,
                            'nombre': f"Empresa {ticker}",
                            'tipo': 'CEDEAR'
                        })
            
            if activos_nuevos:
                result = self.supabase.table('activos').upsert(activos_nuevos).execute()
                print(f"✅ {len(activos_nuevos)} activos nuevos creados")
                
                # Actualizar cache con los nuevos activos
                self._load_ticker_cache()
                
                return len(activos_nuevos)
            else:
                print("✅ Todos los activos ya existen")
                return 0
                
        except Exception as e:
            print(f"❌ Error creando activos: {str(e)}")
            return 0
    
    def insertar_precios_masivo(self, df_precios, fecha_datos=None):
        """
        Inserta precios históricos con mapeo correcto de activo_id
        SOLO guarda: activo_id, ticker, fecha, precio_cierre
        """
        try:
            if fecha_datos is None:
                from datetime import timedelta
                fecha_datos = date.today() - timedelta(days=1)
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            # Verificar duplicados
            registros_existentes, df_filtrado = self.verificar_registros_existentes(df_precios, fecha_datos)
            
            if df_filtrado.empty:
                print("📊 No hay registros nuevos para insertar")
                return 0
            
            ticker_col = 'accion' if 'accion' in df_filtrado.columns else 'cedear'
            
            precios_data = []
            registros_sin_activo_id = 0
            
            for _, row in df_filtrado.iterrows():
                try:
                    ticker = row[ticker_col]
                    
                    # VALIDACIÓN: Debe tener precio_cierre_anterior
                    if pd.isna(row['precio_cierre_anterior']):
                        continue
                    
                    # OBTENER ACTIVO_ID DEL MAESTRO
                    activo_id = self._get_activo_id_by_ticker(ticker)
                    if not activo_id:
                        print(f"⚠️ No se encontró activo_id para {ticker}")
                        registros_sin_activo_id += 1
                        continue
                    
                    precio_cierre = float(row['precio_cierre_anterior'])
                    
                    # SOLO CAMPOS ESENCIALES
                    precio_data = {
                        'activo_id': activo_id,  # ID correcto del maestro
                        'ticker': ticker,        # Para queries directas
                        'fecha': fecha_datos.isoformat(),
                        'precio_cierre': precio_cierre  # SOLO precio histórico relevante
                    }
                    
                    precios_data.append(precio_data)
                    
                except Exception as e:
                    print(f"⚠️ Error procesando {ticker}: {str(e)}")
                    continue
            
            if precios_data:
                result = self.supabase.table('precios_historico').insert(precios_data).execute()
                insertados = len(precios_data)
                
                if registros_sin_activo_id > 0:
                    print(f"⚠️ {registros_sin_activo_id} registros sin activo_id válido")
                
                print(f"✅ {insertados} precios históricos insertados correctamente")
                return insertados
            else:
                print("❌ No se pudieron procesar registros válidos")
                return 0
                
        except Exception as e:
            print(f"❌ Error en inserción masiva: {str(e)}")
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
                .select('fecha, ticker, precio_cierre')\
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
            return pd.DataFrame()
    
    def obtener_estadisticas_fecha(self, fecha_datos=None):
        """Obtiene estadísticas de una fecha específica"""
        try:
            if fecha_datos is None:
                fecha_datos = date.today()
            elif isinstance(fecha_datos, str):
                fecha_datos = datetime.strptime(fecha_datos, '%Y-%m-%d').date()
            
            # Consultar precios con JOIN a activos para obtener tipos
            result = self.supabase.table('precios_historico')\
                .select('ticker, activos!inner(tipo)')\
                .eq('fecha', fecha_datos.isoformat())\
                .execute()
            
            if result.data:
                # Contar por tipo
                acciones = sum(1 for row in result.data if row['activos']['tipo'] == 'ACCION')
                cedears = sum(1 for row in result.data if row['activos']['tipo'] == 'CEDEAR')
                
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
                print(f"📊 No hay datos para {fecha_datos}")
                return stats
                
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {str(e)}")
            return None

# Función de conveniencia actualizada
def procesar_y_guardar_datos(df_acciones=None, df_cedears=None, fecha_datos=None):
    """Función principal actualizada con mapeo correcto de IDs"""
    print("\n" + "="*60)
    print("🗄️ INICIANDO GUARDADO EN BASE DE DATOS")
    print("="*60)
    
    db = SupabaseManager()
    
    if not db.test_connection():
        print("❌ No se pudo conectar a la base de datos")
        return False
    
    try:
        if fecha_datos is None:
            from datetime import timedelta
            fecha_datos = date.today() - timedelta(days=1)
        
        # 1. Crear activos nuevos si no existen
        db.crear_activos_desde_dataframes(df_acciones, df_cedears)
        
        # 2. Insertar precios históricos con IDs correctos
        precios_insertados = 0
        
        if df_acciones is not None and not df_acciones.empty:
            insertados = db.insertar_precios_masivo(df_acciones, fecha_datos)
            precios_insertados += insertados
        
        if df_cedears is not None and not df_cedears.empty:
            insertados = db.insertar_precios_masivo(df_cedears, fecha_datos)
            precios_insertados += insertados
        
        print(f"\n🎯 RESUMEN:")
        print(f"   💰 Precios históricos insertados: {precios_insertados}")
        print(f"   📅 Fecha: {fecha_datos}")
        print(f"   🔗 Con activo_id correctamente mapeado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return False