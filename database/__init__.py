# ============================================================================
# database/__init__.py
# ============================================================================

"""
Módulo de gestión de base de datos
Contiene las funciones para interactuar con Supabase
"""

from .database_manager import SupabaseManager, procesar_y_guardar_datos

__version__ = "2.0.0"
__all__ = [
    'SupabaseManager',
    'procesar_y_guardar_datos'
]