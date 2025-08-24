import uuid
from datetime import datetime
import json

from app.models.database_pg import execute_query, security_events_table_id, app_events_table_id

def log_security_event(user_id, event_type, details, ip_address):
    """
    Registra eventos de seguridad en la tabla de logs
    
    Args:
        user_id: ID del usuario (None si no está autenticado)
        event_type: Tipo de evento (login_success, login_failed, etc.)
        details: Detalles adicionales del evento
        ip_address: Dirección IP desde donde se generó el evento
        
    Returns:
        bool: True si el registro fue exitoso
    """
    log_id = str(uuid.uuid4())
    
    try:
        query = f"""
        INSERT INTO security_events 
        (event_id, user_id, event_type, timestamp, ip_address, details) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        params = (
            log_id,
            user_id,
            event_type,
            datetime.now(),
            ip_address,
            json.dumps(details)
        )
        
        execute_query(query, params=params, fetch=False)
        return True
    except Exception as e:
        print(f"Error al registrar evento de seguridad: {str(e)}")
        return False

def log_app_event(user_id, module, action, details, ip_address):
    """
    Registra eventos generales de la aplicación
    
    Args:
        user_id: ID del usuario (None si no está autenticado)
        module: Módulo donde ocurrió el evento (auth, payments, dashboard, etc.)
        action: Acción realizada (view, create, update, delete, etc.)
        details: Detalles adicionales del evento
        ip_address: Dirección IP desde donde se generó el evento
        
    Returns:
        bool: True si el registro fue exitoso
    """
    log_id = str(uuid.uuid4())
    
    try:
        query = f"""
        INSERT INTO app_events 
        (event_id, user_id, module, action, timestamp, ip_address, details) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            log_id,
            user_id,
            module,
            action,
            datetime.now(),
            ip_address,
            json.dumps(details)
        )
        
        execute_query(query, params=params, fetch=False)
        return True
    except Exception as e:
        print(f"Error al registrar evento de aplicación: {str(e)}")
        return False

def log_error(user_id, module, error, details, ip_address):
    """
    Registra errores en la aplicación
    
    Args:
        user_id: ID del usuario (None si no está autenticado)
        module: Módulo donde ocurrió el error
        error: Descripción del error
        details: Detalles adicionales del error
        ip_address: Dirección IP desde donde se generó el error
        
    Returns:
        bool: True si el registro fue exitoso
    """
    log_id = str(uuid.uuid4())
    
    try:
        query = f"""
        INSERT INTO logs_sistema 
        (log_id, user_id, tipo, modulo, accion, detalles, fecha, ip_address, subtipo) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            log_id,
            user_id,
            'error',
            module,
            'error',
            json.dumps({
                'error': error,
                'details': details
            }),
            datetime.now(),
            ip_address,
            None
        )
        
        execute_query(query, params=params, fetch=False)
        return True
    except Exception as e:
        print(f"Error al registrar error: {str(e)}")
        return False