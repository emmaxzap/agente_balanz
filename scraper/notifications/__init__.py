# scraper/notifications/__init__.py

"""
Módulo de notificaciones
Contiene las funciones para envío de notificaciones por WhatsApp
"""

from .whatsapp_notifier import WhatsAppNotifier, WhatsAppNotifierFree

__version__ = "2.0.0"
__all__ = [
    'WhatsAppNotifier',
    'WhatsAppNotifierFree'
]