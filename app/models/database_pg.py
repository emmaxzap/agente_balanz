import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv
import threading
from contextlib import contextmanager

load_dotenv() 
# Verificar que las variables se cargaron correctamente
print(f"DB_HOST cargado del .env: {os.environ.get('DB_HOST', 'No encontrado')}")
print(f"DB_PORT cargado del .env: {os.environ.get('DB_PORT', 'No encontrado')}")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la conexión a PostgreSQL con las variables correctas del .env
db_config = {
    'dbname': os.environ.get('DB_NAME', 'postgres'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '***'),
    'host': os.environ.get('DB_HOST', 'db.syqloaxfzksuqlhwdsjf.supabase.co'),
    'port': os.environ.get('DB_PORT', '5432')
}

# Para debugging, mostrar información de conexión (sin contraseña)
debug_config = {**db_config}
if 'password' in debug_config:
    debug_config['password'] = '***'
logger.info(f"Configuración de base de datos: {debug_config}")

# Definiciones de nombres de tablas (omitidas para brevedad...)
usuarios_table_id = 'usuarios'
recovery_tokens_table_id = 'recovery_tokens'
historial_passwords_table_id = 'historial_passwords'
logins_table_id = 'sesiones_login'
transacciones_table_id = 'transacciones'
uso_creditos_table_id = 'uso_creditos'
plan_changes_table_id = 'plan_changes'
user_subscriptions_table_id = 'user_subscriptions'
subscription_plans_table_id = 'subscription_plans'
subscription_levels_table_id = 'subscription_levels'
service_categories_table_id = 'service_categories'
credit_packages_table_id = 'credit_packages'
pricing_tiers_table_id = 'pricing_tiers'
security_events_table_id = 'security_events'
app_events_table_id = 'app_events'
team_members_table_id = 'team_members'
team_invitations_table_id = 'team_invitations'
invitation_actions_table_id = 'invitation_actions'
planes_creditos_table_id = 'planes_creditos'
servicios_table_id = 'servicios'

# Mantener compatibilidad con el código existente
client = None

class QueryJobConfig:
    def __init__(self, query_parameters=None):
        self.query_parameters = query_parameters if query_parameters else []

class ScalarQueryParameter:
    def __init__(self, name, param_type, value):
        self.name = name
        self.param_type = param_type
        self.value = value

# Variable para almacenar el pool de conexiones
pool = None
pool_lock = threading.Lock()
thread_local = threading.local()

def init_database():
    """
    Inicializa la conexión a la base de datos y crea el pool
    """
    global pool
    
    with pool_lock:
        if pool is None:
            try:
                # Intentar importar e inicializar el pool
                from psycopg2 import pool as psycopg2_pool
                
                # Crear un ThreadedConnectionPool
                pool = psycopg2_pool.ThreadedConnectionPool(
                    minconn=1, 
                    maxconn=20, 
                    **db_config
                )
                logger.info("Pool de conexiones creado correctamente")
            except (ImportError, AttributeError) as e:
                # Si psycopg2.pool no está disponible, establecer pool a False
                logger.error(f"Error al crear pool de conexiones: {str(e)}")
                pool = False

@contextmanager
def get_db_connection():
    """
    Contexto para obtener una conexión de la base de datos y asegurar que se cierre correctamente.
    Uso: 
        with get_db_connection() as conn:
            # usar conn
    """
    conn = None
    try:
        # Obtener una conexión
        conn = get_connection()
        yield conn
    finally:
        # Asegurar que la conexión se libere correctamente
        if conn:
            release_connection(conn)

