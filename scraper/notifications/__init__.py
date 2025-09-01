# scraper/notifications/__init__.py - CORREGIDO

"""
Módulo de notificaciones
Contiene las funciones para envío de notificaciones por WhatsApp y Email
"""

from .whatsapp_notifier import WhatsAppNotifier
from .email_notifier import EmailNotifier

__version__ = "2.1.0"
__all__ = [
    'WhatsAppNotifier',
    'EmailNotifier'
]