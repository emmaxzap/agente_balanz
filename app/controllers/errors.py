from flask import render_template, request, session
from app.utils.logging import log_security_event, log_error

def register_error_handlers(app):
    """
    Registra los manejadores de errores para la aplicación
    
    Args:
        app: La instancia de Flask
    """
    @app.errorhandler(404)
    def page_not_found(e):
        """Maneja errores 404 - Página no encontrada"""
        # Registrar el error si el usuario está autenticado
        if 'user_id' in session:
            log_error(
                user_id=session.get('user_id'),
                module='system',
                error='404_not_found',
                details={'url': request.path, 'method': request.method},
                ip_address=request.remote_addr
            )
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Maneja errores 500 - Error interno del servidor"""
        # Registrar el error interno del servidor
        log_error(
            user_id=session.get('user_id'),
            module='system',
            error='500_server_error',
            details={'url': request.path, 'method': request.method, 'error': str(e)},
            ip_address=request.remote_addr
        )
        
        # Si es un error de seguridad, registrarlo también en los logs de seguridad
        if hasattr(e, 'security_related') and e.security_related:
            log_security_event(
                user_id=session.get('user_id'),
                event_type='server_error',
                details={'url': request.path, 'method': request.method, 'error': str(e)},
                ip_address=request.remote_addr
            )
            
        return render_template('500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Maneja errores 429 - Demasiadas solicitudes"""
        # Registrar intento de abuso por límite de velocidad
        log_security_event(
            user_id=session.get('user_id'),
            event_type='rate_limit_exceeded',
            details={'url': request.path, 'method': request.method, 'description': e.description},
            ip_address=request.remote_addr
        )
        return render_template('429.html', mensaje=e.description), 429
    
    @app.errorhandler(403)
    def forbidden_error(e):
        """Maneja errores 403 - Acceso prohibido"""
        # Registrar intento de acceso prohibido
        log_security_event(
            user_id=session.get('user_id'),
            event_type='forbidden_access',
            details={'url': request.path, 'method': request.method},
            ip_address=request.remote_addr
        )
        return render_template('403.html'), 403
    
    @app.errorhandler(400)
    def bad_request_error(e):
        """Maneja errores 400 - Solicitud incorrecta"""
        # Registrar solicitud incorrecta
        log_error(
            user_id=session.get('user_id'),
            module='system',
            error='400_bad_request',
            details={'url': request.path, 'method': request.method, 'error': str(e)},
            ip_address=request.remote_addr
        )
        return render_template('400.html'), 400

class SecurityException(Exception):
    """Excepción personalizada para errores relacionados con seguridad"""
    def __init__(self, message, security_related=True):
        super().__init__(message)
        self.security_related = security_related