def get_connection():
    """
    Obtiene una conexión de la base de datos, con manejo de errores.
    Si no se puede usar pool, crea una conexión directa.
    
    Returns:
        connection: Conexión a la base de datos
    """
    global pool
    
    # Inicializar el pool si no existe
    if pool is None:
        init_database()
    
    # Verificar si hay una conexión en el hilo local
    if hasattr(thread_local, 'connection') and thread_local.connection:
        try:
            # Verificar si la conexión está abierta
            if thread_local.connection.closed == 0:
                return thread_local.connection
        except Exception:
            # Si hay error, limpiar la conexión
            thread_local.connection = None
    
    try:
        # Si el pool está disponible, obtener una conexión del pool
        if pool and pool is not False:
            new_conn = pool.getconn(key=threading.get_ident())
            # Verificar si la conexión está viva
            try:
                with new_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except Exception:
                # Si la conexión está muerta, intentar cerrarla y obtener una nueva
                try:
                    pool.putconn(new_conn, key=threading.get_ident(), close=True)
                except:
                    pass
                new_conn = pool.getconn(key=threading.get_ident())
        else:
            # Si el pool no está disponible, crear una conexión directa
            new_conn = psycopg2.connect(**db_config)
            
        # Almacenar la conexión en el hilo local
        thread_local.connection = new_conn
        return new_conn
            
    except Exception as e:
        logger.error(f"Error al conectar a PostgreSQL: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def release_connection(conn):
    """
    Libera una conexión de vuelta al pool o la cierra si no se usa pool
    
    Args:
        conn: Conexión a liberar
    """
    global pool
    
    # Verificar si es la conexión del hilo actual
    is_thread_connection = hasattr(thread_local, 'connection') and thread_local.connection is conn
    
    try:
        # Verificar que conn no sea None
        if conn is None:
            if is_thread_connection:
                thread_local.connection = None
            return
            
        # Verificar si la conexión está cerrada
        if hasattr(conn, 'closed') and conn.closed != 0:
            if is_thread_connection:
                thread_local.connection = None
            return
            
        if pool and pool is not False:
            # Si hay transacciones pendientes, hacer rollback
            if hasattr(conn, 'status') and conn.status != psycopg2.extensions.STATUS_READY:
                try:
                    conn.rollback()
                except:
                    pass
                    
            # Devolver la conexión al pool
            pool.putconn(conn, key=threading.get_ident(), close=False)
        else:
            # Si no hay pool, cerrar la conexión
            conn.close()
    except Exception as e:
        logger.error(f"Error al liberar conexión: {str(e)}")
    finally:
        if is_thread_connection:
            thread_local.connection = None

def execute_query(query, params=None, fetch=True, as_dict=True):
    """
    Ejecuta una consulta SQL con parámetros opcionales
    
    Args:
        query (str): Consulta SQL a ejecutar
        params (tuple, opcional): Parámetros para la consulta
        fetch (bool, opcional): Si se deben recuperar resultados
        as_dict (bool, opcional): Si los resultados deben ser diccionarios
        
    Returns:
        list: Resultados de la consulta (si fetch=True)
    """
    conn = None
    cursor = None
    retries = 2  # Número de reintentos en caso de error
    
    for attempt in range(retries + 1):
        try:
            # Obtener una conexión
            with get_db_connection() as conn:
                # Crear cursor (dict si as_dict=True)
                if as_dict:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor = conn.cursor()
                
                try:
                    # Ejecutar la consulta
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Commit si es necesario (no para SELECT)
                    if not fetch:
                        conn.commit()
                        rowcount = cursor.rowcount
                        cursor.close()
                        return rowcount
                    
                    # Obtener resultados
                    results = cursor.fetchall()
                    
                    # Convertir a lista de diccionarios si es necesario
                    if results and as_dict and not isinstance(cursor, RealDictCursor):
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in results]
                    
                    cursor.close()
                    return results
                except psycopg2.errors.UndefinedColumn as e:
                    # Manejar específicamente el error de columna indefinida
                    logger.error(f"Error de columna indefinida: {str(e)}")
                    logger.error(f"Consulta: {query}")
                    logger.error(f"Parámetros: {params}")
                    
                    # Rollback y relanzar la excepción
                    if conn and not conn.closed:
                        try:
                            conn.rollback()
                        except:
                            pass
                    raise
                except Exception as e:
                    # Rollback en caso de error
                    if conn and not conn.closed:
                        try:
                            conn.rollback()
                        except:
                            pass
                    raise
        except psycopg2.InterfaceError:
            # Si la conexión está cerrada, limpiar la conexión del hilo local e intentar de nuevo
            if hasattr(thread_local, 'connection'):
                thread_local.connection = None
                
            if attempt < retries:
                logger.warning(f"Conexión cerrada, reintentando (intento {attempt+1}/{retries+1})")
                continue
            raise
        except Exception as e:
            # Log del error
            logger.error(f"Error al ejecutar consulta (intento {attempt+1}/{retries+1}): {str(e)}")
            logger.error(f"Consulta: {query}")
            if params:
                logger.error(f"Parámetros: {params}")
            logger.error(traceback.format_exc())
            
            # Si es el último intento, re-lanzar la excepción
            if attempt == retries:
                raise
                
            # En caso de error de conexión, limpiar la conexión del hilo local e intentar de nuevo
            if hasattr(thread_local, 'connection'):
                thread_local.connection = None

