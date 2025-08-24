# ============================================================================
# utils/__init__.py
# ============================================================================

"""
Módulo de utilidades
Contiene funciones auxiliares y constantes del proyecto
"""

from .helpers import (
    clean_price_text,
    safe_click_with_retry,
    extract_ticker_from_id,
    create_empty_dataframe,
    log_progress,
    find_element_by_selectors
)

from .constants import (
    SELECTORS,
    SCROLL_CONFIG,
    LOG_MESSAGES
)

__version__ = "2.0.0"
__all__ = [
    # Helpers
    'clean_price_text',
    'safe_click_with_retry', 
    'extract_ticker_from_id',
    'create_empty_dataframe',
    'log_progress',
    'find_element_by_selectors',
    # Constants
    'SELECTORS',
    'SCROLL_CONFIG', 
    'LOG_MESSAGES'
]