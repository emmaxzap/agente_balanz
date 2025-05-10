import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv

load_dotenv() 
# Verificar que las variables se cargaron correctamente
print(f"DB_HOST cargado del .env: {os.environ.get('DB_HOST', 'No encontrado')}")
print(f"DB_PORT cargado del .env: {os.environ.get('DB_PORT', 'No encontrado')}")

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración de la conexión a PostgreSQL con las variables correctas del .env
db_config = {
    'dbname': os.environ.get('DB_NAME', 'postgres'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'Geba.1149_2025'),
    'host': os.environ.get('DB_HOST', 'db.syqloaxfzksuqlhwdsjf.supabase.co'),
    'port': os.environ.get('DB_PORT', '5432')
}

# Para debugging, mostrar información de conexión (sin contraseña)
debug_config = {**db_config}
if 'password' in debug_config:
    debug_config['password'] = '***'
logger.info(f"Configuración de base de datos: {debug_config}")

# Definiciones de nombres de tablas
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

# Tablas para equipos
team_members_table_id = 'team_members'
team_invitations_table_id = 'team_invitations'
invitation_actions_table_id = 'invitation_actions'

# Tablas adicionales encontradas en payments.py
planes_creditos_table_id = 'planes_creditos'
servicios_table_id = 'servicios'

# Mantener compatibilidad con el código existente - Placeholders para clases de BigQuery
# Estas clases no hacen nada pero permiten mantener la compatibilidad
client = None

class QueryJobConfig:
    """Clase placeholder para mantener compatibilidad con BigQuery"""
    def __init__(self, query_parameters=None):
        self.query_parameters = query_parameters if query_parameters else []

class ScalarQueryParameter:
    """Clase placeholder para mantener compatibilidad con BigQuery"""
    def __init__(self, name, param_type, value):
        self.name = name
        self.param_type = param_type
        self.value = value

# Variable para almacenar el pool de conexiones
pool = None

def get_connection():
    """
    Obtiene una conexión de la base de datos, con manejo de errores.
    Si no se puede usar pool, crea una conexión directa.
    
    Returns:
        connection: Conexión a la base de datos
    """
    global pool
    
    try:
        # Intentar usar psycopg2.pool si está disponible
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
        
        # Si el pool está disponible, obtener una conexión del pool
        if pool and pool is not False:
            return pool.getconn()
        else:
            # Si el pool no está disponible, crear una conexión directa
            return psycopg2.connect(**db_config)
            
    except Exception as e:
        logger.error(f"Error al conectar a PostgreSQL: {str(e)}")
        raise

def release_connection(conn):
    """
    Libera una conexión de vuelta al pool o la cierra si no se usa pool
    
    Args:
        conn: Conexión a liberar
    """
    global pool
    
    if pool and pool is not False:
        # Si el pool está disponible, devolver la conexión al pool
        pool.putconn(conn)
    else:
        # Si no hay pool, cerrar la conexión
        conn.close()

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
    try:
        # Obtener una conexión
        conn = get_connection()
        
        # Crear cursor (dict si as_dict=True)
        if as_dict:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # Ejecutar la consulta
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Commit si es necesario (no para SELECT)
        if not fetch:
            conn.commit()
            return None
        
        # Obtener resultados
        results = cursor.fetchall()
        
        # Convertir a lista de diccionarios si es necesario
        if results and as_dict and not isinstance(cursor, RealDictCursor):
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in results]
            
        return results
    
    except Exception as e:
        # Log del error
        logger.error(f"Error al ejecutar consulta: {str(e)}")
        logger.error(f"Consulta: {query}")
        if params:
            logger.error(f"Parámetros: {params}")
        logger.error(traceback.format_exc())
        
        # Rollback en caso de error
        if conn:
            conn.rollback()
        
        # Re-lanzar la excepción
        raise
    
    finally:
        # Cerrar cursor
        if cursor:
            cursor.close()
        
        # Liberar conexión
        if conn:
            release_connection(conn)

def execute_transaction(queries):
    """
    Ejecuta múltiples consultas en una transacción
    
    Args:
        queries (list): Lista de tuplas (query, params)
        
    Returns:
        bool: True si la transacción fue exitosa
    """
    conn = None
    cursor = None
    
    try:
        # Obtener conexión
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ejecutar cada consulta
        for query, params in queries:
            cursor.execute(query, params)
        
        # Commit de la transacción
        conn.commit()
        return True
        
    except Exception as e:
        # Log del error
        logger.error(f"Error en la transacción: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Rollback en caso de error
        if conn:
            conn.rollback()
            
        # Re-lanzar la excepción
        raise
        
    finally:
        # Cerrar cursor
        if cursor:
            cursor.close()
            
        # Liberar conexión
        if conn:
            release_connection(conn)

def json_serializer(obj):
    """
    Serializador para objetos JSON que maneja fechas
    
    Args:
        obj: Objeto a serializar
        
    Returns:
        str: Representación del objeto serializable
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_table_schema(table_name):
    """
    Obtiene el esquema de una tabla
    
    Args:
        table_name (str): Nombre de la tabla
        
    Returns:
        list: Lista de diccionarios con información de las columnas
    """
    query = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position
    """
    
    return execute_query(query, params=(table_name,), fetch=True, as_dict=True)

def create_table_if_not_exists(table_name, columns_definition):
    """
    Crea una tabla si no existe
    
    Args:
        table_name (str): Nombre de la tabla
        columns_definition (str): Definición de columnas en formato SQL
        
    Returns:
        bool: True si se creó la tabla o ya existía
    """
    try:
        # Verificar si la tabla ya existe
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
        """
        
        result = execute_query(check_query, params=(table_name,), fetch=True, as_dict=False)
        table_exists = result[0][0]
        
        if not table_exists:
            # Crear la tabla
            create_query = f"""
            CREATE TABLE {table_name} (
                {columns_definition}
            );
            """
            
            execute_query(create_query, fetch=False)
            logger.info(f"Tabla {table_name} creada correctamente")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al crear tabla {table_name}: {str(e)}")
        return False

# Inicializar conexión al cargar el módulo
try:
    get_connection()
    logger.info("Módulo database_pg inicializado correctamente")
except Exception as e:
    logger.error(f"Error al inicializar el módulo database_pg: {str(e)}")
    logger.error(traceback.format_exc())