def execute_transaction(queries):
    """
    Ejecuta múltiples consultas en una transacción
    
    Args:
        queries (list): Lista de tuplas (query, params)
        
    Returns:
        bool: True si la transacción fue exitosa
    """
    retries = 2  # Número de reintentos en caso de error
    
    for attempt in range(retries + 1):
        try:
            # Obtener conexión
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Ejecutar cada consulta
                    for query, params in queries:
                        cursor.execute(query, params)
                    
                    # Commit de la transacción
                    conn.commit()
                    cursor.close()
                    return True
                except Exception as e:
                    # Rollback en caso de error
                    if conn and not conn.closed:
                        try:
                            conn.rollback()
                        except:
                            pass
                    raise
        except psycopg2.InterfaceError:
            # Si la conexión está cerrada, limpiar la conexión del hilo local e intentar de nuevo
            if hasattr(thread_local, 'connection'):
                thread_local.connection = None
                
            if attempt < retries:
                logger.warning(f"Conexión cerrada, reintentando (intento {attempt+1}/{retries+1})")
                continue
            raise
        except Exception as e:
            # Log del error
            logger.error(f"Error en la transacción (intento {attempt+1}/{retries+1}): {str(e)}")
            logger.error(traceback.format_exc())
            
            # Si es el último intento, re-lanzar la excepción
            if attempt == retries:
                raise
                
            # En caso de error de conexión, limpiar la conexión del hilo local e intentar de nuevo
            if hasattr(thread_local, 'connection'):
                thread_local.connection = None

def cleanup_pools():
    """
    Limpia el pool de conexiones
    """
    global pool
    if pool and pool is not False:
        try:
            pool.closeall()
            logger.info("Pool de conexiones cerrado correctamente")
        except Exception as e:
            logger.error(f"Error al cerrar el pool de conexiones: {str(e)}")

# El resto de funciones quedan iguales

# Función para agregar a Flask
def init_app(app):
    """
    Configura la integración con Flask
    
    Args:
        app: Aplicación Flask
    """
    @app.teardown_appcontext
    def close_db_connection(exception):
        """Cierra la conexión cuando termina el contexto de la aplicación"""
        if hasattr(thread_local, 'connection'):
            try:
                release_connection(thread_local.connection)
            except:
                pass
            thread_local.connection = None
    
    # Inicializar la base de datos
    init_database()
    
    # Registrar función para limpiar el pool al cerrar la aplicación
    import atexit
    atexit.register(cleanup_pools)

# Inicializar conexión al cargar el módulo
try:
    get_connection()
    logger.info("Módulo database_pg inicializado correctamente")
except Exception as e:
    logger.error(f"Error al inicializar el módulo database_pg: {str(e)}")
    logger.error(traceback.format_exc())